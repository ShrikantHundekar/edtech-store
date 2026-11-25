import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Search,
  Sparkles,
  Layers,
  Clock,
  ArrowRight,
  Filter,
  FileText,
} from 'lucide-react';
import { libraryService } from '../../services/libraryService';
import { useAuth } from '../../context/AuthContext';
import { PassCountdownCard } from '../../components/library/PassCountdownCard';
import { PDFReaderModal } from '../../components/library/PDFReaderModal';
import type { StudentLibraryResponse, LibraryChapter, LibraryMaterial } from '../../types/library';

export const LibraryPage: React.FC = () => {
  const { user } = useAuth();
  const [libraryData, setLibraryData] = useState<StudentLibraryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [selectedSubject, setSelectedSubject] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');

  // Active PDF Reader state
  const [activeMaterial, setActiveMaterial] = useState<{
    material: LibraryMaterial;
    chapter: LibraryChapter;
  } | null>(null);

  useEffect(() => {
    const fetchLibrary = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await libraryService.getStudentLibrary();
        setLibraryData(data);
      } catch (err: unknown) {
        const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error ||
          (err instanceof Error ? err.message : 'Failed to load library.');
        setError(msg);
      } finally {
        setLoading(false);
      }
    };

    fetchLibrary();
  }, []);

  const chapters = libraryData?.chapters || [];
  const passes = libraryData?.passes || [];
  const subjectsList = Array.from(new Set(chapters.map((c) => c.subject_name))).filter(Boolean);

  // Filtered Chapters
  const filteredChapters = chapters.filter((ch) => {
    if (selectedSubject !== 'ALL' && ch.subject_name !== selectedSubject) {
      return false;
    }
    if (sourceFilter !== 'ALL' && ch.unlocked_via !== sourceFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        ch.title.toLowerCase().includes(q) ||
        ch.subject_name.toLowerCase().includes(q) ||
        ch.class_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 flex flex-col items-center justify-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-slate-600 font-semibold text-sm">Loading your digital library...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <div className="p-4 bg-rose-50 rounded-2xl text-rose-600 inline-block mb-4">
          <BookOpen className="w-10 h-10" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Failed to load library</h2>
        <p className="text-slate-600 text-sm mt-2">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-6 px-5 py-2.5 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-10">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-3xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <span className="px-3 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 text-xs font-black uppercase tracking-wider rounded-full">
            Student Learning Hub
          </span>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight mt-3">
            Welcome back, {user?.full_name || user?.email.split('@')[0]} 👋
          </h1>
          <p className="text-slate-300 text-sm sm:text-base mt-2">
            Access your licensed curriculum notes, revisions, and active class passes below.
          </p>

          {/* Quick Metrics */}
          <div className="mt-6 flex flex-wrap gap-3">
            <div className="px-4 py-2 bg-white/10 backdrop-blur-md rounded-2xl border border-white/10 flex items-center space-x-2">
              <Clock className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold">
                {libraryData?.stats.active_passes_count || 0} Active Pass(es)
              </span>
            </div>
            <div className="px-4 py-2 bg-white/10 backdrop-blur-md rounded-2xl border border-white/10 flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-bold">
                {libraryData?.stats.total_chapters_unlocked || 0} Unlocked Chapter Note(s)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Pass Countdown Timers Section */}
      {passes.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900 flex items-center">
              <Clock className="w-5 h-5 mr-2 text-indigo-600" />
              Active Pass Countdown Timers ({passes.length})
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {passes.map((pass) => (
              <PassCountdownCard key={pass.id} pass={pass} />
            ))}
          </div>
        </div>
      )}

      {/* Main Content Explorer / Notes Section */}
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
          <div>
            <h2 className="text-xl font-black text-slate-900 flex items-center">
              <BookOpen className="w-5 h-5 mr-2 text-indigo-600" />
              Study Notes & Materials ({filteredChapters.length})
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Stream protected in-browser PDF notes anytime.
            </p>
          </div>

          {/* Search bar */}
          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search your notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-2xs"
            />
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center space-x-1 overflow-x-auto pb-1 scrollbar-none">
            <Filter className="w-3.5 h-3.5 text-slate-400 mr-1" />
            <button
              onClick={() => setSelectedSubject('ALL')}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                selectedSubject === 'ALL'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              All Subjects
            </button>
            {subjectsList.map((subj) => (
              <button
                key={subj}
                onClick={() => setSelectedSubject(subj)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                  selectedSubject === subj
                    ? 'bg-indigo-600 text-white'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {subj}
              </button>
            ))}
          </div>

          {/* Source Filter */}
          <div className="ml-auto flex items-center space-x-1.5 text-xs text-slate-500">
            <span className="font-medium">Source:</span>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-white border border-slate-200 rounded-xl px-2.5 py-1 text-xs font-semibold focus:outline-none focus:border-indigo-600"
            >
              <option value="ALL">All Sources</option>
              <option value="CHAPTER">Direct Purchases</option>
              <option value="SUBJECT">Subject Packs</option>
              <option value="CLASS_PASS">Class Passes</option>
              <option value="FREE_SAMPLE">Free Samples</option>
            </select>
          </div>
        </div>

        {/* Chapters Grid */}
        {filteredChapters.length === 0 ? (
          <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center">
            <Layers className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-slate-900">No notes found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              You haven&apos;t unlocked notes matching this criteria yet.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <Link
                to="/products"
                className="px-5 py-2.5 bg-indigo-600 text-white font-bold text-xs rounded-xl hover:bg-indigo-700 transition"
              >
                Browse Curriculum Store
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredChapters.map((ch) => (
              <div
                key={ch.id}
                className="bg-white rounded-3xl border border-slate-200/80 p-6 flex flex-col justify-between shadow-xs hover:shadow-md hover:border-slate-300 transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-[10px] font-black rounded-md uppercase tracking-wider">
                      {ch.subject_name}
                    </span>

                    {ch.unlocked_via === 'CLASS_PASS' && (
                      <span className="px-2 py-0.5 bg-purple-50 text-purple-700 text-[10px] font-bold rounded-md flex items-center">
                        Class Pass Unlock
                      </span>
                    )}
                    {ch.unlocked_via === 'SUBJECT' && (
                      <span className="px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-md flex items-center">
                        Subject Pack
                      </span>
                    )}
                    {ch.unlocked_via === 'CHAPTER' && (
                      <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[10px] font-bold rounded-md flex items-center">
                        Lifetime Access
                      </span>
                    )}
                    {ch.unlocked_via === 'FREE_SAMPLE' && (
                      <span className="px-2 py-0.5 bg-amber-50 text-amber-800 text-[10px] font-bold rounded-md flex items-center">
                        <Sparkles className="w-3 h-3 mr-0.5 text-amber-600" /> Free Sample
                      </span>
                    )}
                  </div>

                  <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
                    Ch {ch.chapter_number}: {ch.title}
                  </h3>

                  <p className="text-xs text-slate-400 mt-1">
                    {ch.class_name} • {ch.board_name}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 space-y-2">
                  {ch.materials && ch.materials.length > 0 ? (
                    ch.materials.map((mat) => (
                      <button
                        key={mat.id}
                        type="button"
                        onClick={() => setActiveMaterial({ material: mat, chapter: ch })}
                        className="w-full py-2.5 px-4 bg-slate-900 group-hover:bg-indigo-600 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center justify-between cursor-pointer"
                      >
                        <span className="flex items-center space-x-2 truncate">
                          <FileText className="w-3.5 h-3.5 shrink-0" />
                          <span className="truncate">{mat.title}</span>
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 shrink-0 ml-1.5" />
                      </button>
                    ))
                  ) : (
                    <button
                      type="button"
                      disabled
                      className="w-full py-2 px-3 bg-slate-100 text-slate-400 text-xs font-medium rounded-xl cursor-not-allowed"
                    >
                      Study Notes Processing
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* In-Browser PDF Reader Modal */}
      {activeMaterial && (
        <PDFReaderModal
          materialId={activeMaterial.material.id}
          title={activeMaterial.material.title}
          chapterTitle={`Ch ${activeMaterial.chapter.chapter_number}: ${activeMaterial.chapter.title}`}
          isFreeSample={activeMaterial.chapter.is_free_sample}
          onClose={() => setActiveMaterial(null)}
        />
      )}
    </div>
  );
};
