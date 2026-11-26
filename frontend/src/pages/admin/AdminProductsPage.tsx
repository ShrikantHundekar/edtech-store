import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  Tag,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  Loader2,
  BookOpen,
  Layers,
  GraduationCap,
  Calendar,
  Gift,
  Filter,
} from 'lucide-react';
import { adminProductService } from '../../services/adminProductService';
import { ProductFormModal } from '../../components/admin/ProductFormModal';
import type { Product, ProductType } from '../../types/product';

export const AdminProductsPage: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [activeFilter, setActiveFilter] = useState<string>('ALL');

  // Modal States
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  // Quick Price Edit States
  const [quickPriceId, setQuickPriceId] = useState<number | null>(null);
  const [quickPriceInput, setQuickPriceInput] = useState<string>('');
  const [updatingPrice, setUpdatingPrice] = useState(false);

  // Status/Alert Feedback
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await adminProductService.getProducts();
      setProducts(data);
    } catch {
      setFeedback({ type: 'error', message: 'Failed to load products list.' });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete product "${title}"?`)) {
      return;
    }
    try {
      await adminProductService.deleteProduct(id);
      setProducts((prev) => prev.filter((p) => p.id !== id));
      setFeedback({ type: 'success', message: `Product "${title}" deleted successfully.` });
    } catch {
      setFeedback({ type: 'error', message: 'Failed to delete product.' });
    }
  };

  const handleQuickPriceSave = async (productId: number) => {
    const rupees = parseFloat(quickPriceInput);
    if (isNaN(rupees) || rupees < 0) {
      alert('Please enter a valid price in rupees.');
      return;
    }
    const paise = Math.round(rupees * 100);
    setUpdatingPrice(true);
    try {
      await adminProductService.setPrice(productId, paise);
      setProducts((prev) =>
        prev.map((p) => {
          if (p.id === productId) {
            return {
              ...p,
              current_price_paise: paise,
              current_price_inr: paise / 100,
            };
          }
          return p;
        })
      );
      setQuickPriceId(null);
      setFeedback({ type: 'success', message: `Price updated to ₹${(paise / 100).toFixed(2)}.` });
    } catch {
      setFeedback({ type: 'error', message: 'Failed to update price.' });
    } finally {
      setUpdatingPrice(false);
    }
  };

  // Filter products
  const filteredProducts = products.filter((p) => {
    const matchesQuery =
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.slug.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.subject_name && p.subject_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (p.class_name && p.class_name.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesType = typeFilter === 'ALL' || p.product_type === typeFilter;
    const matchesActive =
      activeFilter === 'ALL' ||
      (activeFilter === 'ACTIVE' && p.is_active) ||
      (activeFilter === 'INACTIVE' && !p.is_active);

    return matchesQuery && matchesType && matchesActive;
  });

  const getProductTypeIcon = (type: ProductType) => {
    switch (type) {
      case 'CHAPTER_NOTES':
        return <BookOpen className="w-3.5 h-3.5 text-blue-600" />;
      case 'SUBJECT_PACK':
        return <Layers className="w-3.5 h-3.5 text-purple-600" />;
      case 'MONTHLY_PASS':
        return <Calendar className="w-3.5 h-3.5 text-emerald-600" />;
      case 'ANNUAL_PASS':
        return <GraduationCap className="w-3.5 h-3.5 text-amber-600" />;
      case 'BUNDLE':
        return <Tag className="w-3.5 h-3.5 text-pink-600" />;
      case 'FREE_SAMPLE':
        return <Gift className="w-3.5 h-3.5 text-rose-600" />;
    }
  };

  const getProductTypeBadge = (type: ProductType, display: string) => {
    const styles: Record<ProductType, string> = {
      CHAPTER_NOTES: 'bg-blue-50 text-blue-700 border-blue-200',
      SUBJECT_PACK: 'bg-purple-50 text-purple-700 border-purple-200',
      MONTHLY_PASS: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      ANNUAL_PASS: 'bg-amber-50 text-amber-700 border-amber-200',
      BUNDLE: 'bg-pink-50 text-pink-700 border-pink-200',
      FREE_SAMPLE: 'bg-rose-50 text-rose-700 border-rose-200',
    };
    return (
      <span
        className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${
          styles[type] || 'bg-slate-100 text-slate-700 border-slate-200'
        }`}
      >
        {getProductTypeIcon(type)}
        <span>{display || type}</span>
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50/60 pb-16">
      {/* Top Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-3">
                <span className="px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200">
                  Admin Workspace
                </span>
                <span className="text-slate-300">|</span>
                <Link
                  to="/admin/curriculum"
                  className="text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors"
                >
                  Curriculum Tree &rarr;
                </Link>
              </div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-1 flex items-center space-x-2">
                <span>Products & Pricing Configuration</span>
                <span className="text-base font-normal text-slate-400">({products.length})</span>
              </h1>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => {
                  setEditingProduct(null);
                  setIsModalOpen(true);
                }}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl shadow-md shadow-indigo-600/20 transition-all flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Create Product</span>
              </button>
            </div>
          </div>

          {/* Feedback alert */}
          {feedback && (
            <div
              className={`mt-4 p-3.5 rounded-xl border flex items-center justify-between text-sm ${
                feedback.type === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}
            >
              <div className="flex items-center space-x-2">
                {feedback.type === 'success' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                )}
                <span>{feedback.message}</span>
              </div>
              <button
                onClick={() => setFeedback(null)}
                className="text-xs font-semibold uppercase hover:underline ml-4"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Search & Filters */}
          <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search products by title, slug, subject..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>

            <div className="relative">
              <Filter className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full pl-9 pr-8 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none appearance-none"
              >
                <option value="ALL">All Product Classifications</option>
                <option value="CHAPTER_NOTES">Chapter Notes</option>
                <option value="SUBJECT_PACK">Subject Packs</option>
                <option value="MONTHLY_PASS">Monthly Class Passes</option>
                <option value="ANNUAL_PASS">Annual Class Passes</option>
                <option value="BUNDLE">Custom Bundles</option>
                <option value="FREE_SAMPLE">Free Samples</option>
              </select>
            </div>

            <div>
              <select
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value)}
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="ALL">All Statuses (Active & Inactive)</option>
                <option value="ACTIVE">Active Only</option>
                <option value="INACTIVE">Inactive Only</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-16 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            <p className="text-sm font-semibold text-slate-600">Loading catalog products and prices...</p>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center space-y-3">
            <Tag className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-bold text-slate-800">No products found</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              No products match your current search or filter criteria. Create your first product or clear filters.
            </p>
            <button
              onClick={() => {
                setSearchQuery('');
                setTypeFilter('ALL');
                setActiveFilter('ALL');
              }}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-colors"
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th className="py-3.5 px-4">Product Details</th>
                    <th className="py-3.5 px-4">Type</th>
                    <th className="py-3.5 px-4">Catalog Scope</th>
                    <th className="py-3.5 px-4">Duration</th>
                    <th className="py-3.5 px-4">Price (₹ / Paise)</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-sm">
                  {filteredProducts.map((p) => (
                    <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                      {/* Title & Slug */}
                      <td className="py-4 px-4">
                        <div className="font-bold text-slate-900">{p.title}</div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">/{p.slug}</div>
                      </td>

                      {/* Classification Badge */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        {getProductTypeBadge(p.product_type, (p as { product_type_display?: string }).product_type_display || p.product_type)}
                      </td>

                      {/* Scope Hierarchy */}
                      <td className="py-4 px-4 text-xs text-slate-600">
                        {p.board_name && <span className="font-semibold text-slate-800">{p.board_name}</span>}
                        {p.class_name && <span> &bull; {p.class_name}</span>}
                        {p.subject_name && <span> &bull; {p.subject_name}</span>}
                        {p.chapter_title && <span className="text-slate-500 block mt-0.5">Ch: {p.chapter_title}</span>}
                        {!p.board_name && !p.class_name && !p.subject_name && (
                          <span className="text-slate-400 italic">No scope linked</span>
                        )}
                      </td>

                      {/* Duration */}
                      <td className="py-4 px-4 whitespace-nowrap text-xs font-medium text-slate-700">
                        {p.access_duration}
                      </td>

                      {/* Price in Rupees / Paise */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        {quickPriceId === p.id ? (
                          <div className="flex items-center space-x-1.5">
                            <span className="font-bold text-xs text-slate-500">₹</span>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={quickPriceInput}
                              onChange={(e) => setQuickPriceInput(e.target.value)}
                              className="w-20 px-2 py-1 text-xs border border-indigo-400 rounded-lg outline-none font-bold"
                              autoFocus
                            />
                            <button
                              disabled={updatingPrice}
                              onClick={() => handleQuickPriceSave(p.id)}
                              className="px-2 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                            >
                              {updatingPrice ? '...' : 'Save'}
                            </button>
                            <button
                              onClick={() => setQuickPriceId(null)}
                              className="px-2 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg text-xs"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center space-x-2">
                            <div>
                              <span className="font-black text-slate-900 text-sm">
                                {p.product_type === 'FREE_SAMPLE'
                                  ? '₹0.00'
                                  : `₹${((p.current_price_paise ?? p.price_paise ?? 0) / 100).toFixed(2)}`}
                              </span>
                              <span className="text-[11px] text-slate-400 font-mono block">
                                {p.current_price_paise ?? p.price_paise ?? 0} paise
                              </span>
                            </div>
                            {p.product_type !== 'FREE_SAMPLE' && (
                              <button
                                onClick={() => {
                                  const effectivePaise = p.current_price_paise ?? p.price_paise ?? 0;
                                  setQuickPriceId(p.id);
                                  setQuickPriceInput((effectivePaise / 100).toString());
                                }}
                                title="Quick price update"
                                className="p-1 text-slate-400 hover:text-indigo-600 rounded hover:bg-indigo-50 transition-colors"
                              >
                                <DollarSign className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                            p.is_active
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                          }`}
                        >
                          {p.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="py-4 px-4 text-right whitespace-nowrap space-x-2">
                        <button
                          onClick={() => {
                            setEditingProduct(p);
                            setIsModalOpen(true);
                          }}
                          className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                          title="Edit Product"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(p.id, p.title)}
                          className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                          title="Delete Product"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Product Form Modal */}
      <ProductFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          loadProducts();
          setFeedback({
            type: 'success',
            message: editingProduct
              ? 'Product and pricing updated successfully.'
              : 'Product created successfully.',
          });
        }}
        productToEdit={editingProduct}
      />
    </div>
  );
};
