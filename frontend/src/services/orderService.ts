import { api } from './api';
import type { Order } from '../types/order';

export const orderService = {
  /**
   * Fetch authenticated student's historical orders
   */
  async getOrders(): Promise<Order[]> {
    const { data } = await api.get<Order[]>('/orders/');
    return data;
  },

  /**
   * Fetch single order detail by ID
   */
  async getOrder(id: number | string): Promise<Order> {
    const { data } = await api.get<Order>(`/orders/${id}/`);
    return data;
  },

  /**
   * Get direct HTML invoice URL for download or new tab view
   */
  getOrderInvoiceUrl(id: number | string): string {
    return `/api/v1/orders/${id}/invoice/`;
  },
};
