from django.conf import settings
from django.contrib import admin
from moka_profile.models import MokaProfile


class MokaProfileAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "email",
        "firebase_uid",
        "thumbnail",
        "balance",
        "wallet",
    )
    list_display = (
        "id",
        "display_name",
        "email",
        "firebase_uid",
        "payout_status",
        "created_at",
        "is_banned",
    )
    search_fields = (
        "firebase_uid",
        "id",
        "display_name",
    )
    sortable_by = ("created_at",)
    actions = None

    def view_on_site(self, obj: MokaProfile):
        return settings.CLIENT_URL + f"/app/profile/{obj.id}"

    @admin.display(description="Email")
    def email(self, obj: MokaProfile):
        return obj.get_email()

    def balance(self, obj: MokaProfile):
        return obj.get_balance()


admin.site.register(MokaProfile, MokaProfileAdmin)
