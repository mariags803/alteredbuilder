from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.detail import DetailView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView

from decks.models import Deck
from profiles.forms import UserProfileForm
from profiles.models import Follow, UserProfile


class ProfileListView(ListView):
    queryset = UserProfile.objects.select_related("user").order_by("-created_at")[:5]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        return context


class ProfileDetailView(DetailView):

    queryset = get_user_model().objects.select_related("profile")
    context_object_name = "builder"
    slug_field = "profile__code"
    slug_url_kwarg = "code"
    template_name = "profiles/userprofile_detail.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context["deck_list"] = Deck.objects.filter(owner=self.object, is_public=True)

        if self.request.user.is_authenticated:
            context["is_followed"] = Follow.objects.filter(
                follower=self.request.user, followed=self.object
            ).exists()

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
    Follow.objects.get_or_create(follower=request.user, followed=builder_profile.user)
    return redirect(builder_profile.get_absolute_url())


@login_required
def unfollow_user(request, code):
    builder_profile = get_object_or_404(UserProfile, code=code)
    follow = Follow.objects.filter(
        follower=request.user, followed=builder_profile.user
    ).first()
    if follow:
        follow.delete()
    return redirect(builder_profile.get_absolute_url())
