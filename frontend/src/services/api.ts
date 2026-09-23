import type { AnalysisResult, UploadConfig } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Request failed' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  async getConfig(): Promise<UploadConfig> {
    try {
      return await request<UploadConfig>('/api/config');
    } catch (error) {
      console.error('Failed to fetch config:', error);
      throw new Error('Cannot connect to analysis server. Please ensure the backend is running on port 8000.');
    }
  },

  async analyzeImage(file: File): Promise<AnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: { message: 'Analysis failed' } }));
        throw new Error(error.detail?.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error('Failed to analyze image:', error);
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Network error occurred while uploading image. Please check your connection.');
    }
  },

  async getAnalysis(analysisId: string): Promise<AnalysisResult> {
    try {
      return await request<AnalysisResult>(`/api/analysis/${analysisId}`);
    } catch (error) {
      console.error('Failed to fetch analysis:', error);
      throw new Error('Failed to load analysis results. Please try again.');
    }
  },

  async getArtifact(analysisId: string, name: string): Promise<Blob> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/artifacts/${analysisId}/${name}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch artifact: ${name}`);
      }
      return response.blob();
    } catch (error) {
      console.error('Failed to fetch artifact:', error);
      throw new Error('Failed to load image artifact. Please try again.');
    }
  },

  getArtifactUrl(analysisId: string, name: string): string {
    return `${API_BASE_URL}/api/artifacts/${analysisId}/${name}`;
  },
};
