from django.contrib import admin
from money.models import Transaction, Wallet


class WalletAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "owner",
        "owner_name",
        "stripe_connect_account",
    )
    list_display = (
        "id",
        "owner",
        "owner_name",
        "balance",
        "usd_value",
        "stripe_connect_account",
    )
    search_fields = (
        "id",
        "owner__display_name",
        "owner__id",
    )
    actions = None

    @admin.display()
    def owner_name(self, obj: Wallet):
        return obj.owner.display_name


class TransactionAdmin(admin.ModelAdmin):
    readonly_fields = (
        "id",
        "type",
        "recipient",
        "sender",
        "coin_amount",
        "usd_value",
        "created_at",
    )
    list_display = (
        "id",
        "type",
        "recipient",
        "sender",
        "coin_amount",
        "usd_value",
        "created_at",
    )
    search_fields = (
        "id",
        "type",
        "recipient__display_name",
        "sender__display_name",
        "recipient__id",
        "sender__id",
    )
    sortable_by = ("created_at",)
    ordering = ("created_at",)
    actions = None


admin.site.register(Wallet, WalletAdmin)
admin.site.register(Transaction, TransactionAdmin)
