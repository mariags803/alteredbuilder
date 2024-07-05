from datetime import timedelta
from typing import Any
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from hitcount.models import Hit
from hitcount.views import HitCountDetailView

from .deck_utils import create_new_deck, get_deck_details
from .game_modes import update_deck_legality
from .models import Card, CardInDeck, Deck, LovePoint, PrivateLink
from .forms import DecklistForm, DeckMetadataForm, UpdateDeckForm
from .exceptions import MalformedDeckException


# Views for this app


class DeckListView(ListView):
    """ListView to display the public decks.
    If the user is authenticated, their decks are added to the context.
    """

    model = Deck
    queryset = (
        Deck.objects.filter(is_public=True)
        .select_related("owner", "hero")
        .order_by("-modified_at")
    )
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Deck]:
        """Return a queryset with the Decks that match the filters in the GET params.

        Returns:
            QuerySet[Deck]: The decks to list.
        """
        qs = super().get_queryset()
        filters = Q()

        # Retrieve the query and search by deck name or hero name
        query = self.request.GET.get("query")
        if query:
            filters &= Q(name__icontains=query) | Q(hero__name__icontains=query)

        # Extract the faction filter
        factions = self.request.GET.get("faction")
        if factions:
            try:
                factions = [Card.Faction(faction) for faction in factions.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(hero__faction__in=factions)

        # Extract the legality filter
        legality = self.request.GET.get("legality")
        if legality:
            legality = legality.split(",")
            if "standard" in legality:
                filters &= Q(is_standard_legal=True)
            elif "draft" in legality:
                filters &= Q(is_draft_legal=True)

        # Extract the other filters, which currently it's simply if the deck is loved
        other = self.request.GET.get("other")
        if other:
            if "loved" in other.split(","):
                try:
                    lp = LovePoint.objects.filter(user=self.request.user)
                    filters &= Q(id__in=lp.values_list("deck_id", flat=True))
                except TypeError:
                    pass

        # In the deck list view there's no need for these fields, which might be
        # expensive to fill into the model
        return qs.filter(filters).defer(
            "description", "cards", "standard_legality_errors", "draft_legality_errors"
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """If the user is authenticated, add their loved decks to the context.

        It also returns the checked filters so that they appear checked on the HTML.

        Returns:
            dict[str, Any]: The view's context.
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["loved_decks"] = LovePoint.objects.filter(
                user=self.request.user
            ).values_list("deck__id", flat=True)
        
        if self.request.user.is_superuser:
            last_week = timezone.now() - timedelta(days=14)
            lps = LovePoint.objects.filter(created_at__date__gt=last_week, deck__is_public=True).values("deck").annotate(total=Count("deck"))[:6]
            context["most_loved"] = Deck.objects.filter(id__in=[lp["deck"] for lp in lps]).order_by("-love_count").select_related("owner", "hero")

            hits = Hit.objects.filter(created__date__gt=last_week).values("hitcount", "hitcount__object_pk").annotate(total=Count("hitcount")).order_by("-total")[:6]
            context["trending"] = Deck.objects.filter(id__in=[hit["hitcount__object_pk"] for hit in hits]).select_related("owner", "hero")

        # Extract the filters applied from the GET params and add them to the context
        # to fill them into the template
        checked_filters = []
        for filter in ["faction", "legality", "other"]:
            if filter in self.request.GET:
                checked_filters += self.request.GET[filter].split(",")
        context["checked_filters"] = checked_filters
        if "query" in self.request.GET:
            context["query"] = self.request.GET.get("query")

        return context


class OwnDeckListView(LoginRequiredMixin, ListView):
    """ListView to display the own decks."""

    model = Deck
    paginate_by = 24
    template_name = "decks/own_deck_list.html"

    def get_queryset(self) -> QuerySet[Deck]:
        """Return a queryset with the Decks created by the user.

        Returns:
            QuerySet[Deck]: Decks created by the user.
        """
        qs = super().get_queryset()
        return (
            qs.filter(owner=self.request.user)
            .select_related("hero")
            .defer(
                "description",
                "cards",
                "standard_legality_errors",
                "draft_legality_errors",
            )
            .order_by("-modified_at")
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Add the loved decks ids to the context to highlight them.

        Returns:
            dict[str, Any]: The view's context.
        """
        context = super().get_context_data(**kwargs)
        context["loved_decks"] = LovePoint.objects.filter(
            user=self.request.user, deck__owner=self.request.user
        ).values_list("deck__id", flat=True)
        return context


class DeckDetailView(HitCountDetailView):
    """DetailView to display the detail of a Deck model."""

    model = Deck
    count_hit = True

    def get_queryset(self) -> Manager[Deck]:
        """When retrieving the object, we need to make sure that the Deck is public or
        the User is its owner.

        Returns:
            Manager[Deck]: The view's queryset.
        """
        filter = Q(is_public=True)
        if self.request.user.is_authenticated:
            filter |= Q(owner=self.request.user)
        return Deck.objects.filter(filter).select_related("hero", "owner")

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Add metadata of the Deck to the context.

        Returns:
            dict[str, Any]: The view's context.
        """

        context = super().get_context_data(**kwargs)
        context |= get_deck_details(self.object)
        context["form"] = DeckMetadataForm(
            initial={
                "name": self.object.name,
                "description": self.object.description,
                "is_public": self.object.is_public,
            }
        )
        if self.request.user.is_authenticated:
            context["is_loved"] = LovePoint.objects.filter(
                deck=self.object, user=self.request.user
            ).exists()

        return context


class PrivateLinkDeckDetailView(LoginRequiredMixin, DeckDetailView):
    """DetailView to display the detail of a Deck model by using a private link."""

    def get(self, request, *args, **kwargs):
        self.object: Deck = self.get_object()
        if self.object.owner == request.user or self.object.is_public:
            # If the owner is accessing with the private link or the Deck is public,
            # redirect to the official one
            return redirect(reverse("deck-detail", kwargs={"pk": self.object.id}))
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_queryset(self) -> Manager[Deck]:
        """When retrieving the object, we need to make sure that the code matches with
        the requested Deck.

        Returns:
            Manager[Deck]: The view's queryset.
        """
        code = self.kwargs["code"]
        deck_id = self.kwargs["pk"]
        try:
            link = PrivateLink.objects.get(code=code, deck__id=deck_id)
            link.last_accessed_at = timezone.now()
            link.save(update_fields=["last_accessed_at"])
            return Deck.objects.filter(id=deck_id).select_related("hero", "owner")
        except PrivateLink.DoesNotExist:
            raise Http404("Private link does not exist")


class NewDeckFormView(LoginRequiredMixin, FormView):
    """FormView to manage the creation of a Deck.
    It requires being authenticated.
    """

    template_name = "decks/new_deck.html"
    form_class = DecklistForm

    def get_initial(self) -> dict[str, Any]:
        """Function to modify the initial values of the form.

        Returns:
            dict[str, Any]: Initial values
        """
        initial = super().get_initial()
        if "decklist" in self.request.GET:
            initial["decklist"] = self.request.GET["decklist"]
        elif "hero" in self.request.GET:
            initial["decklist"] = f"1 {self.request.GET['hero']}"

        return initial

    def form_valid(self, form: DecklistForm) -> HttpResponse:
        """Function called once a submitted DecklistForm has been validated.
        Convert the submitted input into a Deck object. If there's any errors on the
        input, render it to the user.

        Args:
            form (DecklistForm): The submitted information.

        Returns:
            HttpResponse: The view's response.
        """
        # Create deck
        try:
            self.deck = create_new_deck(self.request.user, form.cleaned_data)

        except MalformedDeckException as e:
            # If the deck contains any error, render it to the user
            form.add_error("decklist", e.detail)
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Return the redirect URL for a successful Deck submission.
        Redirect to the Deck's detail view.

        Returns:
            str: The Deck's detail endpoint.
        """
        return reverse("deck-detail", kwargs={"pk": self.deck.id})


@login_required
def delete_deck(request: HttpRequest, pk: int) -> HttpResponse:
    """View to delete a Deck.

    Args:
        request (HttpRequest): The request.
        pk (int): The ID of the Deck to be deleted.

    Returns:
        HttpResponse: The response.
    """

    # The user is part of the filter to ensure ownership.
    # The delete statement won't fail even if the filter doesn't match any record, which
    # means that if the Deck is not found (doesn't exist or isn't owned) the view will
    # fail silently and redirect the user to their Decks regardless of the result.
    Deck.objects.filter(pk=pk, owner=request.user).delete()
    return redirect("own-deck")


@login_required
def love_deck(request: HttpRequest, pk: int) -> HttpResponse:
    """View to add a LovePoint to a Deck. If the Deck is already loved by the user,
    it will be undone.

    Args:
        request (HttpRequest): The request.
        pk (int): The ID of the Deck to act upon.

    Raises:
        PermissionDenied: If the user does not have access to the Deck.

    Returns:
        HttpResponse: The response.
    """
    try:
        # The Deck must be either public or owned
        deck = Deck.objects.filter(Q(is_public=True) | Q(owner=request.user)).get(pk=pk)
        # Retrieve the LovePoint by the user to this Deck
        love_point = LovePoint.objects.get(deck=deck, user=request.user)
    except LovePoint.DoesNotExist:
        # If the LovePoint does not exist, create it and increase the `love_count`
        LovePoint.objects.create(deck=deck, user=request.user)
        deck.love_count = F("love_count") + 1
        deck.save(update_fields=["love_count"])
    except Deck.DoesNotExist:
        # If the Deck is not found (private and not owned), raise a permission error
        raise PermissionDenied
    else:
        # If the LovePoint exists, delete it and decrease the `love_count`
        love_point.delete()
        deck.love_count = F("love_count") - 1
        deck.save(update_fields=["love_count"])
    return redirect(reverse("deck-detail", kwargs={"pk": deck.id}))


@login_required
def update_deck(request: HttpRequest, pk: int) -> HttpResponse:
    """Function to update a deck with AJAX.
    I'm not proud of this implementation, as this code is kinda duplicated in
    `UpdateDeckFormView`. Ideally it should be moved to the API app.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """

    # Ensure it's an AJAX request
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        if request.method == "POST":
            try:
                # Retrieve the referenced objects
                data = json.load(request)
                deck = Deck.objects.get(pk=pk, owner=request.user)
                card = Card.objects.get(reference=data["card_reference"])
                action = data["action"]

                if action == "add":
                    # Not currently used
                    pass

                elif action == "delete":
                    if (
                        card.type == Card.Type.HERO
                        and deck.hero.reference == card.reference
                    ):
                        # If it's the Deck's hero, remove the reference
                        deck.hero = None
                    else:
                        # Retrieve the CiD and delete it
                        cid = CardInDeck.objects.get(deck=deck, card=card)
                        cid.delete()
                    status = {"deleted": True}
                else:
                    raise KeyError("Invalid action")

                update_deck_legality(deck)
                deck.save()

            except Deck.DoesNotExist:
                return JsonResponse(
                    {"error": {"code": 404, "message": _("Deck not found")}}, status=404
                )
            except (Card.DoesNotExist, CardInDeck.DoesNotExist):
                return JsonResponse(
                    {"error": {"code": 404, "message": _("Card not found")}}, status=404
                )
            except (json.decoder.JSONDecodeError, KeyError):
                return JsonResponse(
                    {"error": {"code": 400, "message": _("Invalid payload")}},
                    status=400,
                )
            return JsonResponse({"data": status}, status=201)
        else:
            return JsonResponse(
                {"error": {"code": 400, "message": _("Invalid request")}}, status=400
            )
    else:
        return HttpResponse(_("Invalid request"), status=400)


@login_required
def create_private_link(request: HttpRequest, pk: int) -> HttpResponse:
    """Function to create a PrivateLink with AJAX.
    Ideally it should be moved to the API app.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """

    # Ensure it's an AJAX request
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        if request.method == "POST":
            try:
                # Retrieve the referenced Deck
                deck = Deck.objects.get(pk=pk, owner=request.user)
                if deck.is_public:
                    return JsonResponse(
                        {"error": {"code": 400, "message": _("Invalid request")}},
                        status=400,
                    )

                pl, created = PrivateLink.objects.get_or_create(deck=deck)
                status = {
                    "created": created,
                    "link": reverse(
                        "private-url-deck-detail", kwargs={"pk": pk, "code": pl.code}
                    ),
                }
            except Deck.DoesNotExist:
                return JsonResponse(
                    {"error": {"code": 404, "message": _("Deck not found")}}, status=404
                )
            return JsonResponse({"data": status}, status=201)
        else:
            return JsonResponse(
                {"error": {"code": 400, "message": _("Invalid request")}}, status=400
            )
    else:
        return HttpResponse(_("Invalid request"), status=400)


class UpdateDeckFormView(LoginRequiredMixin, FormView):
    """View to add a Card to a Deck."""

    template_name = "decks/card_list.html"
    form_class = UpdateDeckForm

    def form_valid(self, form: UpdateDeckForm) -> HttpResponse:
        """If the form is valid, add the Card to the Deck

        Args:
            form (UpdateDeckForm): The request.

        Returns:
            HttpResponse: The response.
        """
        try:
            # Retrieve the referenced Card and Deck
            deck = Deck.objects.get(
                pk=form.cleaned_data["deck_id"], owner=self.request.user
            )
            card = Card.objects.get(reference=form.cleaned_data["card_reference"])
            if card.type == Card.Type.HERO:
                # If it's a hero, add it to the Deck unless the Deck has one already
                if not deck.hero:
                    deck.hero = card.hero
                else:
                    # Silently fail
                    form.add_error("deck_id", _("Deck already has a hero"))
                    return super().form_valid(form)
            else:
                # If the Card is already in the Deck, add it to the quantity of it
                cid = CardInDeck.objects.get(deck=deck, card=card)
                cid.quantity = F("quantity") + form.cleaned_data["quantity"]
                cid.save()
        except Deck.DoesNotExist:
            form.add_error("deck_id", _("Deck not found"))
            return self.form_invalid(form)
        except Card.DoesNotExist:
            form.add_error("card_reference", _("Card not found"))
            return self.form_invalid(form)
        except CardInDeck.DoesNotExist:
            # The card is not in the deck, so we add it
            CardInDeck.objects.create(
                deck=deck, card=card, quantity=form.cleaned_data["quantity"]
            )

        # Check the Deck's legality again after adding the Card
        update_deck_legality(deck)
        deck.save()

        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Return the redirect URL after successfully adding the Card to the Deck.
        Redirect to the same page.

        Returns:
            str: The user's current page.
        """
        return f"{reverse_lazy('cards')}?{self.request.META['QUERY_STRING']}"


class UpdateDeckMetadataFormView(LoginRequiredMixin, FormView):
    """View to update the metadata fields of a Deck."""

    template_name = "decks/deck_detail.html"
    form_class = DeckMetadataForm

    def form_valid(self, form: DeckMetadataForm) -> HttpResponse:
        """If the input data is valid, replace the old data with the received values.

        Args:
            form (DeckMetadataForm): The form filed by the user.

        Raises:
            PermissionDenied: If the user is not the owner.

        Returns:
            HttpResponse: The response.
        """
        try:
            # Retrieve the Deck by ID and the user, to ensure ownership
            deck = Deck.objects.get(pk=self.kwargs["pk"], owner=self.request.user)
            deck.name = form.cleaned_data["name"]
            deck.description = form.cleaned_data["description"]
            deck.is_public = form.cleaned_data["is_public"]
            deck.save()
        except Deck.DoesNotExist:
            # For some unknown reason, this is returning 405 instead of 403
            raise PermissionDenied

        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Return the redirect URL for a successful update.
        Redirect to the Deck's detail view.

        Returns:
            str: The Deck's detail endpoint.
        """
        return reverse("deck-detail", kwargs={"pk": self.kwargs["pk"]})


class CardListView(ListView):
    """View to list and filter all the Cards."""

    model = Card
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Card]:
        """Return a queryset matching the filters received via GET parameters.

        Returns:
            QuerySet[Card]: The list of Cards.
        """
        qs = super().get_queryset()
        filters = Q()

        # Retrieve the text query and search by name
        query = self.request.GET.get("query")
        if query:
            filters &= Q(name__icontains=query)

        # Retrieve the Faction filters.
        # If any value is invalid, this filter will not be applied.
        factions = self.request.GET.get("faction")
        if factions:
            try:
                factions = [Card.Faction(faction) for faction in factions.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(faction__in=factions)

        # Retrieve the Rarity filters.
        # If any value is invalid, this filter will not be applied.
        rarities = self.request.GET.get("rarity")
        if rarities:
            try:
                rarities = [Card.Rarity(rarity) for rarity in rarities.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(rarity__in=rarities)

        # Retrieve the Type filters.
        # If any value is invalid, this filter will not be applied.
        card_types = self.request.GET.get("type")
        if card_types:
            try:
                card_types = [
                    Card.Type(card_type) for card_type in card_types.split(",")
                ]
            except ValueError:
                pass
            else:
                filters &= Q(type__in=card_types)

        query_order = []
        order_param = self.request.GET.get("order")

        if order_param:
            # Subtract the "-" simbol pointing that the order will be inversed
            if desc := "-" in order_param:
                clean_order_param = order_param[1:]
            else:
                clean_order_param = order_param

            if clean_order_param in ["name", "rarity"]:
                query_order = [order_param]

            elif clean_order_param in ["mana", "reserve"]:
                # Due to the unique 1-to-1 relationship of the Card types, it is needed
                # to use Coalesce to try and order by different fields
                if clean_order_param == "mana":
                    fields = (
                        "character__main_cost",
                        "spell__main_cost",
                        "permanent__main_cost",
                    )
                else:
                    fields = (
                        "character__recall_cost",
                        "spell__recall_cost",
                        "permanent__recall_cost",
                    )

                mana_order = Coalesce(*fields)
                if desc:
                    mana_order = mana_order.desc()
                query_order = [mana_order]
            # If the order is inversed, the "reference" used as the second clause of
            # ordering also needs to be reversed
            query_order += ["-reference" if desc else "reference"]
        else:
            query_order = ["reference"]

        return qs.filter(filters).order_by(*query_order)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Add extra context to the view.

        If the user is authenticated, include the Decks owned to fill the modal to add
        a Card to a Deck.

        The filters applied are also returned to display their values on the template.

        Returns:
            dict[str, Any]: The template's context.
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["own_decks"] = (
                Deck.objects.filter(owner=self.request.user)
                .order_by("-modified_at")
                .values("id", "name")
            )
            context["form"] = UpdateDeckForm()

        checked_filters = []
        for filter in ["faction", "rarity", "type"]:
            if filter in self.request.GET:
                checked_filters += self.request.GET[filter].split(",")
        context["checked_filters"] = checked_filters
        if "order" in self.request.GET:
            context["order"] = self.request.GET["order"]
        if "query" in self.request.GET:
            context["query"] = self.request.GET.get("query")

        return context
