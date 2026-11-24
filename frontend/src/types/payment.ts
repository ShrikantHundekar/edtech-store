export interface OrderCreateResponse {
  id: number;
  order_number: string;
  status: string;
  gross_amount_paise: number;
  gross_amount_inr: number;
  upgrade_discount_paise: number;
  upgrade_discount_inr: number;
  coupon_code: string | null;
  coupon_discount_paise: number;
  coupon_discount_inr: number;
  taxable_base_paise: number;
  taxable_base_inr: number;
  gst_amount_paise: number;
  gst_amount_inr: number;
  net_payable_paise: number;
  net_payable_inr: number;
  amount_paise: number;
  currency: string;
  razorpay_order_id: string | null;
  razorpay_key_id: string;
  items: Array<{
    id: number;
    product: number;
    product_title: string;
    product_type: string;
    unit_price_inr: number;
    upgrade_credit_inr: number;
    net_price_inr: number;
  }>;
}

export interface PaymentVerifyPayload {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

export interface PaymentVerifyResponse {
  success: boolean;
  order_id?: number;
  order_number?: string;
  status?: string;
  message?: string;
  entitlements_count?: number;
  error?: string;
}

export interface RazorpayResponse {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
}

export interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  image?: string;
  order_id: string;
  handler: (response: RazorpayResponse) => void;
  prefill?: {
    name?: string;
    email?: string;
    contact?: string;
  };
  theme?: {
    color?: string;
  };
  modal?: {
    ondismiss?: () => void;
  };
}

declare global {
  interface Window {
    Razorpay: new (options: RazorpayOptions) => {
      open: () => void;
      on: (event: string, handler: (response: unknown) => void) => void;
    };
  }
}
