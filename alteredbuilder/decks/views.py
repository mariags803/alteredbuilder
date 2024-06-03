from typing import Any
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from .deck_utils import create_new_deck, get_deck_details
from .game_modes import update_deck_legality
from .models import Card, CardInDeck, Deck, LovePoint
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

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        filters = Q()

        query = self.request.GET.get("query")
        if query:
            filters &= Q(name__icontains=query) | Q(hero__name__icontains=query)

        factions = self.request.GET.get("faction")
        if factions:
            try:
                factions = [Card.Faction(faction) for faction in factions.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(hero__faction__in=factions)

        legality = self.request.GET.get("legality")
        if legality:
            legality = legality.split(",")
            if "standard" in legality:
                filters &= Q(is_standard_legal=True)
            elif "draft" in legality:
                filters &= Q(is_draft_legal=True)

        other = self.request.GET.get("other")
        if other:
            if "loved" in other.split(","):
                lp = LovePoint.objects.filter(user=self.request.user)
                filters &= Q(id__in=lp.values_list("deck_id", flat=True))

        return qs.filter(filters).defer(
            "description", "cards", "standard_legality_errors", "draft_legality_errors"
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """If the user is authenticated, add their decks to the context.

        Returns:
            dict[str, Any]: The view's context.
        """
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["own_decks"] = (
                Deck.objects.filter(owner=self.request.user)
                .select_related("hero")
                .defer(
                    "description",
                    "cards",
                    "standard_legality_errors",
                    "draft_legality_errors",
                )
                .order_by("-modified_at")[:10]
            )

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

    def get_queryset(self) -> QuerySet[Any]:
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


class DeckDetailView(DetailView):
    """DetailView to display the detail of a Deck model."""

    model = Deck

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
        try:
            # If the initial GET request contains the `hero` parameter, insert it into
            # the decklist
            initial["decklist"] = f"1 {self.request.GET['hero']}"
        except KeyError:
            pass
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
    Deck.objects.filter(pk=pk, owner=request.user).delete()
    return redirect("own-deck")


@login_required
def love_deck(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        deck = Deck.objects.filter(Q(is_public=True) | Q(owner=request.user)).get(pk=pk)
        love_point = LovePoint.objects.get(deck=deck, user=request.user)
        love_point.delete()
        deck.love_count = F("love_count") - 1
        deck.save(update_fields=["love_count"])
    except LovePoint.DoesNotExist:
        LovePoint.objects.create(deck=deck, user=request.user)
        deck.love_count = F("love_count") + 1
        deck.save(update_fields=["love_count"])
    except Deck.DoesNotExist:
        raise PermissionDenied
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
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if is_ajax:
        if request.method == "POST":
            try:
                data = json.load(request)
                deck = Deck.objects.get(pk=pk, owner=request.user)
                card = Card.objects.get(reference=data["card_reference"])
                action = data["action"]

                if action == "add":
                    quantity = data["quantity"]
                    CardInDeck.objects.create(deck=deck, card=card, quantity=quantity)
                    status = {"added": True}

                elif action == "delete":
                    if (
                        card.type == Card.Type.HERO
                        and deck.hero.reference == card.reference
                    ):
                        deck.hero = None
                    else:
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


class UpdateDeckFormView(LoginRequiredMixin, FormView):
    template_name = "decks/card_list.html"
    form_class = UpdateDeckForm

    def form_valid(self, form: UpdateDeckForm) -> HttpResponse:
        try:
            deck = Deck.objects.get(
                pk=form.cleaned_data["deck_id"], owner=self.request.user
            )
            card = Card.objects.get(reference=form.cleaned_data["card_reference"])
            if card.type == Card.Type.HERO:
                if not deck.hero:
                    deck.hero = card.hero
                else:
                    # Silently fail
                    form.add_error("deck_id", _("Deck already has a hero"))
                    return super().form_valid(form)
            else:
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

        update_deck_legality(deck)
        deck.save()

        return super().form_valid(form)

    def get_success_url(self) -> str:
        return f"{reverse_lazy('cards')}?{self.request.META['QUERY_STRING']}"


class UpdateDeckMetadataFormView(LoginRequiredMixin, FormView):
    template_name = "decks/deck_detail.html"
    form_class = DeckMetadataForm

    def form_valid(self, form: DeckMetadataForm) -> HttpResponse:
        try:
            deck = Deck.objects.get(pk=self.kwargs["pk"], owner=self.request.user)
            deck.name = form.cleaned_data["name"]
            deck.description = form.cleaned_data["description"]
            deck.is_public = form.cleaned_data["is_public"]
            deck.save()
        except Deck.DoesNotExist:
            raise PermissionDenied

        return super().form_valid(form)

    def get_success_url(self) -> str:
        """Return the redirect URL for a successful Deck submission.
        Redirect to the Deck's detail view.

        Returns:
            str: The Deck's detail endpoint.
        """
        return reverse("deck-detail", kwargs={"pk": self.kwargs["pk"]})


class CardListView(ListView):
    model = Card
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Any]:
        qs = super().get_queryset()
        filters = Q()

        query = self.request.GET.get("query")
        if query:
            filters &= Q(name__icontains=query)

        factions = self.request.GET.get("faction")
        if factions:
            try:
                factions = [Card.Faction(faction) for faction in factions.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(faction__in=factions)

        rarities = self.request.GET.get("rarity")
        if rarities:
            try:
                rarities = [Card.Rarity(rarity) for rarity in rarities.split(",")]
            except ValueError:
                pass
            else:
                filters &= Q(rarity__in=rarities)

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
            if desc := "-" in order_param:
                clean_order_param = order_param[1:]
            else:
                clean_order_param = order_param

            if clean_order_param in ["name", "rarity"]:
                query_order = [order_param]

            elif clean_order_param in ["mana", "reserve"]:
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
            query_order += ["-reference" if desc else "reference"]
        else:
            query_order = ["reference"]

        return qs.filter(filters).order_by(*query_order)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["own_decks"] = Deck.objects.filter(
                owner=self.request.user
            ).order_by("-modified_at")
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
