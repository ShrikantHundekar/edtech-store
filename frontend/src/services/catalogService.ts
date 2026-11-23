import { api } from './api';
import type {
  Board,
  ClassLevel,
  Subject,
  Chapter,
  SearchResponse,
} from '../types/catalog';

export const catalogService = {
  getBoards: async (): Promise<Board[]> => {
    const { data } = await api.get<Board[]>('/catalog/boards/');
    return data;
  },

  getBoardClasses: async (boardId: number): Promise<ClassLevel[]> => {
    const { data } = await api.get<ClassLevel[]>(`/catalog/boards/${boardId}/classes/`);
    return data;
  },

  getClassSubjects: async (classId: number): Promise<Subject[]> => {
    const { data } = await api.get<Subject[]>(`/catalog/classes/${classId}/subjects/`);
    return data;
  },

  getSubjectChapters: async (subjectId: number): Promise<Chapter[]> => {
    const { data } = await api.get<Chapter[]>(`/catalog/subjects/${subjectId}/chapters/`);
    return data;
  },

  getChapter: async (chapterId: number): Promise<Chapter> => {
    const { data } = await api.get<Chapter>(`/catalog/chapters/${chapterId}/`);
    return data;
  },

  searchCatalog: async (query: string): Promise<SearchResponse> => {
    const { data } = await api.get<SearchResponse>('/catalog/search/', {
      params: { q: query },
    });
    return data;
  },

  getProducts: async (params?: Record<string, unknown>) => {
    const { data } = await api.get('/products/', { params });
    return data;
  },
};
