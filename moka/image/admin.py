from django.contrib import admin
from django.utils.html import format_html
from image.models import Page, Thumbnail


class ThumbnailAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "owner",
        "owner_name",
        "external_id",
        "storage",
        "status",
        "created_at",
        "display_url",
    )
    list_display = (
        "id",
        "owner",
        "owner_name",
        "external_id",
        "storage",
        "status",
        "created_at",
    )
    search_fields = (
        "id",
        "owner__display_name",
        "owner__id",
    )
    sortable_by = ("created_at",)
    actions = None

    @admin.display()
    def owner_name(self, obj: Thumbnail):
        return obj.owner.display_name

    @admin.display()
    def display_url(self, obj: Thumbnail):
        return format_html("<a href='{url}'>{url}</a>", url=obj.signed_cookie)


class PageAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "owner",
        "owner_name",
        "episode",
        "episode_title",
        "external_id",
        "order",
        "storage",
        "status",
        "created_at",
        "display_url",
    )
    list_display = (
        "id",
        "owner",
        "owner_name",
        "episode_title",
        "external_id",
        "storage",
        "status",
        "created_at",
    )
    search_fields = (
        "id",
        "owner__display_name",
        "owner__id",
    )
    sortable_by = ("created_at",)
    actions = None

    @admin.display()
    def owner_name(self, obj: Page):
        return obj.owner.display_name

    @admin.display()
    def episode_title(self, obj: Page):
        return obj.episode.title

    @admin.display()
    def display_url(self, obj: Page):
        return format_html("<a href='{url}'>{url}</a>", url=obj.signed_cookie)


admin.site.register(Thumbnail, ThumbnailAdmin)
admin.site.register(Page, PageAdmin)
