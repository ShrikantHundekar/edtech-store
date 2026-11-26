import React, { useState, useEffect } from 'react';
import { X, Loader2, AlertCircle, Sparkles } from 'lucide-react';
import type { PromoBanner, PromoBannerInput } from '../../types/banner';
import type { ClassLevel } from '../../types/catalog';
import { bannerService } from '../../services/bannerService';
import { adminCatalogService } from '../../services/adminCatalogService';

interface BannerFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  bannerToEdit?: PromoBanner | null;
}

export const BannerFormModal: React.FC<BannerFormModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  bannerToEdit,
}) => {
  const [title, setTitle] = useState('');
  const [badgeText, setBadgeText] = useState('⚡ Best Value: Full Class Pass');
  const [description, setDescription] = useState('');
  const [academicClassId, setAcademicClassId] = useState<number | ''>('');
  const [monthlyText, setMonthlyText] = useState('Monthly Pass (₹299 / 30 Days)');
  const [annualText, setAnnualText] = useState('Annual Pass (₹2,499 / 365 Days)');
  const [gradientTheme, setGradientTheme] = useState('from-indigo-900 via-indigo-800 to-purple-900');
  const [isActive, setIsActive] = useState(true);

  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    adminCatalogService.getClasses().then(setClasses).catch(() => {});

    if (bannerToEdit) {
      setTitle(bannerToEdit.title);
      setBadgeText(bannerToEdit.badge_text);
      setDescription(bannerToEdit.description);
      setAcademicClassId(bannerToEdit.academic_class || '');
      setMonthlyText(bannerToEdit.monthly_pass_text);
      setAnnualText(bannerToEdit.annual_pass_text);
      setGradientTheme(bannerToEdit.gradient_theme || 'from-indigo-900 via-indigo-800 to-purple-900');
      setIsActive(bannerToEdit.is_active);
    } else {
      setTitle('');
      setBadgeText('⚡ Best Value: Full Class Pass');
      setDescription('');
      setAcademicClassId('');
      setMonthlyText('Monthly Pass (₹299 / 30 Days)');
      setAnnualText('Annual Pass (₹2,499 / 365 Days)');
      setGradientTheme('from-indigo-900 via-indigo-800 to-purple-900');
      setIsActive(true);
    }
  }, [isOpen, bannerToEdit]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Banner title headline is required.');
      return;
    }
    if (!description.trim()) {
      setError('Banner description is required.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const payload: PromoBannerInput = {
        title: title.trim(),
        badge_text: badgeText.trim(),
        description: description.trim(),
        academic_class: academicClassId ? Number(academicClassId) : null,
        monthly_pass_text: monthlyText.trim(),
        annual_pass_text: annualText.trim(),
        gradient_theme: gradientTheme,
        is_active: isActive,
      };

      if (bannerToEdit) {
        await bannerService.updateBanner(bannerToEdit.id, payload);
      } else {
        await bannerService.createBanner(payload);
      }

      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: Record<string, unknown> } })?.response?.data;
      setError(msg ? JSON.stringify(msg) : 'Failed to save banner.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-2xl my-8 overflow-hidden transform transition-all">
        {/* Header */}
        <div className="px-6 py-5 bg-gradient-to-r from-purple-900 to-indigo-900 text-white flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/20">
              <Sparkles className="w-5 h-5 text-amber-300" />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {bannerToEdit ? 'Modify Promo Banner' : 'Create New Promotional Banner'}
              </h2>
              <p className="text-xs text-purple-200">
                Customize hero pitch, pass call-to-actions, and class target
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-purple-200 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-rose-700 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Target Class */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Target Academic Class
            </label>
            <select
              value={academicClassId}
              onChange={(e) => setAcademicClassId(e.target.value ? Number(e.target.value) : '')}
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="">Global / All Classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} {c.board_name ? `(${c.board_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Badge Pill & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Badge Label
              </label>
              <input
                type="text"
                value={badgeText}
                onChange={(e) => setBadgeText(e.target.value)}
                placeholder="e.g. ⚡ Best Value: Full Class Pass"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Headline Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Unlock All Class 10 Subjects & Chapters"
                required
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Body Description *
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="e.g. Get unlimited 24/7 access to all notes. Choose between flexible Monthly and Annual passes..."
              required
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
            />
          </div>

          {/* CTA Buttons Text */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Monthly Pass Button Text
              </label>
              <input
                type="text"
                value={monthlyText}
                onChange={(e) => setMonthlyText(e.target.value)}
                placeholder="Monthly Pass (₹299 / 30 Days)"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Annual Pass Button Text
              </label>
              <input
                type="text"
                value={annualText}
                onChange={(e) => setAnnualText(e.target.value)}
                placeholder="Annual Pass (₹2,499 / 365 Days)"
                className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              />
            </div>
          </div>

          {/* Color Gradient Theme */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
              Color Theme Gradient
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Royal Purple', class: 'from-indigo-900 via-indigo-800 to-purple-900' },
                { label: 'Ocean Blue', class: 'from-blue-900 via-indigo-800 to-cyan-900' },
                { label: 'Sunset Amber', class: 'from-amber-900 via-rose-900 to-purple-950' },
              ].map((theme) => (
                <button
                  type="button"
                  key={theme.class}
                  onClick={() => setGradientTheme(theme.class)}
                  className={`p-3 rounded-xl border text-center transition-all bg-gradient-to-r ${theme.class} text-white text-xs font-bold ${
                    gradientTheme === theme.class ? 'ring-2 ring-indigo-500 ring-offset-2' : 'opacity-80 hover:opacity-100'
                  }`}
                >
                  {theme.label}
                </button>
              ))}
            </div>
          </div>

          {/* Live Preview Card */}
          <div className="pt-2">
            <span className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Live Preview
            </span>
            <div className={`rounded-2xl bg-gradient-to-r ${gradientTheme} p-5 text-white shadow-md`}>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-400 text-amber-950 mb-2">
                {badgeText || 'Badge'}
              </span>
              <h4 className="text-base font-bold">{title || 'Banner Headline'}</h4>
              <p className="text-xs text-indigo-100 mt-1 line-clamp-2">{description || 'Banner body description...'}</p>
              <div className="mt-4 flex gap-2">
                <span className="px-3 py-1.5 rounded-lg bg-white text-indigo-950 font-bold text-xs">
                  {monthlyText}
                </span>
                <span className="px-3 py-1.5 rounded-lg bg-amber-400 text-amber-950 font-bold text-xs">
                  {annualText}
                </span>
              </div>
            </div>
          </div>

          {/* Active Switch */}
          <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div>
              <span className="font-semibold text-sm text-slate-900">Banner Visibility</span>
              <p className="text-xs text-slate-500">
                Turn off to temporarily hide this banner from students without deleting it
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
              className="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm shadow-md transition-all flex items-center space-x-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <span>{bannerToEdit ? 'Save Changes' : 'Create Banner'}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
