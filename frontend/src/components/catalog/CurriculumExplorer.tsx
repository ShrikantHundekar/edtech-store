import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { catalogService } from '../../services/catalogService';
import { Breadcrumbs } from './Breadcrumbs';
import type {
  Board,
  ClassLevel,
  Subject,
  Chapter,
  BreadcrumbItem,
} from '../../types/catalog';
import {
  BookOpen,
  FileText,
  Sparkles,
  ArrowRight,
  Calendar,
  Lock,
  Loader2,
} from 'lucide-react';

interface CurriculumExplorerProps {
  initialSubjectId?: number;
  initialChapterId?: number;
}

export const CurriculumExplorer: React.FC<CurriculumExplorerProps> = ({
  initialSubjectId,
  initialChapterId,
}) => {
  const navigate = useNavigate();

  // Hierarchy Data States
  const [boards, setBoards] = useState<Board[]>([]);
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  // Selection States
  const [selectedBoard, setSelectedBoard] = useState<Board | null>(null);
  const [selectedClass, setSelectedClass] = useState<ClassLevel | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null);

  // Loading States
  const [loadingBoards, setLoadingBoards] = useState(true);
  const [loadingClasses, setLoadingClasses] = useState(false);
  const [loadingSubjects, setLoadingSubjects] = useState(false);
  const [loadingChapters, setLoadingChapters] = useState(false);

  // Initial load: Fetch Boards
  useEffect(() => {
    const fetchBoards = async () => {
      setLoadingBoards(true);
      try {
        const boardList = await catalogService.getBoards();
        setBoards(boardList);
        // Automatically default to the first board (e.g. CBSE)
        if (boardList.length > 0) {
          setSelectedBoard(boardList[0]);
        }
      } catch (err) {
        console.error('Failed to load boards:', err);
      } finally {
        setLoadingBoards(false);
      }
    };
    fetchBoards();
  }, []);

  // When selectedBoard changes, fetch its Classes
  useEffect(() => {
    if (!selectedBoard) {
      setClasses([]);
      setSelectedClass(null);
      return;
    }

    const fetchClasses = async () => {
      setLoadingClasses(true);
      try {
        const classList = await catalogService.getBoardClasses(selectedBoard.id);
        setClasses(classList);
        // Default to Class 10 if present, or first class
        if (classList.length > 0) {
          const c10 = classList.find((c) => c.name.toLowerCase().includes('10')) || classList[0];
          setSelectedClass(c10);
        } else {
          setSelectedClass(null);
        }
      } catch (err) {
        console.error('Failed to load classes:', err);
      } finally {
        setLoadingClasses(false);
      }
    };
    fetchClasses();
  }, [selectedBoard]);

  // When selectedClass changes, fetch its Subjects
  useEffect(() => {
    if (!selectedClass) {
      setSubjects([]);
      setSelectedSubject(null);
      return;
    }

    const fetchSubjects = async () => {
      setLoadingSubjects(true);
      try {
        const subjectList = await catalogService.getClassSubjects(selectedClass.id);
        setSubjects(subjectList);
        // If an initialSubjectId was specified, pick that
        if (initialSubjectId) {
          const target = subjectList.find((s) => s.id === initialSubjectId);
          if (target) {
            setSelectedSubject(target);
            return;
          }
        }
        // Otherwise keep subject null to display the subject grid for this class
        setSelectedSubject(null);
      } catch (err) {
        console.error('Failed to load subjects:', err);
      } finally {
        setLoadingSubjects(false);
      }
    };
    fetchSubjects();
  }, [selectedClass, initialSubjectId]);

  // When selectedSubject changes, fetch its Chapters
  useEffect(() => {
    if (!selectedSubject) {
      setChapters([]);
      return;
    }

    const fetchChapters = async () => {
      setLoadingChapters(true);
      try {
        const chapterList = await catalogService.getSubjectChapters(selectedSubject.id);
        setChapters(chapterList);
      } catch (err) {
        console.error('Failed to load chapters:', err);
      } finally {
        setLoadingChapters(false);
      }
    };
    fetchChapters();
  }, [selectedSubject]);

  // Build Breadcrumbs trail
  const breadcrumbItems: BreadcrumbItem[] = [];
  if (selectedBoard) {
    breadcrumbItems.push({
      label: selectedBoard.name,
      onClick: () => {
        setSelectedSubject(null);
      },
    });
  }
  if (selectedClass) {
    breadcrumbItems.push({
      label: selectedClass.name,
      onClick: () => {
        setSelectedSubject(null);
      },
    });
  }
  if (selectedSubject) {
    breadcrumbItems.push({
      label: selectedSubject.name,
      active: true,
    });
  }

  return (
    <div className="space-y-6">
      {/* Visual Breadcrumb Navigation Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Breadcrumbs
          items={breadcrumbItems}
          onHomeClick={() => {
            setSelectedSubject(null);
          }}
        />

        {/* Board & Class Selectors */}
        <div className="flex items-center space-x-2 shrink-0">
          {(loadingBoards || loadingClasses) && (
            <Loader2 className="w-4 h-4 animate-spin text-indigo-600 mr-1" />
          )}
          {boards.length > 1 && (
            <select
              value={selectedBoard?.id || ''}
              onChange={(e) => {
                const b = boards.find((x) => x.id === Number(e.target.value));
                if (b) setSelectedBoard(b);
              }}
              className="text-xs font-semibold bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
            >
              {boards.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          )}

          {/* Class Tabs */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-xl">
            {classes.map((cls) => {
              const active = selectedClass?.id === cls.id;
              return (
                <button
                  key={cls.id}
                  type="button"
                  onClick={() => {
                    setSelectedClass(cls);
                    setSelectedSubject(null);
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    active
                      ? 'bg-white text-indigo-700 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {cls.name}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Class Pass Hero Banner */}
      {selectedClass && !selectedSubject && (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-900 via-indigo-800 to-purple-900 p-8 text-white shadow-xl">
          <div className="relative z-10 max-w-2xl">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-400 text-amber-950 mb-3 shadow-xs">
              ⚡ Best Value: Full Class Pass
            </span>
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
              Unlock All {selectedClass.name} Subjects & Chapters
            </h2>
            <p className="mt-2 text-sm text-indigo-100 leading-relaxed">
              Get unlimited 24/7 access to all Maths, Science, and Social Science notes for{' '}
              {selectedClass.name}. Choose between flexible Monthly and Annual passes with instant access.
            </p>

            <div className="mt-6 flex flex-wrap gap-4">
              <button
                type="button"
                onClick={() => navigate(`/products?class_id=${selectedClass.id}&type=MONTHLY_PASS`)}
                className="px-5 py-2.5 rounded-xl bg-white text-indigo-950 font-bold text-sm shadow-md hover:bg-indigo-50 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Calendar className="w-4 h-4 text-indigo-600" />
                <span>Monthly Pass (₹299 / 30 Days)</span>
              </button>
              <button
                type="button"
                onClick={() => navigate(`/products?class_id=${selectedClass.id}&type=ANNUAL_PASS`)}
                className="px-5 py-2.5 rounded-xl bg-amber-400 text-amber-950 font-bold text-sm shadow-md hover:bg-amber-300 transition-all flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4 text-amber-900" />
                <span>Annual Pass (₹2,499 / 365 Days)</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Level 1: SUBJECTS GRID (When no subject is selected) */}
      {!selectedSubject && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-black text-slate-900 tracking-tight">
                {selectedClass?.name || 'Class'} Subjects
              </h3>
              <p className="text-xs text-slate-500">
                Select a subject to view chapters, download free preview notes, or buy subject packs.
              </p>
            </div>
          </div>

          {loadingSubjects ? (
            <div className="py-16 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-500">Loading curriculum subjects...</p>
            </div>
          ) : subjects.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
              <BookOpen className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-600">No subjects found for this class.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {subjects.map((sub) => (
                <div
                  key={sub.id}
                  className="bg-white rounded-2xl border border-slate-200/90 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all p-6 flex flex-col justify-between group"
                >
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-12 h-12 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-xl shadow-xs group-hover:scale-105 transition-transform">
                        📚
                      </div>
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                        {sub.chapters_count ?? '5'} Chapters
                      </span>
                    </div>

                    <h4 className="text-lg font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
                      {sub.name}
                    </h4>
                    <p className="text-xs text-slate-500 mt-1">
                      Complete CBSE syllabus with chapter notes & free preview chapter.
                    </p>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => setSelectedSubject(sub)}
                      className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 cursor-pointer"
                    >
                      <span>Explore Chapters</span>
                      <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                    </button>

                    <button
                      type="button"
                      onClick={() => navigate(`/products?subject_id=${sub.id}&type=SUBJECT_PACK`)}
                      className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 font-bold text-xs hover:bg-indigo-100 transition-colors cursor-pointer"
                    >
                      Subject Pack (₹499)
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Level 2: CHAPTERS VIEW (When a subject is selected) */}
      {selectedSubject && (
        <div className="space-y-6">
          {/* Subject Header & Pack Upsell Banner */}
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2.5 py-0.5 rounded-md text-xs font-bold bg-indigo-100 text-indigo-800">
                  {selectedClass?.name}
                </span>
                <span className="text-slate-300">•</span>
                <span className="text-xs font-semibold text-slate-500">{selectedBoard?.name}</span>
              </div>
              <h3 className="text-2xl font-black text-slate-900 tracking-tight">
                {selectedSubject.name} Chapters
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Download or read individual chapter notes (₹49 each) or save with the Complete Subject Pack.
              </p>
            </div>

            {/* Subject Pack Upgrade Callout */}
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-2xl p-4 flex items-center justify-between gap-4 shrink-0">
              <div>
                <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block">
                  Complete Subject Pack
                </span>
                <span className="text-base font-extrabold text-slate-900">
                  All Chapters for ₹499
                </span>
                <span className="text-[11px] text-slate-500 block">
                  Upgrade credits applied automatically
                </span>
              </div>
              <button
                type="button"
                onClick={() => navigate(`/products?subject_id=${selectedSubject.id}&type=SUBJECT_PACK`)}
                className="px-4 py-2 rounded-xl bg-indigo-600 text-white font-bold text-xs shadow-sm hover:bg-indigo-700 transition-colors cursor-pointer shrink-0"
              >
                View Subject Pack
              </button>
            </div>
          </div>

          {/* Chapters List */}
          {loadingChapters ? (
            <div className="py-16 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-500">Loading chapters...</p>
            </div>
          ) : chapters.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-2xl border border-slate-200">
              <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-600">No chapters found for this subject.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {chapters.map((ch) => {
                const isTarget = ch.id === initialChapterId;
                return (
                  <div
                    key={ch.id}
                    className={`bg-white rounded-2xl border transition-all p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs ${
                      isTarget ? 'ring-2 ring-indigo-500 border-indigo-500 bg-indigo-50/10' : ''
                    } ${
                      ch.is_free_sample
                        ? 'border-amber-200/80 bg-amber-50/20 hover:border-amber-300'
                        : 'border-slate-200/90 hover:border-indigo-200'
                    }`}
                  >
                  <div className="flex items-start space-x-4">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 mt-0.5 ${
                        ch.is_free_sample
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-indigo-50 text-indigo-700 border border-indigo-100'
                      }`}
                    >
                      {ch.chapter_number}
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="text-base font-bold text-slate-900">{ch.title}</h4>

                        {/* Acceptance Criteria: Free sample badge displayed on preview chapters */}
                        {ch.is_free_sample && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300 shadow-2xs">
                            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-600" />
                            Free Sample Preview
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-500 mt-1 flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          Full study notes & revision summary included
                        </span>
                        <span>•</span>
                        <span>Lifetime Access</span>
                      </p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-2.5 sm:shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                    {ch.is_free_sample ? (
                      <button
                        type="button"
                        onClick={() => navigate(`/library?chapter_id=${ch.id}&sample=true`)}
                        className="w-full sm:w-auto px-4 py-2 rounded-xl bg-amber-400 text-amber-950 font-bold text-xs shadow-xs hover:bg-amber-300 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-amber-800" />
                        <span>Read Free Sample</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => navigate(`/products?chapter_id=${ch.id}&type=CHAPTER_NOTES`)}
                        className="w-full sm:w-auto px-4 py-2 rounded-xl bg-indigo-600 text-white font-bold text-xs shadow-xs hover:bg-indigo-700 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>Get Chapter Note (₹49)</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
