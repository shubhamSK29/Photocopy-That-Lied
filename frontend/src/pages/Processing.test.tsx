import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act } from 'react'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Processing from './Processing'

// Mock the API service
vi.mock('../services/api', () => ({
  api: {
    getAnalysis: vi.fn(() => Promise.resolve({
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

function ProcessingRoutes() {
  return (
    <Routes>
      <Route path="/processing/:analysisId" element={<Processing />} />
      <Route path="/processing/*" element={<Processing />} />
    </Routes>
  )
}

describe('Processing Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders processing interface correctly', () => {
    render(
      <MemoryRouter initialEntries={['/processing/test-id-123']}>
        <ProcessingRoutes />
      </MemoryRouter>
    )

    expect(screen.getByText('Analyzing Image')).toBeInTheDocument()
    expect(screen.getByText(/Image validated/)).toBeInTheDocument()
  })

  it('shows all processing steps', () => {
    render(
      <MemoryRouter initialEntries={['/processing/test-id-123']}>
        <ProcessingRoutes />
      </MemoryRouter>
    )

    const steps = [
      'Image validated',
      'Metadata inspected',
      'Compression evidence analyzed',
      'Noise characteristics analyzed',
      'Spatial anomalies analyzed',
      'Combining forensic evidence',
      'Generating report'
    ]

    steps.forEach(step => {
      expect(screen.getByText(new RegExp(step, 'i'))).toBeInTheDocument()
    })
  })

  it('navigates to results when analysis completes', async () => {
    render(
      <MemoryRouter initialEntries={['/processing/test-id-123']}>
        <ProcessingRoutes />
      </MemoryRouter>
    )

    // The polling request becomes available after two seconds.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000)
    })

    expect(mockNavigate).toHaveBeenCalledWith('/results/test-id-123')
  })

  it('handles missing analysis ID gracefully', () => {
    render(
      <MemoryRouter initialEntries={['/processing/']}>
        <ProcessingRoutes />
      </MemoryRouter>
    )

    // Should not crash and should still show the processing interface
    expect(screen.getByText('Analyzing Image')).toBeInTheDocument()
  })
})
