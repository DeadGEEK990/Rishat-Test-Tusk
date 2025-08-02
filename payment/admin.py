from django.contrib import admin
from django.utils.html import format_html
from .models import ItemModel, OrderModel, OrderItemModel


@admin.register(ItemModel)
class ItemAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "currency"]
    search_fields = ["name", "description"]
    list_filter = ["currency"]
    actions = ["sync_with_stripe"]

    def stripe_status(self, obj):
        if obj.stripe_product_id and obj.stripe_price_id:
            return format_html('<span style="color: green;">✓ Synced</span>')
        return format_html('<span style="color: red;">✗ Not synced</span>')

    stripe_status.short_description = "Stripe Status"

    def sync_with_stripe(self, request, queryset):
        for item in queryset:
            try:
                item.sync_with_stripe()
                self.message_user(
                    request, f"Successfully synced {item.name} with Stripe"
                )
            except Exception as e:
                self.message_user(
                    request, f"Error syncing {item.name}: {str(e)}", level="error"
                )

    sync_with_stripe.short_description = "Sync selected items with Stripe"


class OrderItemInline(admin.TabularInline):
    model = OrderItemModel
    extra = 0
    readonly_fields = ['item', 'quantity', 'item_price']
    fields = ['item', 'quantity', 'item_price']
    can_delete = False

    def item_price(self, obj):
        return f"{obj.item_price()} {obj.item.currency}"

    item_price.short_description = "Price"


@admin.register(OrderModel)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'created_at',
        'payment_status',
        'display_items',
        'total_price_with_currency',
        'stripe_checkout_link',
        'stripe_payment_status'
    ]
    list_filter = ['payment_status', 'created_at']
    search_fields = ['id', 'stripe_checkout_id', 'stripe_payment_intent_id']
    readonly_fields = [
        'created_at',
        'payment_status',
        'stripe_checkout_id',
        'stripe_payment_intent_id',
        'session_key',
        'total_price_with_currency',
        'stripe_checkout_link',
    ]
    inlines = [OrderItemInline]
    actions = None

    def display_items(self, obj):
        items = obj.order_items.select_related('item')
        return format_html("<br>".join(
            f"{item.item.name} × {item.quantity}"
            for item in items
        ))

    display_items.short_description = "Items"

    def total_price_with_currency(self, obj):
        if not obj.order_items.exists():
            return "-"
        return f"{obj.total_price()} {obj.currency()}"

    total_price_with_currency.short_description = "Total"

    def stripe_checkout_link(self, obj):
        if not obj.stripe_checkout_id:
            return "-"
        url = f"https://dashboard.stripe.com/test/payments/{obj.stripe_payment_intent_id}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.stripe_checkout_id)

    stripe_checkout_link.short_description = "Stripe Checkout"

    def stripe_payment_status(self, obj):
        if not obj.stripe_payment_intent_id:
            return "-"
        return obj.payment_status.capitalize()

    stripe_payment_status.short_description = "Payment Status"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(OrderItemModel)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_link', 'item_link', 'quantity', 'item_price']
    list_select_related = ['order', 'item']
    readonly_fields = ['order', 'item', 'quantity']
    search_fields = ['order__id', 'item__name']

    def order_link(self, obj):
        url = f"/admin/payment/ordermodel/{obj.order.id}/"
        return format_html('<a href="{}">{}</a>', url, obj.order.id)

    order_link.short_description = "Order"

    def item_link(self, obj):
        url = f"/admin/payment/itemmodel/{obj.item.id}/"
        return format_html('<a href="{}">{}</a>', url, obj.item.name)

    item_link.short_description = "Item"

    def item_price(self, obj):
        return f"{obj.item_price()} {obj.item.currency}"

    item_price.short_description = "Price"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
