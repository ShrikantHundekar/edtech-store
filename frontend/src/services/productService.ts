import { api } from './api';
import type {
  Product,
  ProductOwnershipResponse,
  ProductPriceCalculation,
  ProductType,
} from '../types/product';

export interface ProductFilterParams {
  product_type?: ProductType;
  board_id?: number | string;
  class_id?: number | string;
  subject_id?: number | string;
  chapter_id?: number | string;
}

export interface CartValidationResponse {
  valid: boolean;
  message?: string;
  items_count?: number;
  items?: Array<{
    product_id: number;
    title: string;
    product_type: ProductType;
    unit_price_paise: number;
    upgrade_credit_paise: number;
    final_price_paise: number;
    unit_price_inr: number;
    upgrade_credit_inr: number;
    final_price_inr: number;
  }>;
  pricing?: {
    subtotal_gross_paise: number;
    total_upgrade_credit_paise: number;
    discount_paise: number;
    payable_paise: number;
    subtotal_gross_inr: number;
    total_upgrade_credit_inr: number;
    discount_inr: number;
    payable_inr: number;
    gst_breakdown: {
      price_inclusive_paise: number;
      base_taxable_paise: number;
      total_gst_paise: number;
      cgst_paise: number;
      sgst_paise: number;
      igst_paise: number;
      gst_rate_percent: number;
    };
  };
  errors?: string[];
}

export const productService = {
  /**
   * Fetch active products list with optional category / hierarchy filtering
   */
  async getProducts(params?: ProductFilterParams): Promise<Product[]> {
    const { data } = await api.get<Product[]>('/products/', { params });
    return data;
  },

  /**
   * Fetch product detail by ID
   */
  async getProduct(id: number | string): Promise<Product> {
    const { data } = await api.get<Product>(`/products/${id}/`);
    return data;
  },

  /**
   * Check dynamic ownership / purchase state for currently authenticated user
   */
  async getProductOwnership(id: number | string): Promise<ProductOwnershipResponse> {
    const { data } = await api.get<ProductOwnershipResponse>(`/products/${id}/ownership/`);
    return data;
  },

  /**
   * Calculate tailored price including Subject Pack upgrade credits and pass renewal previews
   */
  async calculatePrice(id: number | string): Promise<ProductPriceCalculation> {
    const { data } = await api.get<ProductPriceCalculation>(`/products/${id}/calculate-price/`);
    return data;
  },

  /**
   * Server-authoritative cart validation and price recalculation
   */
  async validateCart(items: Array<{ product_id: number } | number>): Promise<CartValidationResponse> {
    const { data } = await api.post<CartValidationResponse>('/cart/validate/', { items });
    return data;
  },
};
