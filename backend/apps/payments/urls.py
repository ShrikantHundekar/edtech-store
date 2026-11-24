from django.urls import path
from .views import RazorpayWebhookView, RazorpayPaymentVerifyView, RazorpayPaymentSimulateView

urlpatterns = [
    path('webhook/', RazorpayWebhookView.as_view(), name='razorpay_webhook'),
    path('verify/', RazorpayPaymentVerifyView.as_view(), name='razorpay_verify'),
    path('simulate/', RazorpayPaymentSimulateView.as_view(), name='razorpay_simulate'),
]
