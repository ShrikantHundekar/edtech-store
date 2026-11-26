import React, { useState, useEffect } from 'react';
import {
  X,
  Loader2,
  DollarSign,
  AlertCircle,
  HelpCircle,
  Tag,
  BookOpen,
  Layers,
  GraduationCap,
  Calendar,
  Gift,
} from 'lucide-react';
import type { Product, ProductType } from '../../types/product';
import type { Board, ClassLevel, Subject, Chapter } from '../../types/catalog';
import { adminCatalogService } from '../../services/adminCatalogService';
import { adminProductService, type AdminProductInput } from '../../services/adminProductService';

interface ProductFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  productToEdit?: Product | null;
}

export const ProductFormModal: React.FC<ProductFormModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  productToEdit,
}) => {
  const [productType, setProductType] = useState<ProductType>('CHAPTER_NOTES');
  const [title, setTitle] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [priceRupees, setPriceRupees] = useState<string>('');
  const [isActive, setIsActive] = useState(true);

  // Catalog Scopes
  const [boardId, setBoardId] = useState<number | ''>('');
  const [classId, setClassId] = useState<number | ''>('');
  const [subjectId, setSubjectId] = useState<number | ''>('');
  const [chapterId, setChapterId] = useState<number | ''>('');

  // Dropdown options
  const [boards, setBoards] = useState<Board[]>([]);
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  const [loadingScopes, setLoadingScopes] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize data on open
  useEffect(() => {
    if (!isOpen) return;

    setError(null);
    loadInitialScopes();

    if (productToEdit) {
      setProductType(productToEdit.product_type);
      setTitle(productToEdit.title);
      setSlug(productToEdit.slug);
      setDescription(productToEdit.description || '');
      setPriceRupees(
        productToEdit.product_type === 'FREE_SAMPLE'
          ? '0'
          : (productToEdit.current_price_paise / 100).toString()
      );
      setIsActive(productToEdit.is_active);
      setBoardId(productToEdit.board || '');
      setClassId(productToEdit.academic_class || '');
      setSubjectId(productToEdit.subject || '');
      setChapterId(productToEdit.chapter || '');
    } else {
      setProductType('CHAPTER_NOTES');
      setTitle('');
      setSlug('');
      setDescription('');
      setPriceRupees('49');
      setIsActive(true);
      setBoardId('');
      setClassId('');
      setSubjectId('');
      setChapterId('');
    }
  }, [isOpen, productToEdit]);

  // Load Boards
  const loadInitialScopes = async () => {
    setLoadingScopes(true);
    try {
      const boardsData = await adminCatalogService.getBoards();
      setBoards(boardsData);
    } catch {
      setError('Failed to load boards list.');
    } finally {
      setLoadingScopes(false);
    }
  };

  // Load classes when board changes
  useEffect(() => {
    if (boardId) {
      adminCatalogService.getClasses(Number(boardId)).then(setClasses).catch(() => {});
    } else {
      setClasses([]);
    }
  }, [boardId]);

  // Load subjects when class changes
  useEffect(() => {
    if (classId) {
      adminCatalogService.getSubjects(Number(classId)).then(setSubjects).catch(() => {});
    } else {
      setSubjects([]);
    }
  }, [classId]);

  // Load chapters when subject changes
  useEffect(() => {
    if (subjectId) {
      adminCatalogService.getChapters(Number(subjectId)).then(setChapters).catch(() => {});
    } else {
      setChapters([]);
    }
  }, [subjectId]);

  if (!isOpen) return null;

  // Real-time calculation helpers
  const numericRupees = parseFloat(priceRupees) || 0;
  const calculatedPaise = Math.round(numericRupees * 100);
  // 18% inclusive GST calculation:
  // Base taxable = (Paise * 100) / 118
  // Total GST = Paise - Base Taxable
  const baseTaxablePaise = Math.round((calculatedPaise * 100) / 118);
  const totalGstPaise = calculatedPaise - baseTaxablePaise;
  const cgstPaise = Math.round(totalGstPaise / 2);
  const sgstPaise = totalGstPaise - cgstPaise;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError('Product title is required.');
      return;
    }

    if (productType === 'CHAPTER_NOTES' || productType === 'FREE_SAMPLE') {
      if (!chapterId) {
        setError('Please select a Chapter for this product.');
        return;
      }
    } else if (productType === 'SUBJECT_PACK') {
      if (!subjectId) {
        setError('Please select a Subject for this Subject Pack.');
        return;
      }
    } else if (productType === 'MONTHLY_PASS' || productType === 'ANNUAL_PASS') {
      if (!classId) {
        setError('Please select a Class for this Class Pass.');
        return;
      }
    }

    if (productType !== 'FREE_SAMPLE' && (isNaN(numericRupees) || numericRupees < 0)) {
      setError('Please provide a valid price greater than or equal to 0.');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload: AdminProductInput = {
        title: title.trim(),
        slug: slug.trim() || undefined,
        product_type: productType,
        description: description.trim() || undefined,
        is_active: isActive,
        amount_paise: productType === 'FREE_SAMPLE' ? 0 : calculatedPaise,
        board: boardId ? Number(boardId) : null,
        academic_class: classId ? Number(classId) : null,
        subject: subjectId ? Number(subjectId) : null,
        chapter: chapterId ? Number(chapterId) : null,
      };

      if (productToEdit) {
        await adminProductService.updateProduct(productToEdit.id, payload);
      } else {
        await adminProductService.createProduct(payload);
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      const errResponse = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      if (errResponse) {
        const msg = Object.entries(errResponse)
          .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(', ') : val}`)
          .join(' | ');
        setError(msg || 'An error occurred while saving the product.');
      } else {
        setError('Failed to save product. Please verify inputs.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl my-8 overflow-hidden transform transition-all">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-indigo-900 to-indigo-800 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
              <Tag className="w-5 h-5 text-indigo-200" />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {productToEdit ? 'Edit Product & Pricing' : 'Create New Product'}
              </h2>
              <p className="text-xs text-indigo-200">
                Configure commercial catalog scopes, access duration, and price points
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-indigo-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Product Type Selector */}
          <div>
            <label className="block text-sm font-semibold text-slate-800 mb-2">
              Product Classification
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
              {[
                { type: 'CHAPTER_NOTES', label: 'Chapter Notes', icon: BookOpen, desc: 'Single chapter' },
                { type: 'SUBJECT_PACK', label: 'Subject Pack', icon: Layers, desc: 'All chapters' },
                { type: 'MONTHLY_PASS', label: 'Monthly Pass', icon: Calendar, desc: '30-day class access' },
                { type: 'ANNUAL_PASS', label: 'Annual Pass', icon: GraduationCap, desc: '365-day class access' },
                { type: 'BUNDLE', label: 'Custom Bundle', icon: Tag, desc: 'Curated bundle' },
                { type: 'FREE_SAMPLE', label: 'Free Sample', icon: Gift, desc: 'Zero cost preview' },
              ].map(({ type, label, icon: Icon, desc }) => (
                <button
                  type="button"
                  key={type}
                  onClick={() => setProductType(type as ProductType)}
                  className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between ${
                    productType === type
                      ? 'border-indigo-600 bg-indigo-50/70 text-indigo-900 shadow-sm ring-2 ring-indigo-500/20'
                      : 'border-slate-200 hover:border-slate-300 text-slate-700 bg-white'
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <Icon className={`w-4 h-4 ${productType === type ? 'text-indigo-600' : 'text-slate-400'}`} />
                    <span className="font-semibold text-xs">{label}</span>
                  </div>
                  <span className="text-[11px] text-slate-500 mt-1">{desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Title & Slug */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Product Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Class 10 Physics Complete Pack"
                required
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Slug (Optional)
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="Auto-generated if empty"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Description & Inclusions Summary
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Detailed description of coverage, revision notes, sample questions, and duration..."
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none resize-none"
            />
          </div>

          {/* Catalog Scope Hierarchy (Dynamic based on product type) */}
          <div className="bg-slate-50/80 p-4 rounded-xl border border-slate-200/80 space-y-4">
            <div className="flex items-center space-x-2 text-slate-800 font-semibold text-sm">
              <GraduationCap className="w-4 h-4 text-indigo-600" />
              <span>Catalog Scope Association</span>
            </div>

            {loadingScopes ? (
              <div className="flex items-center space-x-2 text-slate-500 text-xs py-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                <span>Loading curriculum hierarchy...</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                {/* Board Selector */}
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">
                    Board {productType !== 'BUNDLE' && '*'}
                  </label>
                  <select
                    value={boardId}
                    onChange={(e) => {
                      setBoardId(e.target.value ? Number(e.target.value) : '');
                      setClassId('');
                      setSubjectId('');
                      setChapterId('');
                    }}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select Board</option>
                    {boards.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Class Selector */}
                <div>
                  <label className="block font-semibold text-slate-600 mb-1">
                    Academic Class {(productType === 'MONTHLY_PASS' || productType === 'ANNUAL_PASS') && '*'}
                  </label>
                  <select
                    value={classId}
                    disabled={!boardId}
                    onChange={(e) => {
                      setClassId(e.target.value ? Number(e.target.value) : '');
                      setSubjectId('');
                      setChapterId('');
                    }}
                    className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                  >
                    <option value="">Select Class</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Subject Selector */}
                {(productType === 'CHAPTER_NOTES' ||
                  productType === 'SUBJECT_PACK' ||
                  productType === 'FREE_SAMPLE') && (
                  <div>
                    <label className="block font-semibold text-slate-600 mb-1">
                      Subject {productType === 'SUBJECT_PACK' && '*'}
                    </label>
                    <select
                      value={subjectId}
                      disabled={!classId}
                      onChange={(e) => {
                        setSubjectId(e.target.value ? Number(e.target.value) : '');
                        setChapterId('');
                      }}
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      <option value="">Select Subject</option>
                      {subjects.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Chapter Selector */}
                {(productType === 'CHAPTER_NOTES' || productType === 'FREE_SAMPLE') && (
                  <div>
                    <label className="block font-semibold text-slate-600 mb-1">Chapter *</label>
                    <select
                      value={chapterId}
                      disabled={!subjectId}
                      onChange={(e) => setChapterId(e.target.value ? Number(e.target.value) : '')}
                      className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
                    >
                      <option value="">Select Chapter</option>
                      {chapters.map((ch) => (
                        <option key={ch.id} value={ch.id}>
                          Ch {ch.chapter_number}: {ch.title}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Pricing & GST Configuration Section */}
          <div className="bg-gradient-to-br from-indigo-50/50 to-slate-50 p-5 rounded-2xl border border-indigo-100 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <DollarSign className="w-5 h-5 text-indigo-600" />
                <span className="font-bold text-sm text-slate-900">Pricing & GST Configuration</span>
              </div>
              <div className="flex items-center space-x-1.5 text-xs text-indigo-700 bg-indigo-100/70 px-2.5 py-1 rounded-full font-medium">
                <HelpCircle className="w-3.5 h-3.5" />
                <span>18% GST Inclusive Rate</span>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Retail Price (₹ Rupees)
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 font-bold text-slate-500">
                    ₹
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    disabled={productType === 'FREE_SAMPLE'}
                    value={productType === 'FREE_SAMPLE' ? '0' : priceRupees}
                    onChange={(e) => setPriceRupees(e.target.value)}
                    placeholder="e.g. 199.00"
                    className="w-full pl-8 pr-3.5 py-2.5 bg-white border border-slate-300 rounded-xl text-base font-bold text-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none disabled:bg-slate-100 disabled:text-slate-400"
                  />
                </div>
                <p className="text-[11px] text-slate-500 mt-1">
                  Stored as <span className="font-semibold text-indigo-700 font-mono">{calculatedPaise} paise</span> in database
                </p>
              </div>

              {/* 18% Inclusive GST Realtime Preview Card */}
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 text-xs space-y-1.5 shadow-sm">
                <div className="flex justify-between text-slate-600">
                  <span>Base Taxable (84.75%):</span>
                  <span className="font-semibold text-slate-900 font-mono">₹{(baseTaxablePaise / 100).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>CGST (9.0%):</span>
                  <span className="font-semibold text-slate-900 font-mono">₹{(cgstPaise / 100).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>SGST (9.0%):</span>
                  <span className="font-semibold text-slate-900 font-mono">₹{(sgstPaise / 100).toFixed(2)}</span>
                </div>
                <div className="pt-1.5 border-t border-slate-100 flex justify-between font-bold text-indigo-700 text-sm">
                  <span>Total Payable:</span>
                  <span className="font-mono">₹{(calculatedPaise / 100).toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Visibility Switch */}
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div>
              <span className="font-semibold text-sm text-slate-900">Active Status</span>
              <p className="text-xs text-slate-500">
                Inactive products are hidden from the public catalog and search listings
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
            </label>
          </div>

          {/* Submit Actions */}
          <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md shadow-indigo-600/20 transition-all flex items-center space-x-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>{productToEdit ? 'Update Product' : 'Create Product'}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
