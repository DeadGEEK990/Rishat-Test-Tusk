from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

CURRENCY_CHOICES = [
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("RUB", "Russian Ruble"),
]

PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("paid", "Paid"),
    ("failed", "Failed"),
]


class ItemModel(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="RUB")
    stripe_product_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_price_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.price} {self.currency}"

    def sync_with_stripe(self):
        try:
            if self.stripe_product_id:
                product = stripe.Product.modify(
                    self.stripe_product_id, name=self.name, description=self.description
                )
            else:
                product = stripe.Product.create(
                    name=self.name, description=self.description
                )
                self.stripe_product_id = product.id

            if self.stripe_price_id:
                try:
                    stripe.Price.modify(self.stripe_price_id, active=False)
                except stripe.error.InvalidRequestError:
                    pass

            price = stripe.Price.create(
                product=self.stripe_product_id,
                unit_amount=int(self.price * 100),
                currency=self.currency.lower(),
            )
            self.stripe_price_id = price.id
            self.save(update_fields=["stripe_product_id", "stripe_price_id"])

            return product, price

        except stripe.error.StripeError as e:
            raise


class OrderModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    items = models.ManyToManyField(ItemModel, through="OrderItemModel")
    stripe_checkout_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    def clean(self):
        if self.pk:
            currencies = {item.currency for item in self.items.all()}
            if len(currencies) > 1:
                raise ValidationError("All items must have the same currency")

    def total_price(self):
        return sum(item.item_price() for item in self.order_items.all())

    def currency(self):
        if not self.order_items.exists():
            return None
        return self.order_items.first().item.currency

    def create_stripe_checkout_session(self, success_url, cancel_url):
        self.clean()

        line_items = []
        for order_item in self.order_items.select_related("item"):
            if not order_item.item.stripe_price_id:
                order_item.item.sync_with_stripe()

            line_items.append(
                {
                    "price": order_item.item.stripe_price_id,
                    "quantity": order_item.quantity,
                }
            )

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=line_items,
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"order_id": str(self.id)},
            )

            self.stripe_checkout_id = session.id
            self.save(update_fields=["stripe_checkout_id"])
            return session

        except stripe.error.StripeError as e:
            raise


class OrderItemModel(models.Model):
    order = models.ForeignKey(
        OrderModel, on_delete=models.CASCADE, related_name="order_items"
    )
    item = models.ForeignKey(ItemModel, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def clean(self):
        if self.quantity < 1:
            raise ValidationError("Quantity must be at least 1")

        if self.order_id and self.item_id:
            other_items_currencies = (
                OrderItemModel.objects.filter(order=self.order)
                .exclude(id=self.pk if self.pk else None)
                .values_list("item__currency", flat=True)
                .distinct()
            )

            if (
                other_items_currencies
                and self.item.currency not in other_items_currencies
            ):
                raise ValidationError("Item currency must match existing order items")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def item_price(self):
        return self.item.price * self.quantity


@receiver(post_save, sender=ItemModel)
def sync_item_with_stripe(sender, instance, **kwargs):
    if kwargs.get("created", False):
        instance.sync_with_stripe()
    else:
        try:
            old_price = ItemModel.objects.get(pk=instance.pk).price
            if old_price != instance.price:
                instance.sync_with_stripe()
        except ItemModel.DoesNotExist:
            pass
