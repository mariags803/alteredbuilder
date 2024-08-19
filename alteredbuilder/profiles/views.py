from collections import defaultdict
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Exists, F, OuterRef, Q, Sum
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import localtime
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from decks.models import Deck, LovePoint
from profiles.forms import UserProfileForm
from profiles.models import Follow, UserProfile


class ProfileListView(ListView):
    template_name = "profiles/userprofile_list.html"
    context_object_name = "latest_users"
    USER_COUNT_DISPLAY = 10

    def get_queryset(self) -> QuerySet[Any]:
        qs = (
            get_user_model()
            .objects.select_related("profile")
            .order_by("-date_joined")[: self.USER_COUNT_DISPLAY]
        )

        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("pk"), follower=self.request.user
                    )
                )
            )
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        most_viewed_users = (
            get_user_model()
            .objects.alias(total_hits=Sum("deck__hit_count_generic__hits"))
            .annotate(deck_count=Count("deck", filter=Q(deck__is_public=True)))
            .select_related("profile")
            .order_by(F("total_hits").desc(nulls_last=True))[: self.USER_COUNT_DISPLAY]
        )

        most_followed_users = (
            get_user_model()
            .objects.annotate(follower_count=Count("followers"))
            .filter(follower_count__gt=0)
            .select_related("profile")
            .order_by("-follower_count")[: self.USER_COUNT_DISPLAY]
        )

        if self.request.user.is_authenticated:
            most_viewed_users = most_viewed_users.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("pk"), follower=self.request.user
                    )
                )
            )
            most_followed_users = most_followed_users.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("pk"), follower=self.request.user
                    )
                )
            )
        context["most_viewed_users"] = most_viewed_users
        context["most_followed_users"] = most_followed_users
        timelapse = localtime() - timedelta(days=1)
        context["recent_users_count"] = (
            get_user_model().objects.filter(date_joined__gte=timelapse).count()
        )

        return context


class FollowersListView(ListView):
    template_name = "profiles/followers_list.html"
    context_object_name = "followers"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[Any]:
        self.builder = get_user_model().objects.get(profile__code=self.kwargs["code"])
        qs = Follow.objects.filter(followed=self.builder).select_related(
            "follower__profile"
        )

        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("follower"), follower=self.request.user
                    )
                )
            )

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["builder"] = self.builder

        followed_users = Follow.objects.filter(follower=self.builder).select_related(
            "followed__profile", "follower__profile"
        )
        if self.request.user.is_authenticated:
            followed_users = followed_users.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        followed=OuterRef("followed"), follower=self.request.user
                    )
                )
            )
        context["followed_users"] = followed_users
        return context


class ProfileDetailView(DetailView):

    context_object_name = "builder"
    slug_field = "profile__code"
    slug_url_kwarg = "code"
    template_name = "profiles/userprofile_detail.html"

    def get_queryset(self) -> QuerySet[Any]:
        qs = (
            get_user_model()
            .objects.select_related("profile")
            .annotate(
                follower_count=Count("followers", distinct=True),
                following_count=Count("following", distinct=True),
            )
        )

        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_followed=Exists(
                    Follow.objects.filter(
                        follower=self.request.user, followed=OuterRef("pk")
                    )
                )
            )

        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        deck_list = Deck.objects.filter(
            owner=self.object, is_public=True
        ).select_related("hero")

        if self.request.user.is_authenticated:
            deck_list = deck_list.annotate(
                is_loved=Exists(
                    LovePoint.objects.filter(
                        deck=OuterRef("pk"), user=self.request.user
                    )
                )
            )

        context["deck_list"] = deck_list

        faction_distribution = defaultdict(int)
        for deck in deck_list:
            if deck.hero:
                faction_distribution[deck.hero.get_faction_display()] += 1

        context["faction_distribution"] = faction_distribution

        return context


class EditProfileFormView(LoginRequiredMixin, FormView):
    template_name = "profiles/edit_profile.html"
    form_class = UserProfileForm

    def get_initial(self) -> dict[str, Any]:
        initial = super().get_initial()
        for attr in self.form_class.base_fields:
            initial[attr] = getattr(self.request.user.profile, attr)
        return initial

    def form_valid(self, form: UserProfileForm):
        profile = self.request.user.profile
        for attr in form.fields:
            setattr(profile, attr, form.cleaned_data[attr])
        profile.save()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return self.request.user.profile.get_absolute_url()


@login_required
def follow_user(request, code):
    builder_profile = get_object_or_404(UserProfile, code=code)
    if request.user != builder_profile.user:
        Follow.objects.get_or_create(
            follower=request.user, followed=builder_profile.user
        )
    return redirect(builder_profile.get_absolute_url())


@login_required
def unfollow_user(request, code):
    builder_profile = get_object_or_404(UserProfile, code=code)
    Follow.objects.filter(follower=request.user, followed=builder_profile.user).delete()
    return redirect(builder_profile.get_absolute_url())