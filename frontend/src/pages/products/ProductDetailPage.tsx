import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
  Receipt,
  Layers,
  ArrowLeft,
  Calendar,
  AlertCircle,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { productService } from '../../services/productService';
import { useAuth } from '../../context/AuthContext';
import type {
  Product,
  ProductOwnershipResponse,
  ProductPriceCalculation,
  PurchaseState,
} from '../../types/product';

export const ProductDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const [product, setProduct] = useState<Product | null>(null);
  const [ownership, setOwnership] = useState<ProductOwnershipResponse | null>(null);
  const [priceCalc, setPriceCalc] = useState<ProductPriceCalculation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [showGstDetails, setShowGstDetails] = useState<boolean>(false);

  useEffect(() => {
    if (!id) return;

    const fetchProductData = async () => {
      setLoading(true);
      setError(null);
      try {
        const prodData = await productService.getProduct(id);
        setProduct(prodData);

        // Fetch ownership and calculated pricing in parallel
        try {
          const [ownerData, calcData] = await Promise.all([
            productService.getProductOwnership(id),
            productService.calculatePrice(id),
          ]);
          setOwnership(ownerData);
          setPriceCalc(calcData);
        } catch {
          // Non-blocking if guest or calculate-price endpoint returns standard values
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load product details';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchProductData();
  }, [id, isAuthenticated]);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-500 font-medium">Loading product details...</p>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="inline-flex p-4 bg-rose-50 rounded-2xl text-rose-600 mb-4">
          <AlertCircle className="w-10 h-10" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Product Not Found</h2>
        <p className="mt-2 text-slate-600">{error || 'The requested product could not be found.'}</p>
        <Link
          to="/products"
          className="mt-6 inline-flex items-center px-5 py-2.5 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Store
        </Link>
      </div>
    );
  }

  // Determine active purchase state
  const purchaseState: PurchaseState =
    ownership?.purchase_state || (product as unknown as { purchase_state?: PurchaseState }).purchase_state || 'BUY';

  // Effective price display
  const effectivePriceInr = priceCalc
    ? priceCalc.payable_price_inr
    : (product as unknown as { price_inr?: number }).price_inr ?? product.current_price_inr;

  const basePriceInr = priceCalc
    ? priceCalc.base_price_inr
    : (product as unknown as { price_inr?: number }).price_inr ?? product.current_price_inr;

  const upgradeCreditInr = priceCalc ? priceCalc.upgrade_credit_inr : 0;
  const gst = priceCalc?.gst_breakdown || product.gst_breakdown;

  const handleAddToCart = () => {
    // Add to cart local storage / cart context
    const existing = JSON.parse(localStorage.getItem('cart_items') || '[]');
    if (!existing.includes(product.id)) {
      existing.push(product.id);
      localStorage.setItem('cart_items', JSON.stringify(existing));
    }
    navigate('/cart');
  };

  const handleBuyNow = () => {
    handleAddToCart();
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Back button & Breadcrumbs */}
      <div className="mb-6 flex items-center justify-between">
        <Link
          to="/products"
          className="inline-flex items-center text-sm font-medium text-slate-500 hover:text-indigo-600 transition"
        >
          <ArrowLeft className="w-4 h-4 mr-1.5" /> All Products
        </Link>

        <div className="flex items-center space-x-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          {product.board_name && <span>{product.board_name}</span>}
          {product.class_name && <span>• {product.class_name}</span>}
          {product.subject_name && <span>• {product.subject_name}</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Product Info & Inclusions */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs">
            {/* Header Badges */}
            <div className="flex flex-wrap items-center gap-2 mb-4">
              <span className="px-3 py-1 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full uppercase tracking-wider">
                {product.product_type.replace('_', ' ')}
              </span>
              <span className="px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1" />
                {product.access_duration}
              </span>
              {purchaseState === 'OWNED' && (
                <span className="px-3 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full flex items-center">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Already Owned
                </span>
              )}
              {purchaseState === 'UNLOCKED_VIA_PASS' && (
                <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-bold rounded-full flex items-center">
                  🔓 Unlocked via Class Pass
                </span>
              )}
              {purchaseState === 'UPGRADE' && (
                <span className="px-3 py-1 bg-amber-100 text-amber-800 text-xs font-bold rounded-full flex items-center">
                  <Sparkles className="w-3.5 h-3.5 mr-1" /> Upgrade Eligible
                </span>
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {product.title}
            </h1>

            {product.description && (
              <p className="mt-4 text-slate-600 leading-relaxed text-base">
                {product.description}
              </p>
            )}

            {/* Pass Validity Notice if applicable */}
            {product.pass_duration_days && (
              <div className="mt-6 p-4 rounded-2xl bg-indigo-50/70 border border-indigo-100 flex items-start space-x-3">
                <Calendar className="w-5 h-5 text-indigo-600 mt-0.5 shrink-0" />
                <div className="text-sm">
                  <p className="font-bold text-indigo-950">
                    {product.pass_duration_days}-Day Comprehensive All-Subject Access
                  </p>
                  <p className="text-indigo-700 mt-0.5">
                    Unlocks all chapter notes, study guides, and subject packs across the entire class curriculum.
                    Stackable renewal extends seamlessly.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Upgrade Credit Breakdown Box */}
          {purchaseState === 'UPGRADE' && priceCalc && priceCalc.upgrade_credit_paise > 0 && (
            <div className="bg-amber-50/70 border-2 border-amber-200 rounded-3xl p-6 sm:p-7">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 bg-amber-100 text-amber-800 rounded-2xl">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-amber-950">Prorated Upgrade Discount Applied</h3>
                  <p className="text-xs text-amber-800 mt-0.5">
                    Because you already purchased individual chapters in this subject, 100% of your prior payments are credited toward this Subject Pack!
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-2.5 bg-white/80 backdrop-blur-xs p-4 rounded-2xl border border-amber-200/60">
                <div className="flex justify-between text-sm text-slate-600">
                  <span>Regular Subject Pack Price:</span>
                  <span className="font-semibold text-slate-900">₹{basePriceInr.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm text-emerald-700 font-medium">
                  <span>Upgrade Credit ({priceCalc.owned_chapters_count} owned chapter(s)):</span>
                  <span className="font-bold">-₹{upgradeCreditInr.toFixed(2)}</span>
                </div>
                <div className="pt-2 border-t border-amber-200 flex justify-between text-base font-black text-amber-950">
                  <span>Net Upgrade Price Payable:</span>
                  <span className="text-xl font-black text-indigo-700">₹{effectivePriceInr.toFixed(2)}</span>
                </div>
              </div>

              {priceCalc.owned_chapters && priceCalc.owned_chapters.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-bold text-amber-900 uppercase tracking-wider mb-2">
                    Credited Chapters:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {priceCalc.owned_chapters.map((ch) => (
                      <span
                        key={ch.chapter_id}
                        className="px-2.5 py-1 bg-amber-100/80 text-amber-900 text-xs font-semibold rounded-lg"
                      >
                        Ch. {ch.chapter_number}: {ch.chapter_title} (+₹{ch.credit_inr.toFixed(2)})
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Inclusions Breakdown */}
          {product.inclusions && product.inclusions.length > 0 && (
            <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-slate-900 flex items-center">
                  <Layers className="w-5 h-5 mr-2 text-indigo-600" /> Included in this Product ({product.inclusions.length})
                </h3>
              </div>
              <div className="divide-y divide-slate-100">
                {product.inclusions.map((item, idx) => (
                  <div key={idx} className="py-3.5 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-xs">
                        {item.chapter_number || idx + 1}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-800">{item.title}</p>
                        {item.subject && (
                          <p className="text-xs text-slate-400">{item.subject}</p>
                        )}
                      </div>
                    </div>
                    {item.is_free_sample && (
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded-md">
                        FREE SAMPLE
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Checkout Card & Dynamic Action Button */}
        <div className="space-y-6">
          <div className="bg-white rounded-3xl p-6 sm:p-7 border border-slate-200 shadow-md sticky top-24">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
              Pricing & Access
            </h3>

            {/* Price Box */}
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl sm:text-4xl font-black text-slate-900">
                ₹{effectivePriceInr.toFixed(2)}
              </span>
              {upgradeCreditInr > 0 && (
                <span className="text-base text-slate-400 line-through">
                  ₹{basePriceInr.toFixed(2)}
                </span>
              )}
              <span className="text-xs font-bold text-slate-500 uppercase">
                (Inclusive of 18% GST)
              </span>
            </div>

            {/* Dynamic Action Buttons */}
            <div className="mt-6 space-y-3">
              {purchaseState === 'BUY' && (
                <>
                  <button
                    onClick={handleBuyNow}
                    className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl shadow-sm shadow-indigo-200 hover:shadow-indigo-300 transition-all flex items-center justify-center space-x-2 cursor-pointer"
                  >
                    <span>Buy Now • ₹{effectivePriceInr.toFixed(2)}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleAddToCart}
                    className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold rounded-2xl transition cursor-pointer"
                  >
                    Add to Cart
                  </button>
                </>
              )}

              {purchaseState === 'UPGRADE' && (
                <>
                  <button
                    onClick={handleBuyNow}
                    className="w-full py-3.5 px-4 bg-amber-500 hover:bg-amber-600 text-white font-black rounded-2xl shadow-sm shadow-amber-200 transition-all flex items-center justify-center space-x-2 cursor-pointer"
                  >
                    <Sparkles className="w-4 h-4" />
                    <span>Upgrade Now • ₹{effectivePriceInr.toFixed(2)}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleAddToCart}
                    className="w-full py-3 px-4 bg-amber-50 hover:bg-amber-100 text-amber-900 font-semibold rounded-2xl transition cursor-pointer"
                  >
                    Add to Cart (Upgrade)
                  </button>
                </>
              )}

              {purchaseState === 'OWNED' && (
                <div className="space-y-3">
                  <div className="w-full py-3.5 px-4 bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold rounded-2xl flex items-center justify-center space-x-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>Already in Your Collection ✓</span>
                  </div>
                  <Link
                    to="/library"
                    className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-2xl shadow-sm transition flex items-center justify-center space-x-2"
                  >
                    <BookOpen className="w-4 h-4" />
                    <span>Open in My Library</span>
                  </Link>
                </div>
              )}

              {purchaseState === 'UNLOCKED_VIA_PASS' && (
                <div className="space-y-3">
                  <div className="w-full py-3.5 px-4 bg-purple-50 border border-purple-200 text-purple-900 font-bold rounded-2xl flex items-center justify-center space-x-2">
                    <Lock className="w-4 h-4 text-purple-600" />
                    <span>Unlocked with Active Pass 🔓</span>
                  </div>
                  <Link
                    to="/library"
                    className="w-full py-3.5 px-4 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-2xl shadow-sm transition flex items-center justify-center space-x-2"
                  >
                    <ExternalLink className="w-4 h-4" />
                    <span>Read in Library</span>
                  </Link>
                </div>
              )}
            </div>

            {/* 18% GST Details Toggle */}
            <div className="mt-6 pt-5 border-t border-slate-100">
              <button
                onClick={() => setShowGstDetails(!showGstDetails)}
                className="w-full flex items-center justify-between text-xs font-bold text-slate-500 hover:text-indigo-600 transition cursor-pointer"
              >
                <span className="flex items-center">
                  <Receipt className="w-3.5 h-3.5 mr-1.5" /> 18% Inclusive GST Breakdown
                </span>
                <span>{showGstDetails ? '▲ Hide' : '▼ Details'}</span>
              </button>

              {showGstDetails && gst && (
                <div className="mt-3 p-3 bg-slate-50 rounded-xl space-y-1.5 text-xs text-slate-600">
                  <div className="flex justify-between">
                    <span>Taxable Base Value:</span>
                    <span className="font-semibold">
                      ₹{((gst.base_taxable_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>CGST (9%):</span>
                    <span className="font-semibold">
                      ₹{((gst.cgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>SGST (9%):</span>
                    <span className="font-semibold">
                      ₹{((gst.sgst_paise || 0) / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="pt-1.5 border-t border-slate-200 flex justify-between font-bold text-slate-900">
                    <span>Total GST (18%):</span>
                    <span>₹{((gst.total_gst_paise || 0) / 100).toFixed(2)}</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
