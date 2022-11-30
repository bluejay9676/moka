from django.conf import settings
from django.contrib import admin
from episode.models import Episode, PurchaseEpisode
from image.models import Page


class PageInline(admin.TabularInline):
    model = Page
    fields = (
        "id",
        "status",
        "external_id",
        "storage",
        "owner",
        "order",
    )
    readonly_fields = (
        "external_id",
        "storage",
        "owner",
        "order",
    )
    can_delete = False
    ordering = ("order",)
    show_change_link = True


class EpisodeAdmin(admin.ModelAdmin):
    inlines = [PageInline]
    readonly_fields = (
        "id",
        "series",
        "series_title",
        "thumbnail",
        "title",
        "status",
        "like_count",
        "publish_date",
        "release_scheduled_date",
        "owner",
    )
    list_display = (
        "id",
        "title",
        "series_title",
        "like_count",
        "view_count",
        "status",
        "publish_date",
        "release_scheduled_date",
        "is_banned",
    )
    search_fields = (
        "id",
        "title",
    )
    sortable_by = (
        "publish_date",
        "release_scheduled_date",
    )
    actions = None

    def view_on_site(self, obj: Episode):
        return settings.CLIENT_URL + f"/app/episode/{obj.id}"

    @admin.display()
    def like_count(self, obj: Episode):
        return obj.get_likes()

    @admin.display()
    def series_title(self, obj: Episode):
        return obj.series.title

    @admin.display()
    def view_count(self, obj: Episode):
        return obj.get_views()

    @admin.display()
    def owner(self, obj: Episode):
        return obj.series.owner


class PurchaseEpisodeAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "episode",
        "profile",
        "episode_title",
        "profile_display_name",
        "episode_price",
        "episode_is_premium",
        "episode_status",
    )
    list_display = (
        "id",
        "episode_title",
        "profile_display_name",
        "created_at",
    )
    search_fields = (
        "episode__id",
        "episode__title",
        "profile__display_name",
        "profile__id",
    )
    sortable_by = ("created_at",)
    actions = None

    @admin.display()
    def episode_title(self, obj: PurchaseEpisode):
        return f"{obj.episode.title} ({obj.episode.id})"

    @admin.display()
    def episode_price(self, obj: PurchaseEpisode):
        return obj.episode.price

    @admin.display()
    def episode_is_premium(self, obj: PurchaseEpisode):
        return obj.episode.is_premium

    @admin.display()
    def episode_status(self, obj: PurchaseEpisode):
        return obj.episode.status

    @admin.display()
    def profile_display_name(self, obj: PurchaseEpisode):
        return f"{obj.profile.display_name} ({obj.profile.id})"


admin.site.register(Episode, EpisodeAdmin)
admin.site.register(PurchaseEpisode, PurchaseEpisodeAdmin)
