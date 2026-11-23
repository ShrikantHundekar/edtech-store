import React, { useState, useEffect, useRef } from 'react';
import { Search, X, BookOpen, FileText, Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { catalogService } from '../../services/catalogService';
import type { SearchResponse, SearchSubjectResult, SearchChapterResult } from '../../types/catalog';

interface SearchBarProps {
  onSelectSubject?: (subject: SearchSubjectResult) => void;
  onSelectChapter?: (chapter: SearchChapterResult) => void;
  placeholder?: string;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSelectSubject,
  onSelectChapter,
  placeholder = "Search topics, chapters, or subjects (e.g. 'Real Numbers', 'Light', 'Math')...",
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Debounced search trigger
  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      setIsLoading(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const data = await catalogService.searchCatalog(query.trim());
        setResults(data);
        setIsOpen(true);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setIsLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleClear = () => {
    setQuery('');
    setResults(null);
    setIsOpen(false);
  };

  const handleSubjectClick = (sub: SearchSubjectResult) => {
    setIsOpen(false);
    if (onSelectSubject) {
      onSelectSubject(sub);
    }
  };

  const handleChapterClick = (ch: SearchChapterResult) => {
    setIsOpen(false);
    if (onSelectChapter) {
      onSelectChapter(ch);
    }
  };

  return (
    <div ref={searchContainerRef} className="relative w-full max-w-2xl mx-auto">
      {/* Search Input Bar */}
      <div className="relative flex items-center">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
          ) : (
            <Search className="w-5 h-5" />
          )}
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (results && (results.subjects.length > 0 || results.chapters.length > 0)) {
              setIsOpen(true);
            }
          }}
          placeholder={placeholder}
          className="w-full pl-11 pr-11 py-3.5 bg-white rounded-2xl border border-slate-200 shadow-md shadow-slate-100 text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all"
        />
        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Live Dropdown Results */}
      {isOpen && results && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-xl border border-slate-200/90 overflow-hidden z-50 max-h-[460px] overflow-y-auto">
          {results.total_count === 0 ? (
            <div className="p-8 text-center text-slate-500">
              <Search className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm font-medium">No chapters or subjects matched "{query}"</p>
              <p className="text-xs text-slate-400 mt-1">Try searching for keywords like "Math", "Science", or "Chapter".</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {/* Subject Matches */}
              {results.subjects.length > 0 && (
                <div className="p-3">
                  <div className="px-3 py-1 text-xs font-bold uppercase tracking-wider text-slate-400">
                    Subjects ({results.subjects.length})
                  </div>
                  <div className="mt-1 space-y-1">
                    {results.subjects.map((sub) => (
                      <button
                        key={`sub-${sub.id}`}
                        type="button"
                        onClick={() => handleSubjectClick(sub)}
                        className="w-full text-left p-2.5 rounded-xl hover:bg-indigo-50/70 flex items-center justify-between group transition-colors cursor-pointer"
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                            <BookOpen className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <span className="block text-sm font-bold text-slate-900 group-hover:text-indigo-600 truncate">
                              {sub.name}
                            </span>
                            <span className="block text-xs text-slate-400 truncate">
                              {sub.breadcrumb_trail}
                            </span>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 shrink-0 ml-2" />
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Chapter Matches */}
              {results.chapters.length > 0 && (
                <div className="p-3">
                  <div className="px-3 py-1 text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Chapters & Topics ({results.chapters.length})</span>
                  </div>
                  <div className="mt-1 space-y-1">
                    {results.chapters.map((ch) => (
                      <button
                        key={`ch-${ch.id}`}
                        type="button"
                        onClick={() => handleChapterClick(ch)}
                        className="w-full text-left p-2.5 rounded-xl hover:bg-indigo-50/70 flex items-center justify-between group transition-colors cursor-pointer"
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0 group-hover:bg-indigo-100 group-hover:text-indigo-600">
                            <FileText className="w-4 h-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 truncate">
                                Ch {ch.chapter_number}: {ch.title}
                              </span>
                              {ch.is_free_sample && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 shrink-0">
                                  <Sparkles className="w-3 h-3 mr-0.5 text-amber-600" />
                                  Free Sample
                                </span>
                              )}
                            </div>
                            <span className="block text-xs text-slate-400 truncate">
                              {ch.breadcrumb_trail}
                            </span>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 shrink-0 ml-2" />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
