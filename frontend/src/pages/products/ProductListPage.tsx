import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  BookOpen,
  ArrowRight,
  Search,
  Filter,
  Layers,
  Clock,
} from 'lucide-react';
import { productService } from '../../services/productService';
import type { Product, ProductType } from '../../types/product';

export const ProductListPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialType = searchParams.get('type') || searchParams.get('product_type') || 'ALL';
  const subjectIdParam = searchParams.get('subject_id');
  const chapterIdParam = searchParams.get('chapter_id');

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string>(initialType);
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      setError(null);
      try {
        const params: Record<string, any> = {};
        if (selectedType !== 'ALL') {
          params.product_type = selectedType as ProductType;
        }
        if (subjectIdParam) {
          params.subject_id = subjectIdParam;
        }
        if (chapterIdParam) {
          params.chapter_id = chapterIdParam;
        }
        const data = await productService.getProducts(params);
        setProducts(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch products';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [selectedType, subjectIdParam, chapterIdParam]);

  const filteredProducts = products.filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      p.title.toLowerCase().includes(q) ||
      (p.subject_name && p.subject_name.toLowerCase().includes(q)) ||
      (p.class_name && p.class_name.toLowerCase().includes(q))
    );
  });

  const filterTabs = [
    { label: 'All Products', value: 'ALL' },
    { label: 'Chapter Notes', value: 'CHAPTER_NOTES' },
    { label: 'Subject Packs', value: 'SUBJECT_PACK' },
    { label: 'Monthly Passes', value: 'MONTHLY_PASS' },
    { label: 'Annual Passes', value: 'ANNUAL_PASS' },
    { label: 'Bundles', value: 'BUNDLE' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-8 border-b border-slate-200">
        <div>
          <span className="text-xs font-black uppercase tracking-widest text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
            CBSE Digital Notes & Passes
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 mt-2 tracking-tight">
            Curriculum Products
          </h1>
          <p className="mt-1 text-slate-600 text-sm sm:text-base">
            Explore chapter notes, subject packs, and all-access class passes.
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search notes, subjects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-2xs"
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="mt-6 flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-none">
        <Filter className="w-4 h-4 text-slate-400 mr-1 shrink-0" />
        {filterTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              setSelectedType(tab.value);
              if (tab.value === 'ALL') {
                setSearchParams({});
              } else {
                setSearchParams({ type: tab.value });
              }
            }}
            className={`px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition cursor-pointer ${
              selectedType === tab.value
                ? 'bg-indigo-600 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Loading & Error States */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center">
          <div className="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
          <p className="mt-3 text-sm text-slate-500 font-medium">Loading products...</p>
        </div>
      ) : error ? (
        <div className="py-16 text-center text-rose-600 font-medium">{error}</div>
      ) : filteredProducts.length === 0 ? (
        <div className="py-16 text-center text-slate-500">
          <BookOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" />
          <p className="font-semibold text-slate-700">No products found</p>
          <p className="text-sm text-slate-400 mt-1">Try selecting a different category or search term.</p>
        </div>
      ) : (
        /* Products Grid */
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProducts.map((product) => {
            const price = (product as unknown as { price_inr?: number }).price_inr ?? product.current_price_inr;
            return (
              <div
                key={product.id}
                className="bg-white rounded-3xl border border-slate-200/80 p-6 flex flex-col justify-between hover:shadow-lg hover:border-slate-300 transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-[11px] font-bold rounded-lg uppercase tracking-wider">
                      {product.product_type.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-slate-400 flex items-center font-medium">
                      <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      {product.access_duration}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
                    {product.title}
                  </h3>

                  <div className="mt-2 flex items-center space-x-2 text-xs text-slate-500">
                    {product.class_name && <span>{product.class_name}</span>}
                    {product.subject_name && <span>• {product.subject_name}</span>}
                  </div>

                  {product.description && (
                    <p className="mt-3 text-xs text-slate-600 line-clamp-2">
                      {product.description}
                    </p>
                  )}

                  {product.inclusions && product.inclusions.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center text-xs text-slate-500">
                      <Layers className="w-3.5 h-3.5 mr-1 text-indigo-500" />
                      <span>Includes {product.inclusions.length} chapter note(s)</span>
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-2xl font-black text-slate-900">
                      ₹{price.toFixed(2)}
                    </span>
                    <span className="block text-[10px] text-slate-400 font-semibold uppercase">
                      Incl. 18% GST
                    </span>
                  </div>

                  <Link
                    to={`/products/${product.id}`}
                    className="inline-flex items-center px-4 py-2 bg-slate-900 text-white group-hover:bg-indigo-600 rounded-xl text-xs font-bold transition shadow-xs"
                  >
                    <span>View</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
