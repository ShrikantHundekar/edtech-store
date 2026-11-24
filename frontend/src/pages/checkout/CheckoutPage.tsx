import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  ShieldCheck,
  CreditCard,
  Smartphone,
  Lock,
  AlertCircle,
  CheckCircle2,
  Receipt,
  ArrowRight,
  BookOpen,
  Sparkles,
  HelpCircle,
  ArrowLeft,
  X,
} from 'lucide-react';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import { paymentService } from '../../services/paymentService';
import type { PaymentVerifyPayload, PaymentVerifyResponse, RazorpayResponse } from '../../types/payment';

export const CheckoutPage: React.FC = () => {
  const { cartData, coupon, clearCart, items, payableInr } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [errorAlert, setErrorAlert] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<PaymentVerifyResponse | null>(null);
  const [redirectCountdown, setRedirectCountdown] = useState<number>(3);

  // Auto-redirect to My Library upon success
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (successData) {
      timer = setInterval(() => {
        setRedirectCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            navigate('/library');
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [successData, navigate]);

  const pricing = cartData?.pricing;
  const gst = coupon?.gst_breakdown || pricing?.gst_breakdown;
  const lineItems = cartData?.items || [];

  // Central payment verification handler
  const handleVerifyPayment = async (payload: PaymentVerifyPayload) => {
    setIsProcessing(true);
    setErrorAlert(null);
    try {
      const result = await paymentService.verifyPayment(payload);
      if (result.success) {
        clearCart();
        setSuccessData(result);
      } else {
        setErrorAlert(result.error || 'Payment verification failed. Please contact support.');
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        (err instanceof Error ? err.message : 'Cryptographic verification error.');
      setErrorAlert(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  // Standard Razorpay Modal Trigger
  const handleStandardCheckout = async () => {
    if (items.length === 0) return;
    setIsProcessing(true);
    setErrorAlert(null);

    try {
      // 1. Create Order on Backend
      const order = await paymentService.createOrder(items, coupon?.code);

      // 2. Handle Zero-balance orders (100% coupon or upgrade credits)
      if (order.net_payable_paise === 0) {
        clearCart();
        setSuccessData({
          success: true,
          order_id: order.id,
          order_number: order.order_number,
          status: 'PAID',
          message: 'Zero-balance order fulfilled with promotional credits.',
          entitlements_count: order.items.length,
        });
        setIsProcessing(false);
        return;
      }

      // 3. Ensure Razorpay SDK is loaded
      const sdkReady = await paymentService.loadRazorpaySDK();
      if (!sdkReady || !window.Razorpay) {
        setErrorAlert('Could not load Razorpay SDK. Please check your internet connection or use Test Simulation below.');
        setIsProcessing(false);
        return;
      }

      // 4. Open Razorpay Checkout Modal
      paymentService.openRazorpayModal({
        key: order.razorpay_key_id,
        amount: order.amount_paise,
        currency: order.currency || 'INR',
        name: 'EdTech Store',
        description: `Order #${order.order_number}`,
        order_id: order.razorpay_order_id || '',
        prefill: {
          name: user?.full_name || '',
          email: user?.email || '',
        },
        theme: {
          color: '#4f46e5',
        },
        modal: {
          ondismiss: () => {
            setIsProcessing(false);
          },
        },
        handler: (response: RazorpayResponse) => {
          handleVerifyPayment({
            razorpay_order_id: response.razorpay_order_id,
            razorpay_payment_id: response.razorpay_payment_id,
            razorpay_signature: response.razorpay_signature,
          });
        },
      });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        (err instanceof Error ? err.message : 'Failed to initiate order.');
      setErrorAlert(msg);
      setIsProcessing(false);
    }
  };

  // Simulated Test Payment (UPI / Card simulation)
  const handleSimulatedPayment = async (method: 'upi' | 'card', fail = false) => {
    if (items.length === 0) return;
    setIsProcessing(true);
    setErrorAlert(null);

    try {
      const order = await paymentService.createOrder(items, coupon?.code);
      if (!order.razorpay_order_id) {
        throw new Error('Order does not have a Razorpay order ID.');
      }

      if (fail) {
        // Trigger simulated failure
        try {
          await paymentService.simulatePayment(order.razorpay_order_id, method, true);
        } catch (simErr: unknown) {
          const msg = simErr instanceof Error ? simErr.message : 'Payment was declined by issuing bank.';
          setErrorAlert(msg);
        }
        setIsProcessing(false);
        return;
      }

      const simPayload = await paymentService.simulatePayment(order.razorpay_order_id, method, false);
      await handleVerifyPayment(simPayload);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
        (err instanceof Error ? err.message : 'Simulation failed.');
      setErrorAlert(msg);
      setIsProcessing(false);
    }
  };

  // If order successfully paid
  if (successData) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center animate-in fade-in-50">
        <div className="w-20 h-20 bg-emerald-100 text-emerald-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-sm">
          <CheckCircle2 className="w-12 h-12" />
        </div>
        <span className="px-3 py-1 bg-emerald-50 text-emerald-800 text-xs font-black uppercase tracking-wider rounded-full">
          Payment Captured & Verified ✓
        </span>
        <h2 className="text-3xl font-black text-slate-900 mt-3">Payment Successful!</h2>
        <p className="mt-2 text-slate-600 text-sm">
          Order <span className="font-mono font-bold text-slate-900">{successData.order_number}</span> has been confirmed.
          Your lifetime curriculum access and study notes have been provisioned to your account.
        </p>

        <div className="mt-8 p-4 bg-slate-50 border border-slate-200/80 rounded-2xl text-xs text-slate-600 space-y-1 text-left">
          <div className="flex justify-between">
            <span>Status:</span>
            <span className="font-bold text-emerald-700 uppercase">PAID</span>
          </div>
          <div className="flex justify-between">
            <span>Provisioned Entitlements:</span>
            <span className="font-bold text-slate-800">{successData.entitlements_count || lineItems.length} Content Item(s)</span>
          </div>
          <div className="flex justify-between">
            <span>Auto-redirecting in:</span>
            <span className="font-bold text-indigo-600">{redirectCountdown}s</span>
          </div>
        </div>

        <div className="mt-6">
          <Link
            to="/library"
            className="w-full py-3.5 px-6 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl shadow-xs transition flex items-center justify-center space-x-2"
          >
            <BookOpen className="w-4 h-4" />
            <span>Go to My Library Now</span>
          </Link>
        </div>
      </div>
    );
  }

  // If cart is empty
  if (lineItems.length === 0) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <div className="inline-flex p-4 bg-slate-100 rounded-2xl text-slate-500 mb-4">
          <CreditCard className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Your Cart is Empty</h2>
        <p className="mt-2 text-slate-600 text-sm">Add notes or subject packs before proceeding to checkout.</p>
        <Link
          to="/products"
          className="mt-6 inline-flex items-center px-5 py-2.5 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Explore Products
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Checkout & Payment
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Secure 256-bit encrypted transaction via Razorpay.
          </p>
        </div>
        <Link
          to="/cart"
          className="text-xs font-bold text-indigo-600 hover:text-indigo-800 transition flex items-center"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Edit Cart
        </Link>
      </div>

      {/* Error Alert Banner */}
      {errorAlert && (
        <div className="mb-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start justify-between">
          <div className="flex items-start space-x-3">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold">Payment Error</p>
              <p className="text-xs mt-0.5">{errorAlert}</p>
            </div>
          </div>
          <button
            onClick={() => setErrorAlert(null)}
            className="text-rose-400 hover:text-rose-600 p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left 2 Columns: Order Review & Payment Options */}
        <div className="lg:col-span-2 space-y-6">
          {/* Order Items Review */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-6 shadow-xs">
            <h2 className="text-base font-bold text-slate-900 mb-4 flex items-center">
              <Receipt className="w-4 h-4 mr-2 text-indigo-600" />
              Order Items ({lineItems.length})
            </h2>
            <div className="divide-y divide-slate-100">
              {lineItems.map((item) => (
                <div key={item.product_id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold text-slate-900">{item.title}</p>
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                      {item.product_type.replace('_', ' ')}
                    </span>
                    {item.upgrade_credit_paise > 0 && (
                      <span className="ml-2 text-[10px] text-amber-700 font-bold bg-amber-50 px-2 py-0.5 rounded-sm">
                        Upgrade credit applied
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-black text-slate-900">
                      ₹{item.final_price_inr.toFixed(2)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Razorpay Standard Payment Action Card */}
          <div className="bg-white rounded-3xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <CreditCard className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">Razorpay Payment Gateway</h3>
                  <p className="text-xs text-slate-400">UPI, Credit/Debit Cards, NetBanking & Wallets</p>
                </div>
              </div>
              <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded-full">
                TEST MODE
              </span>
            </div>

            <div className="mt-6">
              <button
                onClick={handleStandardCheckout}
                disabled={isProcessing}
                className="w-full py-4 px-6 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-black rounded-2xl shadow-sm shadow-indigo-200 transition flex items-center justify-center space-x-2 cursor-pointer text-base"
              >
                <Lock className="w-4 h-4" />
                <span>
                  {isProcessing ? 'Processing Transaction...' : `Pay ₹${payableInr.toFixed(2)} with Razorpay`}
                </span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>

            <p className="text-[11px] text-slate-400 text-center mt-3">
              By clicking Pay, you agree to our terms of digital content access.
            </p>
          </div>

          {/* Test Mode Simulation Panel (Simulates UPI / Card testing in sandbox/dev) */}
          <div className="bg-slate-50 border border-slate-200 rounded-3xl p-6">
            <div className="flex items-center space-x-2 mb-2">
              <Sparkles className="w-4 h-4 text-amber-600" />
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-700">
                Test Mode Simulation (UPI & Card)
              </h3>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Simulate Razorpay checkout responses with cryptographically valid HMAC-SHA256 signatures:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => handleSimulatedPayment('upi', false)}
                disabled={isProcessing}
                className="px-4 py-2.5 bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 rounded-xl text-xs font-bold text-slate-800 transition flex items-center justify-center space-x-2 cursor-pointer shadow-2xs"
              >
                <Smartphone className="w-4 h-4 text-indigo-600" />
                <span>Simulate UPI</span>
              </button>

              <button
                type="button"
                onClick={() => handleSimulatedPayment('card', false)}
                disabled={isProcessing}
                className="px-4 py-2.5 bg-white border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/40 rounded-xl text-xs font-bold text-slate-800 transition flex items-center justify-center space-x-2 cursor-pointer shadow-2xs"
              >
                <CreditCard className="w-4 h-4 text-emerald-600" />
                <span>Simulate Card</span>
              </button>

              <button
                type="button"
                onClick={() => handleSimulatedPayment('card', true)}
                disabled={isProcessing}
                className="px-4 py-2.5 bg-white border border-rose-200 hover:bg-rose-50 rounded-xl text-xs font-bold text-rose-700 transition flex items-center justify-center space-x-1.5 cursor-pointer shadow-2xs"
              >
                <AlertCircle className="w-4 h-4 text-rose-600" />
                <span>Simulate Decline</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Order Summary & Itemized GST Breakdown */}
        <div className="space-y-6">
          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 shadow-md sticky top-24">
            <h2 className="text-base font-extrabold text-slate-900 pb-4 border-b border-slate-100">
              Payment Summary
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
                  <span>Upgrade Credit:</span>
                  <span className="font-bold">
                    -₹{(pricing?.total_upgrade_credit_inr ?? 0).toFixed(2)}
                  </span>
                </div>
              )}

              {coupon && (
                <div className="flex justify-between text-emerald-700">
                  <span>Coupon ({coupon.code}):</span>
                  <span className="font-bold">-₹{coupon.discount_inr.toFixed(2)}</span>
                </div>
              )}

              {/* Itemized 18% GST Breakdown */}
              {gst && (
                <div className="pt-3 border-t border-slate-100 space-y-1.5 text-xs text-slate-500">
                  <div className="flex justify-between">
                    <span>Taxable Base Value:</span>
                    <span className="font-medium">
                      ₹{((gst.base_taxable_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>CGST (9.0%):</span>
                    <span className="font-medium">
                      ₹{((gst.cgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>SGST (9.0%):</span>
                    <span className="font-medium">
                      ₹{((gst.sgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between font-bold text-slate-700">
                    <span>Total GST (18%):</span>
                    <span>₹{((gst.total_gst_paise || 0) / 100).toFixed(2)}</span>
                  </div>
                </div>
              )}

              {/* Net Payable */}
              <div className="pt-4 border-t border-slate-200 flex items-baseline justify-between">
                <div>
                  <span className="text-base font-extrabold text-slate-900 block">Total Due:</span>
                  <span className="text-[10px] text-slate-400 font-bold uppercase">Inclusive of 18% GST</span>
                </div>
                <span className="text-3xl font-black text-indigo-700">
                  ₹{payableInr.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="mt-6 pt-5 border-t border-slate-100 space-y-2 text-xs text-slate-400">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>Instant access granted to My Library</span>
              </div>
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-4 h-4 text-indigo-500 shrink-0" />
                <span>GST Tax Invoice generated automatically</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
