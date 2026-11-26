import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus,
  Sparkles,
  Edit2,
  Trash2,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Calendar,
} from 'lucide-react';
import { bannerService } from '../../services/bannerService';
import { BannerFormModal } from '../../components/admin/BannerFormModal';
import type { PromoBanner } from '../../types/banner';

export const AdminBannersPage: React.FC = () => {
  const [banners, setBanners] = useState<PromoBanner[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBanner, setEditingBanner] = useState<PromoBanner | null>(null);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    loadBanners();
  }, []);

  const loadBanners = async () => {
    setLoading(true);
    try {
      const data = await bannerService.getAdminBanners();
      setBanners(data);
    } catch {
      setFeedback({ type: 'error', message: 'Failed to load promotional banners.' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (banner: PromoBanner) => {
    try {
      const updated = await bannerService.updateBanner(banner.id, { is_active: !banner.is_active });
      setBanners((prev) => prev.map((b) => (b.id === banner.id ? updated : b)));
      setFeedback({
        type: 'success',
        message: `Banner "${banner.title}" is now ${updated.is_active ? 'Visible' : 'Hidden'}.`,
      });
    } catch {
      setFeedback({ type: 'error', message: 'Failed to update banner status.' });
    }
  };

  const handleDelete = async (banner: PromoBanner) => {
    if (!window.confirm(`Are you sure you want to remove banner "${banner.title}"?`)) {
      return;
    }
    try {
      await bannerService.deleteBanner(banner.id);
      setBanners((prev) => prev.filter((b) => b.id !== banner.id));
      setFeedback({ type: 'success', message: 'Banner removed successfully.' });
    } catch {
      setFeedback({ type: 'error', message: 'Failed to delete banner.' });
    }
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
                  Curriculum &rarr;
                </Link>
                <Link
                  to="/admin/products"
                  className="text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors"
                >
                  Products &rarr;
                </Link>
              </div>
              <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-1 flex items-center space-x-2">
                <span>Promotional Hero Banners</span>
                <span className="text-base font-normal text-slate-400">({banners.length})</span>
              </h1>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => {
                  setEditingBanner(null);
                  setIsModalOpen(true);
                }}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-xl shadow-md transition-all flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add New Banner</span>
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
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
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
        </div>
      </div>

      {/* Main Banner List */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-16 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
            <p className="text-sm font-semibold text-slate-600">Loading promotional banners...</p>
          </div>
        ) : banners.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center space-y-3">
            <Sparkles className="w-12 h-12 text-slate-300 mx-auto" />
            <h3 className="text-lg font-bold text-slate-800">No banners created</h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Create a promotional hero banner to pitch passes and key discounts to students on the curriculum store.
            </p>
            <button
              onClick={() => {
                setEditingBanner(null);
                setIsModalOpen(true);
              }}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-xs"
            >
              Create First Banner
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {banners.map((banner) => (
              <div
                key={banner.id}
                className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-all"
              >
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
                  {/* Banner Preview Card */}
                  <div
                    className={`flex-1 rounded-2xl bg-gradient-to-r ${banner.gradient_theme || 'from-indigo-900 via-indigo-800 to-purple-900'} p-6 text-white shadow-md relative overflow-hidden`}
                  >
                    <div className="relative z-10 max-w-xl">
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-400 text-amber-950 mb-3 shadow-xs">
                        {banner.badge_text || '⚡ Promo'}
                      </span>
                      <h3 className="text-xl sm:text-2xl font-black tracking-tight">{banner.title}</h3>
                      <p className="mt-2 text-xs sm:text-sm text-indigo-100 line-clamp-2">
                        {banner.description}
                      </p>

                      <div className="mt-5 flex flex-wrap gap-3">
                        <div className="px-4 py-2 rounded-xl bg-white text-indigo-950 font-bold text-xs flex items-center gap-2">
                          <Calendar className="w-3.5 h-3.5 text-indigo-600" />
                          <span>{banner.monthly_pass_text}</span>
                        </div>
                        <div className="px-4 py-2 rounded-xl bg-amber-400 text-amber-950 font-bold text-xs flex items-center gap-2">
                          <Sparkles className="w-3.5 h-3.5 text-amber-900" />
                          <span>{banner.annual_pass_text}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions & Meta Side Panel */}
                  <div className="w-full lg:w-72 border-t lg:border-t-0 lg:border-l border-slate-100 lg:pl-6 space-y-4">
                    <div>
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                        Assigned Scope
                      </span>
                      <span className="text-sm font-bold text-slate-800">
                        {banner.class_name ? `${banner.class_name} (${banner.board_name || 'Board'})` : 'Global (All Classes)'}
                      </span>
                    </div>

                    <div>
                      <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                        Display Status
                      </span>
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold mt-1 ${
                          banner.is_active
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {banner.is_active ? '● Live / Visible' : '○ Hidden'}
                      </span>
                    </div>

                    <div className="pt-2 flex items-center space-x-2">
                      <button
                        onClick={() => handleToggleActive(banner)}
                        className={`px-3 py-1.5 rounded-xl border text-xs font-semibold flex items-center space-x-1.5 transition-colors ${
                          banner.is_active
                            ? 'border-slate-300 text-slate-700 hover:bg-slate-50'
                            : 'border-emerald-300 text-emerald-700 hover:bg-emerald-50'
                        }`}
                        title={banner.is_active ? 'Hide Banner' : 'Show Banner'}
                      >
                        {banner.is_active ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        <span>{banner.is_active ? 'Hide' : 'Publish'}</span>
                      </button>

                      <button
                        onClick={() => {
                          setEditingBanner(banner);
                          setIsModalOpen(true);
                        }}
                        className="px-3 py-1.5 rounded-xl border border-indigo-200 text-indigo-700 hover:bg-indigo-50 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>

                      <button
                        onClick={() => handleDelete(banner)}
                        className="px-3 py-1.5 rounded-xl border border-rose-200 text-rose-700 hover:bg-rose-50 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Remove</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <BannerFormModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          loadBanners();
          setFeedback({
            type: 'success',
            message: editingBanner ? 'Banner updated successfully.' : 'New banner published successfully.',
          });
        }}
        bannerToEdit={editingBanner}
      />
    </div>
  );
};
