import { api } from './api';
import type { Product, ProductType } from '../types/product';

export interface AdminProductInput {
  title: string;
  slug?: string;
  product_type: ProductType;
  description?: string;
  board?: number | null;
  academic_class?: number | null;
  subject?: number | null;
  chapter?: number | null;
  is_active?: boolean;
  amount_paise?: number; // Integer paise
}

export interface BundleItemInput {
  target_type: 'CHAPTER' | 'SUBJECT';
  chapter?: number;
  subject?: number;
}

export interface AdminBundleItem {
  id: number;
  target_type: 'CHAPTER' | 'SUBJECT';
  chapter?: number;
  subject?: number;
  title: string;
}

export interface AdminPriceHistory {
  id: number;
  amount_paise: number;
  currency: string;
  valid_from: string;
  valid_until?: string | null;
  is_current: boolean;
  amount_inr: number;
  created_at: string;
}

export const adminProductService = {
  /**
   * List all products with full administrative details
   */
  async getProducts(): Promise<Product[]> {
    const { data } = await api.get<Product[]>('/admin/products/');
    return data;
  },

  /**
   * Get single product details
   */
  async getProduct(id: number): Promise<Product> {
    const { data } = await api.get<Product>(`/admin/products/${id}/`);
    return data;
  },

  /**
   * Create a new product with scopes and price in paise
   */
  async createProduct(input: AdminProductInput): Promise<Product> {
    const { data } = await api.post<Product>('/admin/products/', input);
    return data;
  },

  /**
   * Update an existing product
   */
  async updateProduct(id: number, input: Partial<AdminProductInput>): Promise<Product> {
    const { data } = await api.patch<Product>(`/admin/products/${id}/`, input);
    return data;
  },

  /**
   * Delete a product
   */
  async deleteProduct(id: number): Promise<void> {
    await api.delete(`/admin/products/${id}/`);
  },

  /**
   * Set or update price point (in integer paise)
   */
  async setPrice(productId: number, amountPaise: number): Promise<AdminPriceHistory> {
    const { data } = await api.post<AdminPriceHistory>(`/admin/products/${productId}/prices/`, {
      amount_paise: amountPaise,
      is_current: true,
    });
    return data;
  },

  /**
   * Fetch price history for a product
   */
  async getPriceHistory(productId: number): Promise<AdminPriceHistory[]> {
    const { data } = await api.get<AdminPriceHistory[]>(`/admin/products/${productId}/prices/`);
    return data;
  },

  /**
   * Get items in a bundle product
   */
  async getBundleItems(productId: number): Promise<AdminBundleItem[]> {
    const { data } = await api.get<AdminBundleItem[]>(`/admin/products/${productId}/bundle-items/`);
    return data;
  },

  /**
   * Add item to a bundle product
   */
  async addBundleItem(productId: number, item: BundleItemInput): Promise<AdminBundleItem> {
    const { data } = await api.post<AdminBundleItem>(`/admin/products/${productId}/bundle-items/`, item);
    return data;
  },

  /**
   * Remove item from bundle
   */
  async removeBundleItem(productId: number, itemId: number): Promise<void> {
    await api.delete(`/admin/products/${productId}/bundle-items/${itemId}/`);
  },
};
