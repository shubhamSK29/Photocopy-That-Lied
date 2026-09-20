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
    return request<UploadConfig>('/api/config');
  },

  async analyzeImage(file: File): Promise<AnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: { message: 'Analysis failed' } }));
      throw new Error(error.detail?.message || `HTTP ${response.status}`);
    }

    return response.json();
  },

  async getAnalysis(analysisId: string): Promise<AnalysisResult> {
    return request<AnalysisResult>(`/api/analysis/${analysisId}`);
  },

  async getArtifact(analysisId: string, name: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/artifacts/${analysisId}/${name}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch artifact: ${name}`);
    }
    return response.blob();
  },

  getArtifactUrl(analysisId: string, name: string): string {
    return `${API_BASE_URL}/api/artifacts/${analysisId}/${name}`;
  },
};
