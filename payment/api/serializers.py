from rest_framework import serializers
from ..models import ItemModel, OrderModel, OrderItemModel


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemModel
        fields = ["id", "name", "description", "price", "currency"]


class OrderItemSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(queryset=ItemModel.objects.all())
    order = serializers.PrimaryKeyRelatedField(
        queryset=OrderModel.objects.all(), required=False
    )  # Добавляем поле order

    class Meta:
        model = OrderItemModel
        fields = ["id", "item", "quantity", "order"]
        read_only_fields = ["id"]
        extra_kwargs = {"quantity": {"min_value": 1}}

    def create(self, validated_data):
        validated_data["order"] = self.context["order"]
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    items = serializers.SerializerMethodField()

    class Meta:
        model = OrderModel
        fields = [
            "id",
            "created_at",
            "order_items",
            "items",
            "total_price",
            "currency",
            "payment_status",
        ]
        read_only_fields = fields

    def get_items(self, obj):
        return [
            {
                "id": item.id,
                "item_id": item.item.id,
                "name": item.item.name,
                "price": str(item.item.price),
                "currency": item.item.currency,
                "quantity": item.quantity,
            }
            for item in obj.order_items.all()
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderModel
        fields = []  # ничего не ожидает

    def create(self, validated_data):
        request = self.context.get("request")
        if request and not request.session.session_key:
            request.session.create()

        order = OrderModel.objects.create(session_key=request.session.session_key)
        return order
