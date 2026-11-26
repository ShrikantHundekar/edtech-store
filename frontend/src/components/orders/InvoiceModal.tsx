import React from 'react';
import {
  X,
  Printer,
  ExternalLink,
  Receipt,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import type { Order } from '../../types/order';
import { orderService } from '../../services/orderService';

interface InvoiceModalProps {
  order: Order;
  onClose: () => void;
}

export const InvoiceModal: React.FC<InvoiceModalProps> = ({ order, onClose }) => {
  const handlePrint = () => {
    window.print();
  };

  const invoiceUrl = orderService.getOrderInvoiceUrl(order.id);

  const gst = order.gst_breakdown;
  const taxableInr = gst?.base_taxable_inr ?? order.taxable_base_inr;
  const cgstInr = gst?.cgst_inr ?? order.gst_amount_inr / 2.0;
  const sgstInr = gst?.sgst_inr ?? order.gst_amount_inr / 2.0;
  const totalGstInr = gst?.total_gst_inr ?? order.gst_amount_inr;

  const paymentId = order.razorpay_payment_id || order.razorpay_order_id || 'N/A';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-xs p-3 sm:p-6 overflow-y-auto animate-in fade-in-50">
      <div className="bg-white rounded-3xl shadow-2xl max-w-3xl w-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-200">
        {/* Modal Action Bar (Hidden when printing) */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between no-print">
          <div className="flex items-center space-x-2">
            <Receipt className="w-5 h-5 text-indigo-400" />
            <span className="font-bold text-sm">Tax Invoice Preview</span>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handlePrint}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5 cursor-pointer shadow-xs"
            >
              <Printer className="w-4 h-4" />
              <span>Print Invoice</span>
            </button>

            <a
              href={invoiceUrl}
              target="_blank"
              rel="noreferrer"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition flex items-center space-x-1"
              title="Open full HTML invoice in new tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>HTML View</span>
            </a>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Invoice Card Content */}
        <div className="p-6 sm:p-10 overflow-y-auto printable-content">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between pb-6 border-b-2 border-indigo-600 gap-4">
            <div>
              <div className="text-2xl font-black text-indigo-600 tracking-tight">
                🎓 EdTech Store
              </div>
              <p className="text-xs text-slate-500 mt-1">
                CBSE Digital Notes & Educational Pass Platform
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                GSTIN: 27AABCE1234F1Z5 | PAN: AABCE1234F
              </p>
            </div>

            <div className="text-left sm:text-right">
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                  order.status === 'PAID'
                    ? 'bg-emerald-100 text-emerald-800'
                    : order.status === 'FAILED'
                    ? 'bg-rose-100 text-rose-800'
                    : 'bg-amber-100 text-amber-800'
                }`}
              >
                {order.status === 'PAID' ? (
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                ) : order.status === 'FAILED' ? (
                  <AlertCircle className="w-3.5 h-3.5 mr-1" />
                ) : (
                  <Clock className="w-3.5 h-3.5 mr-1" />
                )}
                {order.status}
              </span>
              <h2 className="text-xl font-black text-slate-900 mt-2">TAX INVOICE</h2>
              <p className="text-xs font-bold text-indigo-600">#{order.order_number}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Date: {new Date(order.created_at).toLocaleDateString('en-IN', {
                  day: 'numeric',
                  month: 'long',
                  year: 'numeric',
                })}
              </p>
            </div>
          </div>

          {/* Billed To & Payment Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 my-6 text-xs text-slate-600">
            <div>
              <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                Billed To (Student)
              </span>
              <p className="font-bold text-sm text-slate-900 mt-1">
                {order.customer_name || 'Student Account'}
              </p>
              <p className="text-slate-600">{order.customer_email || 'student@edtechstore.local'}</p>
              <p className="text-[11px] text-slate-400 mt-1">Place of Supply: Maharashtra (27)</p>
            </div>

            <div className="sm:text-right">
              <span className="font-bold text-slate-400 uppercase tracking-wider block text-[10px]">
                Payment Transaction Details
              </span>
              <p className="mt-1">
                Gateway: <strong className="text-slate-800">Razorpay Test Mode</strong>
              </p>
              <p className="mt-0.5">
                Payment ID:{' '}
                <code className="bg-slate-100 px-1.5 py-0.5 rounded-md font-mono text-slate-800 font-semibold">
                  {paymentId}
                </code>
              </p>
              <p className="mt-0.5">
                Method: <strong className="text-slate-800">{(order.payment_method || 'Razorpay').toUpperCase()}</strong>
              </p>
            </div>
          </div>

          {/* Line Items Table */}
          <div className="border border-slate-200 rounded-2xl overflow-hidden mb-6">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                <tr>
                  <th className="py-3 px-4 w-10 text-center">#</th>
                  <th className="py-3 px-4">Description of Supply</th>
                  <th className="py-3 px-4 text-right">Unit Price</th>
                  <th className="py-3 px-4 text-right">Upgrade Credit</th>
                  <th className="py-3 px-4 text-right">Net Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {order.items.map((item, idx) => (
                  <tr key={item.id}>
                    <td className="py-3 px-4 text-center text-slate-400">{idx + 1}</td>
                    <td className="py-3 px-4">
                      <p className="font-bold text-slate-900">{item.product_title}</p>
                      <span className="text-[10px] text-slate-400 font-medium">
                        SAC Code: 998431 (Online Digital Content)
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-slate-700">
                      ₹{item.unit_price_inr.toFixed(2)}
                    </td>
                    <td className="py-3 px-4 text-right font-medium text-emerald-600">
                      {item.upgrade_credit_inr > 0 ? `-₹${item.upgrade_credit_inr.toFixed(2)}` : '₹0.00'}
                    </td>
                    <td className="py-3 px-4 text-right font-black text-slate-900">
                      ₹{item.net_price_inr.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pricing & GST Tax Breakdown */}
          <div className="flex justify-end">
            <div className="w-full sm:w-80 space-y-2 text-xs text-slate-600">
              <div className="flex justify-between">
                <span>Gross Subtotal:</span>
                <span className="font-semibold text-slate-900">
                  ₹{order.gross_amount_inr.toFixed(2)}
                </span>
              </div>

              {order.upgrade_discount_inr > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Subject Pack Upgrade Credit:</span>
                  <span className="font-bold">-₹{order.upgrade_discount_inr.toFixed(2)}</span>
                </div>
              )}

              {order.coupon_discount_inr > 0 && (
                <div className="flex justify-between text-emerald-700">
                  <span>Coupon Discount ({order.coupon_code}):</span>
                  <span className="font-bold">-₹{order.coupon_discount_inr.toFixed(2)}</span>
                </div>
              )}

              <div className="pt-2 border-t border-slate-200 flex justify-between">
                <span>Taxable Base Value:</span>
                <span className="font-semibold text-slate-800">
                  ₹{taxableInr.toFixed(2)}
                </span>
              </div>

              <div className="flex justify-between text-slate-500 pl-3">
                <span>CGST (9.0%):</span>
                <span>₹{cgstInr.toFixed(2)}</span>
              </div>

              <div className="flex justify-between text-slate-500 pl-3">
                <span>SGST (9.0%):</span>
                <span>₹{sgstInr.toFixed(2)}</span>
              </div>

              <div className="flex justify-between font-bold text-slate-700 pl-3">
                <span>Total 18% GST:</span>
                <span>₹{totalGstInr.toFixed(2)}</span>
              </div>

              <div className="pt-2.5 border-t-2 border-slate-900 flex justify-between items-baseline">
                <span className="text-sm font-black text-slate-900">Total Amount Paid:</span>
                <span className="text-lg font-black text-indigo-600">
                  ₹{order.net_payable_inr.toFixed(2)}
                </span>
              </div>
            </div>
          </div>

          {/* Terms Footer */}
          <div className="mt-8 pt-4 border-t border-dashed border-slate-200 text-[11px] text-slate-400 leading-relaxed">
            <p>
              <strong>Notes:</strong> This is a computer-generated tax invoice for digital educational content supply.
              18% GST (CGST 9% + SGST 9%) is inclusive in the net amount. For support, quote Order #{order.order_number}.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
