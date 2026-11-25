import { api } from './api';
import type { StudentLibraryResponse } from '../types/library';

export const libraryService = {
  /**
   * Fetch authenticated student library dashboard data
   */
  async getStudentLibrary(): Promise<StudentLibraryResponse> {
    const { data } = await api.get<StudentLibraryResponse>('/entitlements/my-library/');
    return data;
  },

  /**
   * Stream protected PDF note file from backend streaming endpoint
   * Converts byte response into a temporary Blob Object URL
   */
  async streamMaterialPDF(materialId: number): Promise<{ url: string; blob: Blob }> {
    const response = await api.get(`/materials/${materialId}/stream/`, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    return { url, blob };
  },
};
