from http import HTTPStatus
from typing import Any
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Exists, F, OuterRef, Q
from django.db.models.manager import Manager
from django.db.models.query import QuerySet
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from hitcount.views import HitCountDetailView

from api.utils import ajax_request, ApiJsonResponse
from decks.deck_utils import (
    create_new_deck,
    get_deck_details,
    import_unique_card,
    parse_card_query_syntax,
    parse_deck_query_syntax,
    patch_deck,
    remove_card_from_deck,
)
from decks.game_modes import update_deck_legality
from decks.models import (
    Card,
    CardInDeck,
    Comment,
    CommentVote,
    Deck,
    LovePoint,
    PrivateLink,
    Set,
    Tag,
)
from decks.forms import (
    CardImportForm,
    CommentForm,
    DecklistForm,
    DeckMetadataForm,
    DeckTagsForm,
)
from decks.exceptions import AlteredAPIError, CardAlreadyExists, MalformedDeckException
from profiles.models import Follow


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
    paginate_by = 30

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
            qs, query_tags = parse_deck_query_syntax(qs, query)
            self.query_tags = query_tags
        else:
            self.query_tags = None

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
            if "exalts" in legality:
                filters &= Q(is_exalts_legal=True)

        # Extract the legality filter
        tags = self.request.GET.get("tag")
        if tags:
            tags = tags.split(",")
            filters &= Q(tags__name__in=tags)

        # Extract the other filters
        other_filters = self.request.GET.get("other")
        if other_filters:
            for other in other_filters.split(","):
                if other == "loved":
                    try:
                        lp = LovePoint.objects.filter(user=self.request.user)
                        filters &= Q(id__in=lp.values_list("deck_id", flat=True))
                    except TypeError:
                        pass
                elif other == "description":
                    qs = qs.exclude(description="")

        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_loved=Exists(
                    LovePoint.objects.filter(
                        deck=OuterRef("pk"), user=self.request.user
                    )
                ),
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("owner"), follower=self.request.user
                    )
                ),
            )

        # In the deck list view there's no need for these fields, which might be
        # expensive to fill into the model
        return (
            qs.filter(filters)
            .defer(
                "description",
                "cards",
                "standard_legality_errors",
                "draft_legality_errors",
            )
            .prefetch_related("hit_count_generic")
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """If the user is authenticated, add their loved decks to the context.

        It also returns the checked filters so that they appear checked on the HTML.

        Returns:
            dict[str, Any]: The view's context.
        """
        context = super().get_context_data(**kwargs)

        # Extract the filters applied from the GET params and add them to the context
        # to fill them into the template
        checked_filters = []
        for filter in ["faction", "legality", "tag", "other"]:
            if filter in self.request.GET:
                checked_filters += self.request.GET[filter].split(",")
        context["checked_filters"] = checked_filters

        if "query" in self.request.GET:
            context["query"] = self.request.GET.get("query")
            context["query_tags"] = self.query_tags

        context["tags"] = Tag.objects.order_by("-type", "name").values_list("name", flat=True)

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
            .annotate(
                is_loved=Exists(
                    LovePoint.objects.filter(
                        deck=OuterRef("pk"), user=self.request.user
                    )
                )
            )
            .select_related("hero")
            .defer(
                "description",
                "cards",
                "standard_legality_errors",
                "draft_legality_errors",
            )
            .order_by("-modified_at")
        )


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
        qs = super().get_queryset()
        filter = Q(is_public=True)
        if self.request.user.is_authenticated:
            filter |= Q(owner=self.request.user)
            qs = qs.annotate(
                is_loved=Exists(
                    LovePoint.objects.filter(
                        deck=OuterRef("pk"), user=self.request.user
                    )
                ),
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("owner"), follower=self.request.user
                    )
                ),
            )
        # I don't fancy making these queries here. Maybe I could store that information
        # on the UserProfile model
        qs = qs.annotate(
            follower_count=Count("owner__followers", distinct=True),
            following_count=Count("owner__following", distinct=True),
        )
        return (
            qs.filter(filter)
            .select_related("hero", "owner", "owner__profile")
            .prefetch_related("tags")
        )

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Add metadata of the Deck to the context.

        Returns:
            dict[str, Any]: The view's context.
        """

        context = super().get_context_data(**kwargs)
        context |= get_deck_details(self.object)
        context["metadata_form"] = DeckMetadataForm(
            initial={
                "name": self.object.name,
                "description": self.object.description,
                "is_public": self.object.is_public,
            }
        )
        context["tags_form"] = DeckTagsForm(initial={"tags": self.object.tags.all()})
        context["tags_type"] = Tag.objects.filter(type=Tag.Type.TYPE)
        context["tags_subtype"] = Tag.objects.filter(type=Tag.Type.SUBTYPE)
        context["comment_form"] = CommentForm()
        comments_qs = Comment.objects.filter(deck=self.object).select_related(
            "user", "user__profile"
        )
        if self.request.user.is_authenticated:
            comments_qs = comments_qs.annotate(
                is_upvoted=Exists(
                    CommentVote.objects.filter(
                        comment=OuterRef("pk"), user=self.request.user
                    )
                )
            )
        context["comments"] = comments_qs
        return context


class PrivateLinkDeckDetailView(LoginRequiredMixin, DeckDetailView):
    """DetailView to display the detail of a Deck model by using a private link."""

    def get(self, request, *args, **kwargs):
        self.object: Deck = self.get_object()
        if self.object.owner == request.user or self.object.is_public:
            # If the owner is accessing with the private link or the Deck is public,
            # redirect to the official one
            return redirect(self.object.get_absolute_url())
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
            return (
                Deck.objects.filter(id=deck_id)
                .select_related("hero", "owner", "owner__profile")
                .annotate(
                    follower_count=Count("owner__followers", distinct=True),
                    following_count=Count("owner__following", distinct=True),
                )
            )
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
        return self.deck.get_absolute_url()


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
        with transaction.atomic():
            love_point.delete()
            deck.love_count = F("love_count") - 1
            deck.save(update_fields=["love_count"])
    return redirect(deck.get_absolute_url())


@login_required
@ajax_request()
def update_deck(request: HttpRequest, pk: int) -> HttpResponse:
    """Function to update a deck with AJAX.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """
    try:
        data = json.load(request)

        match data["action"]:
            case "add":
                # Not currently used
                # The deck is retrieved for validation purposes
                deck = Deck.objects.get(pk=pk, owner=request.user)
                status = {"added": False}
            case "delete":
                deck = Deck.objects.get(pk=pk, owner=request.user)
                remove_card_from_deck(deck, data["card_reference"])
                status = {"deleted": True}
            case "patch":
                if not data["name"]:
                    return ApiJsonResponse(
                        _("The deck must have a name"), HTTPStatus.UNPROCESSABLE_ENTITY
                    )
                if pk == 0:
                    deck = Deck.objects.create(
                        owner=request.user, name=data["name"], is_public=True
                    )
                else:
                    deck = Deck.objects.get(pk=pk, owner=request.user)
                patch_deck(deck, data["name"], data["decklist"])
                status = {"patched": True, "deck": deck.id}
            case _:
                raise KeyError("Invalid action")

        update_deck_legality(deck)
        deck.save()
    except Deck.DoesNotExist:
        return ApiJsonResponse(_("Deck not found"), HTTPStatus.NOT_FOUND)
    except (Card.DoesNotExist, CardInDeck.DoesNotExist):
        return ApiJsonResponse(_("Card not found"), HTTPStatus.NOT_FOUND)
    except KeyError:
        return ApiJsonResponse(_("Invalid payload"), HTTPStatus.BAD_REQUEST)
    return ApiJsonResponse(status, HTTPStatus.OK)


@login_required
@ajax_request()
def vote_comment(request: HttpRequest, pk: int, comment_pk: int) -> HttpResponse:
    """Function to upvote a Comment with AJAX.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck
        comment_pk (int): Id of the target comment

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """
    try:
        comment = Comment.objects.get(pk=comment_pk, deck__pk=pk)
        comment_vote = CommentVote.objects.get(user=request.user, comment=comment)
        comment_vote.delete()
        comment.vote_count = F("vote_count") - 1
        comment.save()
        status = {"deleted": True}
    except CommentVote.DoesNotExist:
        CommentVote.objects.create(user=request.user, comment=comment)
        comment.vote_count = F("vote_count") + 1
        comment.save()
        status = {"created": True}
    except Comment.DoesNotExist:
        return ApiJsonResponse(_("Comment not found"), HTTPStatus.NOT_FOUND)

    return ApiJsonResponse(status, HTTPStatus.OK)


@login_required
@ajax_request()
def delete_comment(request: HttpRequest, pk: int, comment_pk: int) -> HttpResponse:
    """Function to delete a Comment with AJAX.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck
        comment_pk (int): Id of the target comment

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """
    try:
        deck = Deck.objects.get(pk=pk)
        comment = Comment.objects.get(pk=comment_pk, deck=deck, user=request.user)
        comment.delete()
        deck.comment_count = F("comment_count") - 1
        deck.save(update_fields=["comment_count"])

        status = {"deleted": True}
    except Comment.DoesNotExist:
        return ApiJsonResponse(_("Comment not found"), HTTPStatus.NOT_FOUND)
    except Deck.DoesNotExist:
        return ApiJsonResponse(_("Deck not found"), HTTPStatus.NOT_FOUND)

    return ApiJsonResponse(status, HTTPStatus.OK)


@login_required
@ajax_request()
def create_private_link(request: HttpRequest, pk: int) -> HttpResponse:
    """Function to create a PrivateLink with AJAX.
    Ideally it should be moved to the API app.

    Args:
        request (HttpRequest): Received request
        pk (int): Id of the target deck

    Returns:
        HttpResponse: A JSON response indicating whether the request succeeded or not.
    """
    try:
        # Retrieve the referenced Deck
        deck = Deck.objects.get(pk=pk, owner=request.user)
        if deck.is_public:
            return JsonResponse(
                {
                    "error": {
                        "code": HTTPStatus.BAD_REQUEST,
                        "message": _("Invalid request"),
                    }
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        pl, created = PrivateLink.objects.get_or_create(deck=deck)
        status = {"created": created, "link": pl.get_absolute_url()}

    except Deck.DoesNotExist:
        return JsonResponse(
            {"error": {"code": HTTPStatus.NOT_FOUND, "message": _("Deck not found")}},
            status=HTTPStatus.NOT_FOUND,
        )
    return JsonResponse({"data": status}, status=HTTPStatus.OK)


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
            self.deck = Deck.objects.get(pk=self.kwargs["pk"], owner=self.request.user)
            self.deck.name = form.cleaned_data["name"]
            self.deck.description = form.cleaned_data["description"]
            self.deck.is_public = form.cleaned_data["is_public"]
            self.deck.save()
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
        return self.deck.get_absolute_url()


class UpdateTagsFormView(LoginRequiredMixin, FormView):
    template_name = "decks/deck_detail.html"
    form_class = DeckTagsForm

    def form_valid(self, form: DeckTagsForm) -> HttpResponse:
        try:
            self.deck = Deck.objects.get(pk=self.kwargs["pk"], owner=self.request.user)
            print(form.cleaned_data["tags"])
            self.deck.tags.set(form.cleaned_data["tags"])
        except Deck.DoesNotExist:
            raise PermissionDenied
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.deck.get_absolute_url()


class CreateCommentFormView(LoginRequiredMixin, FormView):
    """View to create a Comment for a Deck."""

    template_name = "decks/deck_detail.html"
    form_class = CommentForm

    def form_valid(self, form: CommentForm) -> HttpResponse:
        """If the input data is valid, create a new Comment.

        Args:
            form (CommentForm): The form filed by the user.

        Returns:
            HttpResponse: The response.
        """
        # Retrieve the Deck by ID and the user, to ensure ownership
        try:
            self.deck = Deck.objects.get(pk=self.kwargs["pk"])
            Comment.objects.create(
                user=self.request.user, deck=self.deck, body=form.cleaned_data["body"]
            )
            self.deck.comment_count = F("comment_count") + 1

            self.deck.save(update_fields=["comment_count"])

            return super().form_valid(form)
        except Deck.DoesNotExist:
            raise Http404

    def get_success_url(self) -> str:
        """Return the redirect URL for a successful update.
        Redirect to the Deck's detail view.

        Returns:
            str: The Deck's detail endpoint.
        """
        return self.deck.get_absolute_url()


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
        self.filter_sets = None

        # Retrieve the text query and search by name
        query = self.request.GET.get("query")
        if query:
            qs, query_tags, has_reference = parse_card_query_syntax(qs, query)
            self.query_tags = query_tags
            if has_reference:
                return qs
        else:
            self.query_tags = None

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
        else:
            filters &= ~Q(rarity=Card.Rarity.UNIQUE)

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

        # Retrieve the Set filters.
        # If any value is invalid, this filter will not be applied.
        card_sets = self.request.GET.get("set")
        if card_sets:
            self.filter_sets = Set.objects.filter(code__in=card_sets.split(","))
            filters &= Q(set__in=self.filter_sets)

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
                    fields = "stats__main_cost"
                else:
                    fields = "stats__recall_cost"

                mana_order = F(fields)
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
            edit_deck_id = self.request.GET.get("deck")
            if edit_deck_id:
                try:
                    context["edit_deck"] = Deck.objects.filter(
                        pk=edit_deck_id, owner=self.request.user
                    ).get()
                    context["edit_deck_cards"] = (
                        CardInDeck.objects.filter(deck=context["edit_deck"])
                        .select_related("card")
                        .order_by("card__reference")
                    )
                except Deck.DoesNotExist:
                    pass

        checked_filters = []
        for filter in ["faction", "rarity", "type", "set"]:
            if filter in self.request.GET:
                checked_filters += self.request.GET[filter].split(",")
        context["checked_filters"] = checked_filters
        context["checked_sets"] = self.filter_sets
        context["sets"] = Set.objects.all()
        if "order" in self.request.GET:
            context["order"] = self.request.GET["order"]
        if "query" in self.request.GET:
            context["query"] = self.request.GET.get("query")
            context["query_tags"] = self.query_tags

        return context


@login_required
def import_card(request):
    context = {}
    form = None
    if request.method == "POST":
        form = CardImportForm(request.POST)
        if form.is_valid():
            reference = form.cleaned_data["reference"]
            try:
                card = import_unique_card(reference)
                context["message"] = _(
                    "The card '%(card_name)s' (%(reference)s) was successfully imported."
                ) % {"card_name": card.name, "reference": reference}
                form = None
                context["card"] = card
            except CardAlreadyExists:
                card = Card.objects.get(reference=reference)
                context["message"] = _(
                    "This unique version of '%(card_name)s' (%(reference)s) already exists in the database."
                ) % {"card_name": card.name, "reference": reference}
                form = None
                context["card"] = card
            except AlteredAPIError as e:
                if e.status_code == HTTPStatus.UNAUTHORIZED:
                    form.add_error(
                        "reference",
                        _("The card '%(reference)s' is not public")
                        % {"reference": reference},
                    )
                else:
                    form.add_error(
                        "reference", _("Failed to fetch the card on the official API.")
                    )

    context["form"] = (
        form
        if form
        else CardImportForm(initial={"reference": request.GET.get("reference")})
    )

    return render(request, "decks/import_card.html", context)
