import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import type { BreadcrumbItem } from '../../types/catalog';

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  onHomeClick?: () => void;
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items, onHomeClick }) => {
  return (
    <nav className="flex items-center space-x-1.5 text-sm text-slate-500 overflow-x-auto py-2 scrollbar-none" aria-label="Breadcrumb">
      <button
        type="button"
        onClick={onHomeClick}
        className="flex items-center space-x-1 text-slate-600 hover:text-indigo-600 font-medium transition-colors cursor-pointer shrink-0"
      >
        <Home className="w-4 h-4" />
        <span>Curriculum</span>
      </button>

      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <React.Fragment key={`${item.label}-${index}`}>
            <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
            {isLast || !item.onClick ? (
              <span className="font-bold text-slate-900 truncate max-w-[200px] shrink-0">
                {item.label}
              </span>
            ) : (
              <button
                type="button"
                onClick={item.onClick}
                className="text-slate-600 hover:text-indigo-600 font-medium transition-colors cursor-pointer truncate max-w-[180px] shrink-0"
              >
                {item.label}
              </button>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
};
