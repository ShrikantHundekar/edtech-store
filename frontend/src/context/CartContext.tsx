import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { useAuth } from './AuthContext';
import type { ServerCartResponse, AppliedCoupon } from '../types/cart';

interface CartContextType {
  items: number[];
  cartData: ServerCartResponse | null;
  coupon: AppliedCoupon | null;
  loading: boolean;
  couponLoading: boolean;
  error: string | null;
  couponError: string | null;
  addToCart: (productId: number) => void;
  removeFromCart: (productId: number) => void;
  clearCart: () => void;
  applyCoupon: (code: string) => Promise<boolean>;
  removeCoupon: () => void;
  refreshCart: () => Promise<void>;
  itemCount: number;
  payablePaise: number;
  payableInr: number;
}

const CartContext = createContext<CartContextType | undefined>(undefined);

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<number[]>(() => {
    try {
      const stored = localStorage.getItem('cart_items');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [cartData, setCartData] = useState<ServerCartResponse | null>(null);
  const [coupon, setCoupon] = useState<AppliedCoupon | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [couponLoading, setCouponLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [couponError, setCouponError] = useState<string | null>(null);

  // Sync to localStorage
  useEffect(() => {
    localStorage.setItem('cart_items', JSON.stringify(items));
  }, [items]);

  // Server-authoritative Cart Recalculation
  const refreshCart = useCallback(async () => {
    if (items.length === 0) {
      setCartData(null);
      setCoupon(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post<ServerCartResponse>('/cart/validate/', {
        items,
      });
      setCartData(data);

      // If coupon was active, re-validate against newly recalculated subtotal
      if (coupon) {
        try {
          const couponResp = await api.post('/coupons/apply/', {
            code: coupon.code,
            items,
          });
          if (couponResp.data.valid) {
            setCoupon({
              code: coupon.code,
              discount_type: couponResp.data.coupon?.discount_type || 'FLAT',
              discount_value: couponResp.data.coupon?.discount_value || 0,
              discount_paise: couponResp.data.discount_paise,
              discount_inr: couponResp.data.discount_inr,
              subtotal_paise: couponResp.data.subtotal_paise,
              subtotal_inr: couponResp.data.subtotal_inr,
              net_payable_paise: couponResp.data.net_payable_paise,
              net_payable_inr: couponResp.data.net_payable_inr,
              gst_breakdown: couponResp.data.gst_breakdown,
            });
          } else {
            setCoupon(null);
            setCouponError(couponResp.data.error || 'Coupon no longer applicable.');
          }
        } catch {
          setCoupon(null);
        }
      }
    } catch (err: unknown) {
      const respData = (err as { response?: { data?: { errors?: string[]; error?: string; message?: string } } }).response?.data;
      const errMsg =
        respData?.errors?.join(', ') ||
        respData?.error ||
        respData?.message ||
        'Failed to recalculate cart.';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  }, [items, coupon]);

  // Recalculate whenever items change or authentication status updates
  useEffect(() => {
    refreshCart();
  }, [items.length, isAuthenticated]);

  const addToCart = (productId: number) => {
    if (!items.includes(productId)) {
      setItems((prev) => [...prev, productId]);
    }
  };

  const removeFromCart = (productId: number) => {
    setItems((prev) => prev.filter((id) => id !== productId));
  };

  const clearCart = () => {
    setItems([]);
    setCartData(null);
    setCoupon(null);
    setError(null);
    setCouponError(null);
    localStorage.removeItem('cart_items');
  };

  const applyCoupon = async (code: string): Promise<boolean> => {
    if (!code.trim()) {
      setCouponError('Please enter a coupon code.');
      return false;
    }

    setCouponLoading(true);
    setCouponError(null);
    try {
      const { data } = await api.post('/coupons/apply/', {
        code: code.trim(),
        items,
      });

      if (data.valid) {
        setCoupon({
          code: code.trim().toUpperCase(),
          discount_type: data.coupon?.discount_type || 'FLAT',
          discount_value: data.coupon?.discount_value || 0,
          discount_paise: data.discount_paise,
          discount_inr: data.discount_inr,
          subtotal_paise: data.subtotal_paise,
          subtotal_inr: data.subtotal_inr,
          net_payable_paise: data.net_payable_paise,
          net_payable_inr: data.net_payable_inr,
          gst_breakdown: data.gst_breakdown,
        });
        return true;
      } else {
        setCouponError(data.error || 'Invalid coupon code.');
        return false;
      }
    } catch (err: unknown) {
      const respData = (err as { response?: { data?: { error?: string } } }).response?.data;
      setCouponError(respData?.error || 'Failed to apply coupon.');
      return false;
    } finally {
      setCouponLoading(false);
    }
  };

  const removeCoupon = () => {
    setCoupon(null);
    setCouponError(null);
  };

  // Compute final payable figures
  const payablePaise = coupon
    ? coupon.net_payable_paise
    : cartData?.pricing.subtotal_paise ?? 0;

  const payableInr = coupon
    ? coupon.net_payable_inr
    : cartData?.pricing.subtotal_inr ?? 0;

  return (
    <CartContext.Provider
      value={{
        items,
        cartData,
        coupon,
        loading,
        couponLoading,
        error,
        couponError,
        addToCart,
        removeFromCart,
        clearCart,
        applyCoupon,
        removeCoupon,
        refreshCart,
        itemCount: items.length,
        payablePaise,
        payableInr,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = (): CartContextType => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};
