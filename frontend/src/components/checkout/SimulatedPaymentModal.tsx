import React, { useState } from 'react';
import { ShieldCheck, CreditCard, Smartphone, AlertCircle, X, Loader2 } from 'lucide-react';

interface SimulatedPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderNumber: string;
  amountInr: number;
  onSelectMethod: (method: 'upi' | 'card', fail?: boolean) => Promise<void>;
}

export const SimulatedPaymentModal: React.FC<SimulatedPaymentModalProps> = ({
  isOpen,
  onClose,
  orderNumber,
  amountInr,
  onSelectMethod,
}) => {
  const [loadingMethod, setLoadingMethod] = useState<'upi' | 'card' | 'fail' | null>(null);

  if (!isOpen) return null;

  const handleAction = async (method: 'upi' | 'card', fail = false) => {
    setLoadingMethod(fail ? 'fail' : method);
    try {
      await onSelectMethod(method, fail);
      onClose();
    } catch {
      // Handled in parent
    } finally {
      setLoadingMethod(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden transform transition-all">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-indigo-900 to-indigo-800 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
              <ShieldCheck className="w-6 h-6 text-indigo-300" />
            </div>
            <div>
              <h3 className="font-bold text-base">Razorpay Test Checkout</h3>
              <p className="text-xs text-indigo-200">Sandbox Payment Simulator</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-indigo-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Amount & Order details */}
        <div className="p-6 bg-slate-50 border-b border-slate-200/80 flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Order #{orderNumber}
            </span>
            <span className="text-xs text-slate-400">Total Payable Amount</span>
          </div>
          <div className="text-right">
            <span className="text-2xl font-black text-indigo-700">₹{amountInr.toFixed(2)}</span>
            <span className="text-[10px] text-emerald-700 font-bold block bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 mt-0.5">
              18% GST Included
            </span>
          </div>
        </div>

        {/* Payment Options */}
        <div className="p-6 space-y-3">
          <p className="text-xs text-slate-500 mb-2">
            Select a payment method to generate authentic cryptographic HMAC-SHA256 signatures:
          </p>

          <button
            type="button"
            disabled={loadingMethod !== null}
            onClick={() => handleAction('upi', false)}
            className="w-full p-4 rounded-2xl border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-left transition flex items-center justify-between group disabled:opacity-50"
          >
            <div className="flex items-center space-x-3.5">
              <div className="w-10 h-10 rounded-xl bg-indigo-100/70 text-indigo-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <p className="font-bold text-sm text-slate-900">Instant UPI Payment</p>
                <p className="text-xs text-slate-500">Google Pay, PhonePe, Paytm, BHIM</p>
              </div>
            </div>
            {loadingMethod === 'upi' ? (
              <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
            ) : (
              <span className="text-xs font-bold text-indigo-600 group-hover:translate-x-0.5 transition-transform">
                Pay &rarr;
              </span>
            )}
          </button>

          <button
            type="button"
            disabled={loadingMethod !== null}
            onClick={() => handleAction('card', false)}
            className="w-full p-4 rounded-2xl border border-slate-200 hover:border-emerald-400 hover:bg-emerald-50/50 text-left transition flex items-center justify-between group disabled:opacity-50"
          >
            <div className="flex items-center space-x-3.5">
              <div className="w-10 h-10 rounded-xl bg-emerald-100/70 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <CreditCard className="w-5 h-5" />
              </div>
              <div>
                <p className="font-bold text-sm text-slate-900">Debit / Credit Card</p>
                <p className="text-xs text-slate-500">Visa, Mastercard, RuPay</p>
              </div>
            </div>
            {loadingMethod === 'card' ? (
              <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
            ) : (
              <span className="text-xs font-bold text-emerald-600 group-hover:translate-x-0.5 transition-transform">
                Pay &rarr;
              </span>
            )}
          </button>

          <button
            type="button"
            disabled={loadingMethod !== null}
            onClick={() => handleAction('card', true)}
            className="w-full p-3 rounded-xl border border-rose-100 hover:bg-rose-50 text-left transition flex items-center justify-between group text-rose-700 disabled:opacity-50"
          >
            <div className="flex items-center space-x-2.5 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-500" />
              <span className="font-semibold">Simulate Payment Failure / Decline</span>
            </div>
            {loadingMethod === 'fail' ? (
              <Loader2 className="w-4 h-4 animate-spin text-rose-600" />
            ) : (
              <span className="text-[11px] font-bold text-rose-500">Test Error</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
