import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import History from './History';

// Mock the API
vi.mock('../services/api', () => ({
  api: {
    getConfig: vi.fn().mockResolvedValue({
      max_file_size_mb: 10,
      allowed_formats: ['jpg', 'png'],
      review_bands: { low_threshold: 30, high_threshold: 70 },
      limitations: [],
      disclaimer: 'Test disclaimer'
    })
  }
}));

// Mock fetch to return empty history immediately
global.fetch = vi.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({ items: [] })
  })
);

describe('History Page', () => {
  it('renders empty state when no history exists', async () => {
    render(
      <BrowserRouter>
        <History />
      </BrowserRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByText(/no analysis history/i)).toBeInTheDocument();
    });
  });
});
