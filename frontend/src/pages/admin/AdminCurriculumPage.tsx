import React, { useState, useEffect, useTransition } from 'react';
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  X,
  Loader2,
} from 'lucide-react';
import {
  adminCatalogService,
  type BoardInput,
  type ClassInput,
  type SubjectInput,
  type ChapterInput,
} from '../../services/adminCatalogService';
import type { Board, ClassLevel, Subject, Chapter } from '../../types/catalog';

type TabType = 'BOARDS' | 'CLASSES' | 'SUBJECTS' | 'CHAPTERS';

export const AdminCurriculumPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('BOARDS');
  const [, startTransition] = useTransition();

  // Data states
  const [boards, setBoards] = useState<Board[]>([]);
  const [classes, setClasses] = useState<ClassLevel[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Modal States
  const [modalType, setModalType] = useState<'BOARD' | 'CLASS' | 'SUBJECT' | 'CHAPTER' | null>(null);
  const [editingItem, setEditingItem] = useState<Board | ClassLevel | Subject | Chapter | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  // Form Fields
  const [boardForm, setBoardForm] = useState<BoardInput>({ name: '', slug: '', description: '' });
  const [classForm, setClassForm] = useState<ClassInput>({ board: 0, name: '', slug: '' });
  const [subjectForm, setSubjectForm] = useState<SubjectInput>({ academic_class: 0, name: '', slug: '' });
  const [chapterForm, setChapterForm] = useState<ChapterInput>({
    subject: 0,
    chapter_number: 1,
    title: '',
    slug: '',
    is_free_sample: false,
  });

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [boardsData, classesData, subjectsData, chaptersData] = await Promise.all([
        adminCatalogService.getBoards(),
        adminCatalogService.getClasses(),
        adminCatalogService.getSubjects(),
        adminCatalogService.getChapters(),
      ]);
      setBoards(boardsData);
      setClasses(classesData);
      setSubjects(subjectsData);
      setChapters(chaptersData);
    } catch {
      setFeedback({ type: 'error', message: 'Failed to load curriculum data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => setFeedback(null), 4000);
  };

  // Open Modal Helpers
  const openCreateModal = (type: TabType) => {
    setFormErrors({});
    if (type === 'BOARDS') {
      setBoardForm({ name: '', slug: '', description: '' });
      setEditingItem(null);
      setModalType('BOARD');
    } else if (type === 'CLASSES') {
      setClassForm({ board: boards[0]?.id || 0, name: '', slug: '' });
      setEditingItem(null);
      setModalType('CLASS');
    } else if (type === 'SUBJECTS') {
      setSubjectForm({ academic_class: classes[0]?.id || 0, name: '', slug: '' });
      setEditingItem(null);
      setModalType('SUBJECT');
    } else if (type === 'CHAPTERS') {
      setChapterForm({
        subject: subjects[0]?.id || 0,
        chapter_number: (chapters.length > 0 ? Math.max(...chapters.map((c) => c.chapter_number)) + 1 : 1),
        title: '',
        slug: '',
        is_free_sample: false,
      });
      setEditingItem(null);
      setModalType('CHAPTER');
    }
  };

  const openEditModal = (item: Board | ClassLevel | Subject | Chapter, type: TabType) => {
    setFormErrors({});
    setEditingItem(item);
    if (type === 'BOARDS') {
      const b = item as Board;
      setBoardForm({ name: b.name, slug: b.slug, description: b.description || '' });
      setModalType('BOARD');
    } else if (type === 'CLASSES') {
      const c = item as ClassLevel;
      setClassForm({ board: c.board, name: c.name, slug: c.slug });
      setModalType('CLASS');
    } else if (type === 'SUBJECTS') {
      const s = item as Subject;
      setSubjectForm({ academic_class: s.academic_class, name: s.name, slug: s.slug });
      setModalType('SUBJECT');
    } else if (type === 'CHAPTERS') {
      const ch = item as Chapter;
      setChapterForm({
        subject: ch.subject,
        chapter_number: ch.chapter_number,
        title: ch.title,
        slug: ch.slug,
        is_free_sample: ch.is_free_sample,
      });
      setModalType('CHAPTER');
    }
  };

  // Submit Handlers
  const handleBoardSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!boardForm.name.trim()) {
      setFormErrors({ name: 'Board name is required.' });
      return;
    }
    setIsSubmitting(true);
    try {
      if (editingItem) {
        const updated = await adminCatalogService.updateBoard(editingItem.id, boardForm);
        setBoards((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
        showFeedback('success', `Board "${updated.name}" updated successfully.`);
      } else {
        const created = await adminCatalogService.createBoard(boardForm);
        setBoards((prev) => [created, ...prev]);
        showFeedback('success', `Board "${created.name}" created successfully.`);
      }
      setModalType(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string; name?: string[] } } }).response?.data?.error || 'Failed to save board.';
      setFormErrors({ form: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClassSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (!classForm.name.trim()) errors.name = 'Class name is required.';
    if (!classForm.board) errors.board = 'Parent board is required.';
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setIsSubmitting(true);
    try {
      if (editingItem) {
        const updated = await adminCatalogService.updateClass(editingItem.id, classForm);
        setClasses((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
        showFeedback('success', `Class "${updated.name}" updated successfully.`);
      } else {
        const created = await adminCatalogService.createClass(classForm);
        setClasses((prev) => [created, ...prev]);
        showFeedback('success', `Class "${created.name}" created successfully.`);
      }
      setModalType(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error || 'Failed to save class.';
      setFormErrors({ form: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (!subjectForm.name.trim()) errors.name = 'Subject name is required.';
    if (!subjectForm.academic_class) errors.academic_class = 'Class level is required.';
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setIsSubmitting(true);
    try {
      if (editingItem) {
        const updated = await adminCatalogService.updateSubject(editingItem.id, subjectForm);
        setSubjects((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
        showFeedback('success', `Subject "${updated.name}" updated successfully.`);
      } else {
        const created = await adminCatalogService.createSubject(subjectForm);
        setSubjects((prev) => [created, ...prev]);
        showFeedback('success', `Subject "${created.name}" created successfully.`);
      }
      setModalType(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error || 'Failed to save subject.';
      setFormErrors({ form: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChapterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors: Record<string, string> = {};
    if (!chapterForm.title.trim()) errors.title = 'Chapter title is required.';
    if (!chapterForm.subject) errors.subject = 'Parent subject is required.';
    if (!chapterForm.chapter_number) errors.chapter_number = 'Chapter number is required.';
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }
    setIsSubmitting(true);
    try {
      if (editingItem) {
        const updated = await adminCatalogService.updateChapter(editingItem.id, chapterForm);
        setChapters((prev) => prev.map((ch) => (ch.id === updated.id ? updated : ch)));
        showFeedback('success', `Chapter "${updated.title}" updated successfully.`);
      } else {
        const created = await adminCatalogService.createChapter(chapterForm);
        setChapters((prev) => [created, ...prev]);
        showFeedback('success', `Chapter "${created.title}" created successfully.`);
      }
      setModalType(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } }).response?.data?.error || 'Failed to save chapter.';
      setFormErrors({ form: msg });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete Handlers
  const handleDelete = async (id: number, type: TabType, name: string) => {
    if (!window.confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
      return;
    }
    try {
      if (type === 'BOARDS') {
        await adminCatalogService.deleteBoard(id);
        setBoards((prev) => prev.filter((b) => b.id !== id));
      } else if (type === 'CLASSES') {
        await adminCatalogService.deleteClass(id);
        setClasses((prev) => prev.filter((c) => c.id !== id));
      } else if (type === 'SUBJECTS') {
        await adminCatalogService.deleteSubject(id);
        setSubjects((prev) => prev.filter((s) => s.id !== id));
      } else if (type === 'CHAPTERS') {
        await adminCatalogService.deleteChapter(id);
        setChapters((prev) => prev.filter((ch) => ch.id !== id));
      }
      showFeedback('success', `Successfully deleted ${name}.`);
    } catch {
      showFeedback('error', `Failed to delete ${name}. It may have dependent child records.`);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-slate-200">
        <div>
          <span className="text-xs font-black uppercase tracking-widest text-purple-600 bg-purple-50 px-3 py-1 rounded-full">
            Admin Management Console
          </span>
          <h1 className="text-3xl font-extrabold text-slate-900 mt-2 tracking-tight">
            Curriculum Structure Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Create, edit, and organize Educational Boards, Academic Classes, Subjects, and Chapters.
          </p>
        </div>

        <button
          onClick={() => openCreateModal(activeTab)}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl transition flex items-center space-x-1.5 shadow-xs cursor-pointer shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>Add New {activeTab.slice(0, -1)}</span>
        </button>
      </div>

      {/* Global Toast Feedback */}
      {feedback && (
        <div
          className={`mt-4 p-4 rounded-2xl flex items-center justify-between border ${
            feedback.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center space-x-2 text-sm font-semibold">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-rose-600" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button onClick={() => setFeedback(null)} className="p-1 hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Hierarchy Level Navigation Tabs */}
      <div className="mt-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-2 bg-slate-100 p-1.5 rounded-2xl w-fit">
          {(['BOARDS', 'CLASSES', 'SUBJECTS', 'CHAPTERS'] as TabType[]).map((tab) => (
            <button
              key={tab}
              onClick={() => {
                startTransition(() => {
                  setActiveTab(tab);
                  setSearchQuery('');
                });
              }}
              className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-wider transition cursor-pointer ${
                activeTab === tab
                  ? 'bg-white text-indigo-700 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab} (
              {tab === 'BOARDS'
                ? boards.length
                : tab === 'CLASSES'
                ? classes.length
                : tab === 'SUBJECTS'
                ? subjects.length
                : chapters.length}
              )
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder={`Search ${activeTab.toLowerCase()}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 shadow-2xs"
          />
        </div>
      </div>

      {/* Data Table */}
      <div className="mt-6 bg-white rounded-3xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-600 mb-2" />
            <p className="text-xs text-slate-400 font-medium">Loading curriculum structure...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            {/* BOARDS TAB */}
            {activeTab === 'BOARDS' && (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-6">Board Name</th>
                    <th className="py-3.5 px-6">Slug</th>
                    <th className="py-3.5 px-6">Description</th>
                    <th className="py-3.5 px-6 text-center">Classes</th>
                    <th className="py-3.5 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {boards
                    .filter((b) => !searchQuery.trim() || b.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .map((b) => (
                      <tr key={b.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-4 px-6 font-bold text-slate-900">{b.name}</td>
                        <td className="py-4 px-6 font-mono text-slate-500">{b.slug}</td>
                        <td className="py-4 px-6 text-slate-600 truncate max-w-xs">
                          {b.description || '—'}
                        </td>
                        <td className="py-4 px-6 text-center font-bold text-indigo-600">
                          {b.classes_count ?? 0}
                        </td>
                        <td className="py-4 px-6 text-right space-x-2">
                          <button
                            onClick={() => openEditModal(b, 'BOARDS')}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                            title="Edit Board"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(b.id, 'BOARDS', b.name)}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                            title="Delete Board"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* CLASSES TAB */}
            {activeTab === 'CLASSES' && (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-6">Class Name</th>
                    <th className="py-3.5 px-6">Board</th>
                    <th className="py-3.5 px-6">Slug</th>
                    <th className="py-3.5 px-6 text-center">Subjects</th>
                    <th className="py-3.5 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {classes
                    .filter((c) => !searchQuery.trim() || c.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-4 px-6 font-bold text-slate-900">{c.name}</td>
                        <td className="py-4 px-6">
                          <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 font-bold rounded-md">
                            {c.board_name || `Board #${c.board}`}
                          </span>
                        </td>
                        <td className="py-4 px-6 font-mono text-slate-500">{c.slug}</td>
                        <td className="py-4 px-6 text-center font-bold text-indigo-600">
                          {c.subjects_count ?? 0}
                        </td>
                        <td className="py-4 px-6 text-right space-x-2">
                          <button
                            onClick={() => openEditModal(c, 'CLASSES')}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                            title="Edit Class"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(c.id, 'CLASSES', c.name)}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                            title="Delete Class"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* SUBJECTS TAB */}
            {activeTab === 'SUBJECTS' && (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-6">Subject Name</th>
                    <th className="py-3.5 px-6">Academic Class</th>
                    <th className="py-3.5 px-6">Board</th>
                    <th className="py-3.5 px-6 text-center">Chapters</th>
                    <th className="py-3.5 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {subjects
                    .filter((s) => !searchQuery.trim() || s.name.toLowerCase().includes(searchQuery.toLowerCase()))
                    .map((s) => (
                      <tr key={s.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-4 px-6 font-bold text-slate-900">{s.name}</td>
                        <td className="py-4 px-6 font-medium text-slate-700">{s.class_name}</td>
                        <td className="py-4 px-6 text-slate-500">{s.board_name || 'CBSE'}</td>
                        <td className="py-4 px-6 text-center font-bold text-indigo-600">
                          {s.chapters_count ?? 0}
                        </td>
                        <td className="py-4 px-6 text-right space-x-2">
                          <button
                            onClick={() => openEditModal(s, 'SUBJECTS')}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                            title="Edit Subject"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(s.id, 'SUBJECTS', s.name)}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                            title="Delete Subject"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* CHAPTERS TAB */}
            {activeTab === 'CHAPTERS' && (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-700 font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-6">#</th>
                    <th className="py-3.5 px-6">Chapter Title</th>
                    <th className="py-3.5 px-6">Subject</th>
                    <th className="py-3.5 px-6 text-center">Free Sample</th>
                    <th className="py-3.5 px-6 text-center">Materials</th>
                    <th className="py-3.5 px-6 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {chapters
                    .filter((ch) => !searchQuery.trim() || ch.title.toLowerCase().includes(searchQuery.toLowerCase()))
                    .map((ch) => (
                      <tr key={ch.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-4 px-6 font-black text-slate-500">Ch {ch.chapter_number}</td>
                        <td className="py-4 px-6 font-bold text-slate-900">{ch.title}</td>
                        <td className="py-4 px-6">
                          <span className="px-2 py-0.5 bg-slate-100 font-semibold rounded-md text-slate-700">
                            {ch.subject_name}
                          </span>
                        </td>
                        <td className="py-4 px-6 text-center">
                          {ch.is_free_sample ? (
                            <span className="inline-flex items-center px-2 py-0.5 bg-amber-100 text-amber-800 font-black rounded-md text-[10px]">
                              <Sparkles className="w-3 h-3 mr-0.5" /> FREE SAMPLE
                            </span>
                          ) : (
                            <span className="text-slate-400 font-medium">Standard</span>
                          )}
                        </td>
                        <td className="py-4 px-6 text-center font-bold text-slate-700">
                          {ch.materials_count ?? 0} PDF(s)
                        </td>
                        <td className="py-4 px-6 text-right space-x-2">
                          <button
                            onClick={() => openEditModal(ch, 'CHAPTERS')}
                            className="p-1.5 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                            title="Edit Chapter"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(ch.id, 'CHAPTERS', ch.title)}
                            className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
                            title="Delete Chapter"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* CREATE / EDIT MODAL */}
      {modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 backdrop-blur-xs p-4 animate-in fade-in-50">
          <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-8 border border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">
                {editingItem ? 'Edit' : 'Create New'} {modalType.charAt(0) + modalType.slice(1).toLowerCase()}
              </h3>
              <button
                onClick={() => setModalType(null)}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formErrors.form && (
              <div className="mt-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-xl text-xs font-semibold">
                {formErrors.form}
              </div>
            )}

            {/* BOARD FORM */}
            {modalType === 'BOARD' && (
              <form onSubmit={handleBoardSubmit} className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Board Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Central Board of Secondary Education (CBSE)"
                    value={boardForm.name}
                    onChange={(e) => setBoardForm({ ...boardForm, name: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                  {formErrors.name && <p className="text-xs text-rose-600 mt-1">{formErrors.name}</p>}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Slug (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. cbse (auto-generated if empty)"
                    value={boardForm.slug || ''}
                    onChange={(e) => setBoardForm({ ...boardForm, slug: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Description (Optional)</label>
                  <textarea
                    rows={3}
                    placeholder="Board details..."
                    value={boardForm.description || ''}
                    onChange={(e) => setBoardForm({ ...boardForm, description: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                </div>
                <div className="pt-4 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setModalType(null)}
                    className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                  >
                    {isSubmitting ? 'Saving...' : editingItem ? 'Save Changes' : 'Create Board'}
                  </button>
                </div>
              </form>
            )}

            {/* CLASS FORM */}
            {modalType === 'CLASS' && (
              <form onSubmit={handleClassSubmit} className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Educational Board *</label>
                  <select
                    value={classForm.board}
                    onChange={(e) => setClassForm({ ...classForm, board: Number(e.target.value) })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  >
                    <option value={0}>Select a board...</option>
                    {boards.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.name}
                      </option>
                    ))}
                  </select>
                  {formErrors.board && <p className="text-xs text-rose-600 mt-1">{formErrors.board}</p>}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Class Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Class 10"
                    value={classForm.name}
                    onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                  {formErrors.name && <p className="text-xs text-rose-600 mt-1">{formErrors.name}</p>}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Slug (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. class-10"
                    value={classForm.slug || ''}
                    onChange={(e) => setClassForm({ ...classForm, slug: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                </div>
                <div className="pt-4 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setModalType(null)}
                    className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                  >
                    {isSubmitting ? 'Saving...' : editingItem ? 'Save Changes' : 'Create Class'}
                  </button>
                </div>
              </form>
            )}

            {/* SUBJECT FORM */}
            {modalType === 'SUBJECT' && (
              <form onSubmit={handleSubjectSubmit} className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Academic Class *</label>
                  <select
                    value={subjectForm.academic_class}
                    onChange={(e) =>
                      setSubjectForm({ ...subjectForm, academic_class: Number(e.target.value) })
                    }
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  >
                    <option value={0}>Select a class...</option>
                    {classes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.board_name || 'Board'})
                      </option>
                    ))}
                  </select>
                  {formErrors.academic_class && (
                    <p className="text-xs text-rose-600 mt-1">{formErrors.academic_class}</p>
                  )}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Subject Name *</label>
                  <input
                    type="text"
                    placeholder="e.g. Science"
                    value={subjectForm.name}
                    onChange={(e) => setSubjectForm({ ...subjectForm, name: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                  {formErrors.name && <p className="text-xs text-rose-600 mt-1">{formErrors.name}</p>}
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Slug (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. science"
                    value={subjectForm.slug || ''}
                    onChange={(e) => setSubjectForm({ ...subjectForm, slug: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  />
                </div>
                <div className="pt-4 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setModalType(null)}
                    className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                  >
                    {isSubmitting ? 'Saving...' : editingItem ? 'Save Changes' : 'Create Subject'}
                  </button>
                </div>
              </form>
            )}

            {/* CHAPTER FORM */}
            {modalType === 'CHAPTER' && (
              <form onSubmit={handleChapterSubmit} className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Parent Subject *</label>
                  <select
                    value={chapterForm.subject}
                    onChange={(e) =>
                      setChapterForm({ ...chapterForm, subject: Number(e.target.value) })
                    }
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                  >
                    <option value={0}>Select a subject...</option>
                    {subjects.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.class_name})
                      </option>
                    ))}
                  </select>
                  {formErrors.subject && (
                    <p className="text-xs text-rose-600 mt-1">{formErrors.subject}</p>
                  )}
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Chapter # *</label>
                    <input
                      type="number"
                      min={1}
                      value={chapterForm.chapter_number}
                      onChange={(e) =>
                        setChapterForm({ ...chapterForm, chapter_number: Number(e.target.value) })
                      }
                      className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs font-bold text-slate-700 mb-1">Chapter Title *</label>
                    <input
                      type="text"
                      placeholder="e.g. Chemical Reactions and Equations"
                      value={chapterForm.title}
                      onChange={(e) => setChapterForm({ ...chapterForm, title: e.target.value })}
                      className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:border-indigo-600"
                    />
                  </div>
                </div>
                {formErrors.title && <p className="text-xs text-rose-600 mt-1">{formErrors.title}</p>}

                <div className="p-3 bg-amber-50 border border-amber-200 rounded-2xl flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="is_free_sample"
                    checked={chapterForm.is_free_sample}
                    onChange={(e) =>
                      setChapterForm({ ...chapterForm, is_free_sample: e.target.checked })
                    }
                    className="w-4 h-4 text-indigo-600 rounded-md focus:ring-indigo-500"
                  />
                  <label htmlFor="is_free_sample" className="text-xs font-bold text-amber-900 cursor-pointer">
                    Flag as Free Sample Chapter (Available publicly without purchase)
                  </label>
                </div>

                <div className="pt-4 flex justify-end space-x-2">
                  <button
                    type="button"
                    onClick={() => setModalType(null)}
                    className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs transition"
                  >
                    {isSubmitting ? 'Saving...' : editingItem ? 'Save Changes' : 'Create Chapter'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
