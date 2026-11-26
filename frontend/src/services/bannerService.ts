import { api } from './api';
import type { PromoBanner, PromoBannerInput } from '../types/banner';

export const bannerService = {
  /**
   * Fetch active promo banners for catalog display
   */
  async getActiveBanners(classId?: number): Promise<PromoBanner[]> {
    const params = classId ? { class_id: classId } : undefined;
    const { data } = await api.get<PromoBanner[]>('/catalog/banners/', { params });
    return data;
  },

  /**
   * Fetch all banners for admin management
   */
  async getAdminBanners(): Promise<PromoBanner[]> {
    const { data } = await api.get<PromoBanner[]>('/admin/banners/');
    return data;
  },

  /**
   * Create a new promotional banner
   */
  async createBanner(input: PromoBannerInput): Promise<PromoBanner> {
    const { data } = await api.post<PromoBanner>('/admin/banners/', input);
    return data;
  },

  /**
   * Update an existing promotional banner
   */
  async updateBanner(id: number, input: Partial<PromoBannerInput>): Promise<PromoBanner> {
    const { data } = await api.patch<PromoBanner>(`/admin/banners/${id}/`, input);
    return data;
  },

  /**
   * Delete a banner
   */
  async deleteBanner(id: number): Promise<void> {
    await api.delete(`/admin/banners/${id}/`);
  },
};
