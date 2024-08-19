from django.contrib import admin

from profiles.models import Follow, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user"]
    search_fields = ["user__username"]
    readonly_fields = ["user", "altered_handle"]


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ["__str__"]
    readonly_fields = ["follower", "followed"]