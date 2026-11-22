from django.urls import path
from .views import RazorpayWebhookView, RazorpayPaymentVerifyView

urlpatterns = [
    path('webhook/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    path('verify/', RazorpayPaymentVerifyView.as_view(), name='razorpay_verify'),
]
