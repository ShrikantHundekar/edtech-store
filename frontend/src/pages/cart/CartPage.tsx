import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Trash2,
  Tag,
  ArrowRight,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  AlertTriangle,
  Receipt,
  BookOpen,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';

export const CartPage: React.FC = () => {
  const {
    cartData,
    loading,
    error,
    removeFromCart,
    coupon,
    couponLoading,
    couponError,
    applyCoupon,
    removeCoupon,
    payableInr,
  } = useCart();

  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [couponInput, setCouponInput] = useState<string>('');

  const handleApplyCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!couponInput.trim()) return;
    const success = await applyCoupon(couponInput);
    if (success) {
      setCouponInput('');
    }
  };

  const handleProceedToCheckout = () => {
    if (!isAuthenticated) {
      navigate('/login?redirect=/checkout');
    } else {
      navigate('/checkout');
    }
  };

  const items = cartData?.items || [];
  const pricing = cartData?.pricing;

  // Active GST breakdown (from coupon or cart)
  const gst = coupon?.gst_breakdown || pricing?.gst_breakdown;

  if (items.length === 0 && !loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-20 text-center">
        <div className="w-20 h-20 bg-indigo-50 text-indigo-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-sm">
          <ShoppingBag className="w-10 h-10" />
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900">Your Cart is Empty</h2>
        <p className="mt-2 text-slate-600 max-w-md mx-auto text-sm sm:text-base">
          Looks like you haven&apos;t added any curriculum notes, subject packs, or class passes yet.
        </p>
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            to="/products"
            className="w-full sm:w-auto px-6 py-3 bg-indigo-600 text-white font-bold rounded-xl shadow-xs hover:bg-indigo-700 transition flex items-center justify-center space-x-2"
          >
            <BookOpen className="w-4 h-4" />
            <span>Browse Products</span>
          </Link>
          <Link
            to="/"
            className="w-full sm:w-auto px-6 py-3 bg-slate-100 text-slate-800 font-semibold rounded-xl hover:bg-slate-200 transition"
          >
            Curriculum Explorer
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="pb-6 border-b border-slate-200">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Shopping Cart ({items.length})
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Review your items, apply promotional discounts, and review itemized GST.
        </p>
      </div>

      {/* Cart-level Errors (e.g. Overlapping items or Inactive products) */}
      {error && (
        <div className="mt-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-bold">Cart Eligibility Issue</p>
            <p className="mt-0.5">{error}</p>
          </div>
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Items List & Coupon Code Input */}
        <div className="lg:col-span-2 space-y-6">
          {/* Items List */}
          <div className="bg-white rounded-3xl border border-slate-200/80 divide-y divide-slate-100 shadow-xs overflow-hidden">
            {items.map((item) => (
              <div key={item.product_id} className="p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-[10px] font-black rounded-md uppercase tracking-wider">
                      {item.product_type.replace('_', ' ')}
                    </span>
                    {item.upgrade_credit_paise > 0 && (
                      <span className="px-2 py-0.5 bg-amber-50 text-amber-800 text-[10px] font-bold rounded-md flex items-center">
                        <Sparkles className="w-3 h-3 mr-1 text-amber-600" />
                        Upgrade Credit Applied
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-slate-900">
                    {item.title}
                  </h3>

                  {item.upgrade_credit_paise > 0 && (
                    <p className="text-xs text-amber-800 font-medium">
                      Credited ₹{item.upgrade_credit_inr.toFixed(2)} from {item.owned_chapters_count || 1} previously purchased chapter(s).
                    </p>
                  )}

                  {item.renewal_preview && (
                    <p className="text-xs text-indigo-600 font-medium">
                      Pass stacks seamlessly: Active through {new Date(item.renewal_preview.valid_until).toLocaleDateString()}.
                    </p>
                  )}
                </div>

                <div className="flex items-center justify-between sm:justify-end sm:space-x-6 pt-3 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                  <div className="text-right">
                    <div className="flex items-baseline space-x-1.5 justify-end">
                      <span className="text-lg font-black text-slate-900">
                        ₹{item.final_price_inr.toFixed(2)}
                      </span>
                      {item.upgrade_credit_paise > 0 && (
                        <span className="text-xs text-slate-400 line-through">
                          ₹{item.base_price_inr.toFixed(2)}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 font-medium uppercase">
                      Incl. 18% GST
                    </span>
                  </div>

                  <button
                    onClick={() => removeFromCart(item.product_id)}
                    className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition cursor-pointer"
                    title="Remove item"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Promotional Coupon Input Box */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs">
            <h3 className="text-sm font-bold text-slate-900 flex items-center mb-3">
              <Tag className="w-4 h-4 mr-2 text-indigo-600" /> Have a Coupon or Promo Code?
            </h3>

            {coupon ? (
              <div className="flex items-center justify-between p-3.5 bg-emerald-50 border border-emerald-200 rounded-2xl">
                <div className="flex items-center space-x-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  <div>
                    <span className="font-mono font-black text-emerald-900 text-sm tracking-wider">
                      {coupon.code}
                    </span>
                    <span className="ml-2 text-xs font-semibold text-emerald-700">
                      (Saved ₹{coupon.discount_inr.toFixed(2)})
                    </span>
                  </div>
                </div>
                <button
                  onClick={removeCoupon}
                  className="text-xs font-bold text-rose-600 hover:text-rose-800 transition cursor-pointer flex items-center"
                >
                  <XCircle className="w-4 h-4 mr-1" /> Remove
                </button>
              </div>
            ) : (
              <form onSubmit={handleApplyCoupon} className="space-y-2">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Enter coupon code (e.g. CBSE10)"
                    value={couponInput}
                    onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                    className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-mono uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 focus:bg-white"
                  />
                  <button
                    type="submit"
                    disabled={couponLoading || !couponInput.trim()}
                    className="px-5 py-2.5 bg-slate-900 hover:bg-indigo-600 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition cursor-pointer"
                  >
                    {couponLoading ? 'Checking...' : 'Apply'}
                  </button>
                </div>
                {couponError && (
                  <p className="text-xs text-rose-600 font-medium">{couponError}</p>
                )}
              </form>
            )}
          </div>
        </div>

        {/* Right Column: Order Summary & 18% GST Breakdown Card */}
        <div className="space-y-6">
          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-md sticky top-24">
            <h2 className="text-base font-extrabold text-slate-900 pb-4 border-b border-slate-100">
              Order Summary
            </h2>

            <div className="mt-4 space-y-3 text-sm text-slate-600">
              <div className="flex justify-between">
                <span>Gross Subtotal:</span>
                <span className="font-semibold text-slate-900">
                  ₹{(pricing?.total_base_price_inr ?? 0).toFixed(2)}
                </span>
              </div>

              {(pricing?.total_upgrade_credit_paise ?? 0) > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Subject Pack Upgrade Credit:</span>
                  <span className="font-bold">
                    -₹{(pricing?.total_upgrade_credit_inr ?? 0).toFixed(2)}
                  </span>
                </div>
              )}

              {coupon && coupon.discount_paise > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Coupon Discount ({coupon.code}):</span>
                  <span className="font-bold">-₹{coupon.discount_inr.toFixed(2)}</span>
                </div>
              )}

              {/* Itemized 18% GST Breakdown */}
              {gst && (
                <div className="pt-3 border-t border-slate-100 space-y-2 text-xs text-slate-500">
                  <div className="flex items-center text-slate-700 font-bold">
                    <Receipt className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                    <span>Itemized Tax Summary (18% GST Inclusive)</span>
                  </div>
                  <div className="flex justify-between pl-5">
                    <span>Taxable Base Value:</span>
                    <span className="font-medium">
                      ₹{((gst.base_taxable_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between pl-5">
                    <span>CGST (9.0%):</span>
                    <span className="font-medium">
                      ₹{((gst.cgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between pl-5">
                    <span>SGST (9.0%):</span>
                    <span className="font-medium">
                      ₹{((gst.sgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between pl-5 font-bold text-slate-700">
                    <span>Total GST Split:</span>
                    <span>₹{((gst.total_gst_paise || 0) / 100).toFixed(2)}</span>
                  </div>
                </div>
              )}

              {/* Total Payable */}
              <div className="pt-4 border-t border-slate-200 flex items-baseline justify-between">
                <div>
                  <span className="text-base font-extrabold text-slate-900 block">Total Payable:</span>
                  <span className="text-[10px] text-slate-400 font-bold uppercase">
                    (Final Amount with Taxes)
                  </span>
                </div>
                <span className="text-3xl font-black text-indigo-700">
                  ₹{payableInr.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Checkout Action Button */}
            <div className="mt-6">
              <button
                onClick={handleProceedToCheckout}
                disabled={Boolean(error) || loading || items.length === 0}
                className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-bold rounded-2xl shadow-sm shadow-indigo-200 hover:shadow-indigo-300 transition-all flex items-center justify-center space-x-2 cursor-pointer"
              >
                <span>Proceed to Checkout</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Trust badge */}
            <div className="mt-4 flex items-center justify-center space-x-2 text-xs text-slate-400 font-medium">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Instant Digital Access & GST Invoice</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
