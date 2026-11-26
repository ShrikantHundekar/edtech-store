import { api } from './api';
import type { Board, ClassLevel, Subject, Chapter } from '../types/catalog';

export interface BoardInput {
  name: string;
  slug?: string;
  description?: string;
}

export interface ClassInput {
  board: number;
  name: string;
  slug?: string;
}

export interface SubjectInput {
  academic_class: number;
  name: string;
  slug?: string;
  thumbnail_url?: string;
}

export interface ChapterInput {
  subject: number;
  chapter_number: number;
  title: string;
  slug?: string;
  is_free_sample?: boolean;
}

export const adminCatalogService = {
  // Boards
  async getBoards(): Promise<Board[]> {
    const { data } = await api.get<Board[]>('/admin/boards/');
    return data;
  },
  async createBoard(input: BoardInput): Promise<Board> {
    const { data } = await api.post<Board>('/admin/boards/', input);
    return data;
  },
  async updateBoard(id: number, input: Partial<BoardInput>): Promise<Board> {
    const { data } = await api.patch<Board>(`/admin/boards/${id}/`, input);
    return data;
  },
  async deleteBoard(id: number): Promise<void> {
    await api.delete(`/admin/boards/${id}/`);
  },

  // Classes
  async getClasses(boardId?: number): Promise<ClassLevel[]> {
    const params = boardId ? { board_id: boardId } : undefined;
    const { data } = await api.get<ClassLevel[]>('/admin/classes/', { params });
    return data;
  },
  async createClass(input: ClassInput): Promise<ClassLevel> {
    const { data } = await api.post<ClassLevel>('/admin/classes/', input);
    return data;
  },
  async updateClass(id: number, input: Partial<ClassInput>): Promise<ClassLevel> {
    const { data } = await api.patch<ClassLevel>(`/admin/classes/${id}/`, input);
    return data;
  },
  async deleteClass(id: number): Promise<void> {
    await api.delete(`/admin/classes/${id}/`);
  },

  // Subjects
  async getSubjects(classId?: number): Promise<Subject[]> {
    const params = classId ? { class_id: classId } : undefined;
    const { data } = await api.get<Subject[]>('/admin/subjects/', { params });
    return data;
  },
  async createSubject(input: SubjectInput): Promise<Subject> {
    const { data } = await api.post<Subject>('/admin/subjects/', input);
    return data;
  },
  async updateSubject(id: number, input: Partial<SubjectInput>): Promise<Subject> {
    const { data } = await api.patch<Subject>(`/admin/subjects/${id}/`, input);
    return data;
  },
  async deleteSubject(id: number): Promise<void> {
    await api.delete(`/admin/subjects/${id}/`);
  },

  // Chapters
  async getChapters(subjectId?: number): Promise<Chapter[]> {
    const params = subjectId ? { subject_id: subjectId } : undefined;
    const { data } = await api.get<Chapter[]>('/admin/chapters/', { params });
    return data;
  },
  async createChapter(input: ChapterInput): Promise<Chapter> {
    const { data } = await api.post<Chapter>('/admin/chapters/', input);
    return data;
  },
  async updateChapter(id: number, input: Partial<ChapterInput>): Promise<Chapter> {
    const { data } = await api.patch<Chapter>(`/admin/chapters/${id}/`, input);
    return data;
  },
  async deleteChapter(id: number): Promise<void> {
    await api.delete(`/admin/chapters/${id}/`);
  },

  // Chapter PDF Upload & Free Sample Toggle (Issue #46)
  async uploadChapterPDF(
    chapterId: number,
    file: File,
    title?: string,
    onProgress?: (percent: number) => void
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    if (title && title.trim()) {
      formData.append('title', title.trim());
    }

    const { data } = await api.post(`/admin/chapters/${chapterId}/upload-material/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
    return data;
  },

  async toggleFreeSample(chapterId: number, isFreeSample?: boolean): Promise<Chapter> {
    const body = isFreeSample !== undefined ? { is_free_sample: isFreeSample } : {};
    const { data } = await api.post<Chapter>(`/admin/chapters/${chapterId}/toggle-free-sample/`, body);
    return data;
  },
};

