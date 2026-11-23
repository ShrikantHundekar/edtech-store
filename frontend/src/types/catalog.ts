export interface Board {
  id: number;
  name: string;
  slug: string;
  description?: string;
  classes_count?: number;
}

export interface ClassLevel {
  id: number;
  board: number;
  board_name?: string;
  name: string;
  slug: string;
  subjects_count?: number;
}

export interface Subject {
  id: number;
  academic_class: number;
  class_name?: string;
  board_name?: string;
  name: string;
  slug: string;
  thumbnail_url?: string;
  chapters_count?: number;
}

export interface Chapter {
  id: number;
  subject: number;
  subject_name?: string;
  chapter_number: number;
  title: string;
  slug: string;
  is_free_sample: boolean;
  materials_count?: number;
  product_id?: number;
  price_paise?: number;
}

export interface SearchBreadcrumb {
  id: number;
  name: string;
  slug: string;
}

export interface SearchSubjectResult {
  id: number;
  name: string;
  slug: string;
  thumbnail_url?: string;
  breadcrumbs: {
    board: SearchBreadcrumb;
    class: SearchBreadcrumb;
  };
  breadcrumb_trail: string;
}

export interface SearchChapterResult {
  id: number;
  title: string;
  slug: string;
  chapter_number: number;
  is_free_sample: boolean;
  breadcrumbs: {
    board: SearchBreadcrumb;
    class: SearchBreadcrumb;
    subject: SearchBreadcrumb;
  };
  breadcrumb_trail: string;
}

export interface SearchResponse {
  query: string;
  total_count: number;
  subjects: SearchSubjectResult[];
  chapters: SearchChapterResult[];
}

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
  active?: boolean;
}
