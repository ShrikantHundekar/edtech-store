import type { ProductType, GSTBreakdown } from './product';

export interface CartLineItem {
  product_id: number;
  title: string;
  product_type: ProductType;
  academic_class_id?: number;
  subject_id?: number;
  chapter_id?: number;
  base_price_paise: number;
  base_price_inr: number;
  upgrade_credit_paise: number;
  upgrade_credit_inr: number;
  final_price_paise: number;
  final_price_inr: number;
  currency: string;
  renewal_preview?: {
    class_id: number;
    duration_days: number;
    is_renewal: boolean;
    remaining_active_days: number;
    valid_from: string;
    valid_until: string;
  };
  owned_chapters_count?: number;
  total_credit_available_paise?: number;
}

export interface CartPricing {
  total_base_price_paise: number;
  total_base_price_inr: number;
  total_upgrade_credit_paise: number;
  total_upgrade_credit_inr: number;
  subtotal_paise: number;
  subtotal_inr: number;
  currency: string;
  gst_breakdown: GSTBreakdown;
}

export interface ServerCartResponse {
  valid: boolean;
  message?: string;
  items_count: number;
  items: CartLineItem[];
  pricing: CartPricing;
  errors?: string[];
}

export interface AppliedCoupon {
  code: string;
  discount_type: 'PERCENTAGE' | 'FLAT';
  discount_value: number;
  discount_paise: number;
  discount_inr: number;
  subtotal_paise: number;
  subtotal_inr: number;
  net_payable_paise: number;
  net_payable_inr: number;
  gst_breakdown: GSTBreakdown;
}
