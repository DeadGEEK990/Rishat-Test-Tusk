from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, OrderViewSet

router = DefaultRouter()
router.register(r"items", ItemViewSet)
router.register(r"orders", OrderViewSet, basename="orders")

urlpatterns = [
    path("", include(router.urls)),
    #path(
     #   "orders/current/",
      #  OrderViewSet.as_view({"get": "current"}),
     #   name="current-order",
   # ),
]
