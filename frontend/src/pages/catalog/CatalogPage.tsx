import React, { useState } from 'react';
import { SearchBar } from '../../components/catalog/SearchBar';
import { CurriculumExplorer } from '../../components/catalog/CurriculumExplorer';
import type { SearchSubjectResult, SearchChapterResult } from '../../types/catalog';
import { Sparkles } from 'lucide-react';

export const CatalogPage: React.FC = () => {
  const [selectedSubjectId, setSelectedSubjectId] = useState<number | undefined>(undefined);
  const [selectedChapterId, setSelectedChapterId] = useState<number | undefined>(undefined);

  const handleSelectSubject = (subject: SearchSubjectResult) => {
    setSelectedSubjectId(subject.id);
  };

  const handleSelectChapter = (chapter: SearchChapterResult) => {
    if (chapter.breadcrumbs?.subject?.id) {
      setSelectedSubjectId(chapter.breadcrumbs.subject.id);
    }
    setSelectedChapterId(chapter.id);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-10">
      {/* Hero Header & Live Search */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold tracking-wide">
          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
          <span>Curated CBSE Study Materials & Passes</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
          Find Any Topic, Chapter, or Full Subject Pack
        </h1>

        <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto">
          Explore complete CBSE curriculum notes. Preview free sample chapters, upgrade to full subject packs with automatic credits, or unlock everything with a Class Pass.
        </p>

        {/* Live Search Component */}
        <div className="pt-2">
          <SearchBar
            onSelectSubject={handleSelectSubject}
            onSelectChapter={handleSelectChapter}
          />
        </div>
      </div>

      {/* Feature Badges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-2 border-y border-slate-200/80">
        <div className="flex items-center space-x-3 p-3">
          <div className="w-9 h-9 rounded-xl bg-amber-100 text-amber-800 flex items-center justify-center text-base shrink-0 font-bold">
            ✨
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Free Preview</h4>
            <p className="text-[11px] text-slate-500">1 free chapter per subject</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-800 flex items-center justify-center text-base shrink-0 font-bold">
            💳
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Upgrade Credits</h4>
            <p className="text-[11px] text-slate-500">Subject pack discounts</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center text-base shrink-0 font-bold">
            ⚡
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">Class Passes</h4>
            <p className="text-[11px] text-slate-500">30-day & 365-day access</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3">
          <div className="w-9 h-9 rounded-xl bg-purple-100 text-purple-800 flex items-center justify-center text-base shrink-0 font-bold">
            🛡️
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-900">18% GST Compliant</h4>
            <p className="text-[11px] text-slate-500">Official tax invoices</p>
          </div>
        </div>
      </div>

      {/* Main Hierarchical Curriculum Explorer */}
      <CurriculumExplorer
        key={`${selectedSubjectId}-${selectedChapterId}`}
        initialSubjectId={selectedSubjectId}
        initialChapterId={selectedChapterId}
      />
    </div>
  );
};
