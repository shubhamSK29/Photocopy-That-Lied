import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Upload from './Upload'

// Mock the API service
vi.mock('../services/api', () => ({
  api: {
    getConfig: vi.fn(() => Promise.resolve({
      max_file_size_mb: 25,
      allowed_formats: ['JPEG', 'PNG', 'WEBP'],
      review_bands: {
        low_threshold: 30,
        high_threshold: 60
      },
      limitations: [],
      disclaimer: 'Test disclaimer'
    })),
    analyzeImage: vi.fn(() => Promise.resolve({
      analysis_id: 'test-id-123',
      manipulation_evidence: 45.5,
      data_coverage: 72.3,
      risk_band: 'Review required'
    })),
    getArtifactUrl: vi.fn((id: string, name: string) => `http://localhost:8000/api/artifacts/${id}/${name}`)
  }
}))

// Mock the navigate function
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

describe('Upload Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
  })

  it('renders upload interface correctly', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    expect(screen.getByText('PHOTOCOPY THAT LIED')).toBeInTheDocument()
    expect(screen.getByText('AI-Assisted Image Forensics for Crop Insurance Review')).toBeInTheDocument()
    expect(screen.getByText('Drag & Drop Image')).toBeInTheDocument()
    expect(screen.getByText('Choose Image')).toBeInTheDocument()
    await screen.findByText(/Supported formats:/)
  })

  it('handles file selection via click', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    const fileInput = screen.getByLabelText(/choose image/i) as HTMLInputElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/results/test-id-123')
    })
  })

  it('handles drag and drop', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    const dropZone = screen.getByText('Drag & Drop Image').parentElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })

    if (dropZone) {
      fireEvent.dragOver(dropZone)
      fireEvent.drop(dropZone, {
        dataTransfer: { files: [file] }
      })

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/results/test-id-123')
      })
    }
  })

  it('shows loading state during upload', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    await screen.findByText(/Supported formats:/)
    const fileInput = screen.getByLabelText(/choose image/i) as HTMLInputElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })

    fireEvent.change(fileInput, { target: { files: [file] } })

    // Check for loading state
    expect(screen.getByText('Analyzing image...')).toBeInTheDocument()
  })

  it('displays error on upload failure', async () => {
    // Mock API to fail
    const { api } = await import('../services/api')
    vi.mocked(api.analyzeImage).mockRejectedValueOnce(new Error('Upload failed'))

    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    const fileInput = screen.getByLabelText(/choose image/i) as HTMLInputElement
    const file = new File(['test'], 'test.jpg', { type: 'image/jpeg' })

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('Upload failed')).toBeInTheDocument()
    })
  })

  it('displays configuration information', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Supported formats:/)).toBeInTheDocument()
      expect(screen.getByText(/Maximum file size:/)).toBeInTheDocument()
    })
  })

  it('validates file types', async () => {
    render(
      <MemoryRouter>
        <Upload />
      </MemoryRouter>
    )

    const fileInput = screen.getByLabelText(/choose image/i) as HTMLInputElement
    
    // Test that only image files are accepted
    expect(fileInput.accept).toBe('image/jpeg,image/png,image/webp')
    await screen.findByText(/Supported formats:/)
  })
})
