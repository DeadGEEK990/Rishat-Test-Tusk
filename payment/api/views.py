from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import ItemModel, OrderModel, OrderItemModel
from .serializers import (
    ItemSerializer,
    OrderSerializer,
    OrderCreateSerializer,
    OrderItemSerializer,
)


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ItemModel.objects.all()
    serializer_class = ItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = OrderModel.objects.prefetch_related("order_items__item")
    serializer_class = OrderSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        return OrderModel.objects.prefetch_related(
            'order_items',
            'order_items__item'
        )

    def create(self, request, *args, **kwargs):
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        order = OrderModel.objects.filter(session_key=session_key, payment_status="pending").first()

        if order:
            serializer = OrderSerializer(order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        order = OrderModel.objects.create(session_key=session_key, payment_status="pending")
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def current(self, request):
        if not request.session.session_key:
            request.session.create()

        try:
            order = (
                OrderModel.objects.filter(
                    session_key=request.session.session_key, payment_status="pending"
                )
                .prefetch_related("order_items__item")
                .first()
            )

            if not order:
                return Response({"detail": "Cart is empty"}, status=status.HTTP_200_OK)

            request.session["order_id"] = order.id
            request.session.modified = True

            serializer = self.get_serializer(order)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def add_item(self, request, pk=None):
        order = self.get_object()
        serializer = OrderItemSerializer(
            data={
                "item": request.data.get("item_id"),
                "quantity": request.data.get("quantity", 1),
            },
            context={"order": order},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="remove_item/(?P<item_pk>[^/.]+)")
    def remove_item(self, request, pk=None, item_pk=None):
        order = self.get_object()
        OrderItemModel.objects.filter(order=order, pk=item_pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        order = self.get_object()
        try:
            session = order.create_stripe_checkout_session(
                success_url=request.data.get("success_url"),
                cancel_url=request.data.get("cancel_url"),
            )
            return Response({"checkout_url": session.url})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
