import { api } from './api';
import type {
  OrderCreateResponse,
  PaymentVerifyPayload,
  PaymentVerifyResponse,
  RazorpayOptions,
} from '../types/payment';

export const paymentService = {
  /**
   * Create server-authoritative order from current cart items & coupon
   */
  async createOrder(items: number[], couponCode?: string): Promise<OrderCreateResponse> {
    const { data } = await api.post<OrderCreateResponse>('/orders/create/', {
      items,
      coupon_code: couponCode || undefined,
    });
    return data;
  },

  /**
   * Verify Razorpay checkout signature and complete atomic order fulfillment
   */
  async verifyPayment(payload: PaymentVerifyPayload): Promise<PaymentVerifyResponse> {
    const { data } = await api.post<PaymentVerifyResponse>('/payments/verify/', payload);
    return data;
  },

  /**
   * Development & Test helper to simulate UPI / Card checkout signatures
   */
  async simulatePayment(
    razorpayOrderId: string,
    method: 'upi' | 'card' = 'upi',
    fail = false
  ): Promise<PaymentVerifyPayload> {
    const { data } = await api.post<{
      success: boolean;
      razorpay_order_id: string;
      razorpay_payment_id: string;
      razorpay_signature: string;
      error?: string;
    }>('/payments/simulate/', {
      razorpay_order_id: razorpayOrderId,
      method,
      fail,
    });

    if (!data.success) {
      throw new Error(data.error || 'Simulated payment failure');
    }

    return {
      razorpay_order_id: data.razorpay_order_id,
      razorpay_payment_id: data.razorpay_payment_id,
      razorpay_signature: data.razorpay_signature,
    };
  },

  /**
   * Dynamically load Razorpay standard Checkout script if not already in DOM
   */
  loadRazorpaySDK(): Promise<boolean> {
    return new Promise((resolve) => {
      if (typeof window !== 'undefined' && window.Razorpay) {
        resolve(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => {
        console.warn('Razorpay SDK could not be reached (offline or blocked).');
        resolve(false);
      };
      document.body.appendChild(script);
    });
  },

  /**
   * Launch Razorpay Checkout Modal
   */
  openRazorpayModal(options: RazorpayOptions): void {
    if (!window.Razorpay) {
      throw new Error('Razorpay Checkout SDK is not loaded.');
    }
    const rzp = new window.Razorpay(options);
    rzp.open();
  },
};
