export interface OrderItem {
  id: number;
  product: number;
  product_title: string;
  product_type: string;
  unit_price_paise: number;
  unit_price_inr: number;
  upgrade_credit_paise: number;
  upgrade_credit_inr: number;
  net_price_paise: number;
  net_price_inr: number;
  created_at: string;
}

export interface OrderGSTBreakdown {
  price_inclusive_paise: number;
  base_taxable_paise: number;
  total_gst_paise: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  price_inclusive_inr: number;
  base_taxable_inr: number;
  total_gst_inr: number;
  cgst_inr: number;
  sgst_inr: number;
  igst_inr: number;
  gst_rate_percent: number;
}

export interface Order {
  id: number;
  order_number: string;
  user: number;
  customer_name?: string;
  customer_email?: string;
  status: 'PENDING' | 'PAID' | 'FAILED';
  gross_amount_paise: number;
  gross_amount_inr: number;
  upgrade_discount_paise: number;
  upgrade_discount_inr: number;
  coupon?: number | null;
  coupon_code?: string | null;
  coupon_discount_paise: number;
  coupon_discount_inr: number;
  taxable_base_paise: number;
  taxable_base_inr: number;
  gst_amount_paise: number;
  gst_amount_inr: number;
  net_payable_paise: number;
  net_payable_inr: number;
  currency: string;
  razorpay_order_id?: string | null;
  razorpay_payment_id?: string | null;
  payment_method?: string | null;
  gst_breakdown?: OrderGSTBreakdown;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
}
