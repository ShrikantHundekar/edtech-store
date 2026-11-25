export type UnlockedViaType = 'CHAPTER' | 'SUBJECT' | 'CLASS_PASS' | 'FREE_SAMPLE';

export interface PassItem {
  id: number;
  class_id: number;
  class_name: string;
  board_name: string;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  status: string;
  remaining_days: number;
  remaining_seconds: number;
  countdown_text: string;
}

export interface LibraryMaterial {
  id: number;
  title: string;
  mime_type: string;
  file_size_bytes: number;
  stream_url: string;
}

export interface LibraryChapter {
  id: number;
  chapter_number: number;
  title: string;
  subject_id: number;
  subject_name: string;
  class_id: number;
  class_name: string;
  board_name: string;
  is_free_sample: boolean;
  unlocked_via: UnlockedViaType;
  materials: LibraryMaterial[];
}

export interface LibrarySubject {
  id: number;
  name: string;
  class_name: string;
  board_name: string;
  chapters_count: number;
}

export interface StudentLibraryResponse {
  passes: PassItem[];
  chapters: LibraryChapter[];
  subjects: LibrarySubject[];
  stats: {
    active_passes_count: number;
    total_chapters_unlocked: number;
    direct_chapters_count: number;
    direct_subjects_count: number;
  };
}
