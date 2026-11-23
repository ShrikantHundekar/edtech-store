export type ProductType =
  | 'CHAPTER_NOTES'
  | 'SUBJECT_PACK'
  | 'MONTHLY_PASS'
  | 'ANNUAL_PASS'
  | 'BUNDLE'
  | 'FREE_SAMPLE';

export type PurchaseState = 'BUY' | 'OWNED' | 'UPGRADE' | 'UNLOCKED_VIA_PASS' | 'UNAVAILABLE';

export interface GSTBreakdown {
  price_inclusive_paise: number;
  base_taxable_paise: number;
  total_gst_paise: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  is_interstate: boolean;
  gst_rate_percent: number;
  price_inclusive_inr: number;
  base_taxable_inr: number;
  total_gst_inr: number;
  cgst_inr: number;
  sgst_inr: number;
  igst_inr: number;
}

export interface ProductInclusion {
  target_type: 'CHAPTER' | 'SUBJECT';
  id: number;
  title: string;
  chapter_number?: number;
  subject?: string;
  is_free_sample?: boolean;
}

export interface ProductPrice {
  amount_paise: number;
  amount_inr: number;
  valid_from?: string;
  valid_until?: string;
  is_current?: boolean;
}

export interface Product {
  id: number;
  title: string;
  slug: string;
  product_type: ProductType;
  description?: string;
  thumbnail_url?: string;
  board?: number;
  board_name?: string;
  academic_class?: number;
  class_name?: string;
  subject?: number;
  subject_name?: string;
  chapter?: number;
  chapter_title?: string;
  is_active: boolean;
  current_price_paise: number;
  current_price_inr: number;
  access_duration: string;
  pass_duration_days?: number | null;
  gst_breakdown: GSTBreakdown;
  inclusions: ProductInclusion[];
}

export interface ProductOwnershipResponse {
  product_id: number;
  title: string;
  product_type: ProductType;
  purchase_state: PurchaseState;
  can_purchase: boolean;
  reason: string;
  renewal_preview?: {
    class_id: number;
    duration_days: number;
    is_renewal: boolean;
    remaining_active_days: number;
    valid_from: string;
    valid_until: string;
  };
}

export interface OwnedChapterCredit {
  chapter_id: number;
  chapter_title: string;
  chapter_number: number;
  credit_paise: number;
  credit_inr: number;
}

export interface ProductPriceCalculation {
  product_id: number;
  title: string;
  product_type: ProductType;
  base_price_paise: number;
  base_price_inr: number;
  upgrade_credit_paise: number;
  upgrade_credit_inr: number;
  total_credit_available_paise?: number;
  payable_price_paise: number;
  payable_price_inr: number;
  owned_chapters_count: number;
  owned_chapters: OwnedChapterCredit[];
  gst_breakdown: GSTBreakdown;
  renewal_preview?: Record<string, unknown>;
}

export interface CartItem {
  product: Product;
  unit_price_paise: number;
  upgrade_credit_paise: number;
  net_price_paise: number;
}
