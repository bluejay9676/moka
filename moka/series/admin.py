from django.conf import settings
from django.contrib import admin
from episode.models import Episode
from series.models import Series


class EpisodeInline(admin.TabularInline):
    model = Episode
    fields = (
        "id",
        "title",
        "episode_number",
    )
    readonly_fields = ("title",)
    can_delete = False
    ordering = ("-episode_number",)
    show_change_link = True


class SeriesAdmin(admin.ModelAdmin):
    inlines = [EpisodeInline]
    readonly_fields = (
        "id",
        "title",
        "owner",
        "thumbnail",
        "description",
        "status",
        "publish_date",
        "created_at",
        "updated_at",
    )
    list_display = (
        "id",
        "title",
        "owner_name",
        "owner_email",
        "status",
        "created_at",
        "is_banned",
    )
    search_fields = (
        "id",
        "title",
        "owner__display_name",
        "owner__id",
    )
    sortable_by = ("created_at",)
    actions = None

    def view_on_site(self, obj: Series):
        return settings.CLIENT_URL + f"/app/series/{obj.id}"

    @admin.display()
    def owner_name(self, obj: Series):
        return obj.owner.display_name

    @admin.display()
    def owner_email(self, obj: Series):
        return obj.owner.get_email()


admin.site.register(Series, SeriesAdmin)
