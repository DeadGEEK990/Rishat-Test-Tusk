"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import path, include
from payment.views import stripe_webhook


urlpatterns = [
    path("", lambda request: redirect("products/"), name="root_redirect"),
    path("order/success/", lambda request: HttpResponseRedirect('/products/'), name="order-success"),
    path("admin/", admin.site.urls),
    path("", include("payment.urls")),
    path("api/", include("payment.api.urls")),
    path('webhooks/stripe/', stripe_webhook, name='stripe-webhook'),
]
