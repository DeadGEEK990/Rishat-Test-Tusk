from django.shortcuts import render
from django.views import View
from django.conf import settings
import stripe
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


class ProductListView(View):
    def get(self, request):
        return render(
            request,
            "payment/product_list.html",
            {
                "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            },
        )


class CartView(View):
    def get(self, request):
        return render(request, "payment/cart.html", {
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        })


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get("id")

        if session_id:
            from .models import OrderModel
            try:
                order = OrderModel.objects.get(stripe_checkout_id=session_id)
                order.payment_status = 'paid'
                order.save()
            except OrderModel.DoesNotExist:
                pass

    return HttpResponse(status=200)
