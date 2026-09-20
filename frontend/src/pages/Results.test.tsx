import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Results from './Results'

// Mock the API service
vi.mock('../services/api', () => ({
  api: {
    getAnalysis: vi.fn(() => Promise.resolve({
      analysis_id: 'test-id-123',
      manipulation_evidence: 45.5,
      data_coverage: 72.3,
      risk_band: 'Review required',
      detectors: {
        copy_move: { status: 'not_detected', score: 0.0, explanation: 'No copy-move detected' },
        local_anomaly: { status: 'not_detected', score: 0.0, explanation: 'No local anomaly detected' },
        compression: { status: 'detected', score: 0.15, explanation: 'Compression artifacts detected' }
      },
      metadata: { status: 'available', exif_present: true },
      fusion: { mode: 'demo_fallback', demo_mode: true, model_version: 'fusion-demo-fallback', dataset_version: 'dataset-unavailable', note: 'DEMO MODE' },
      versions: { model_version: 'fusion-demo-fallback', dataset_version: 'dataset-unavailable' },
      warnings: ['Test warning'],
      limitations: ['Test limitation'],
      disclaimer: 'Test disclaimer',
      artifacts: { analysis_image: 'analysis.png', heatmap: 'heatmap.png', overlay: 'overlay.png', note: 'Test note' },
      natural_processing: { natural_processing_similarity: 0.5 },
      timestamp_integrity: { verification: 'partial' },
      spatial_agreement: { combined_dice: 0.3 },
      image: { sha256: 'abc123', format: 'JPEG', width: 1200, height: 800, file_size: 1024000 },
      duration_ms: 1500
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

function ResultRoutes() {
  return (
    <Routes>
      <Route path="/results/:analysisId" element={<Results />} />
      <Route path="/results/*" element={<Results />} />
    </Routes>
  )
}

describe('Results Component', () => {
  beforeEach(() => {
    mockNavigate.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders results interface correctly', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('PHOTOCOPY THAT LIED')).toBeInTheDocument()
      expect(screen.getByText('MANIPULATION EVIDENCE')).toBeInTheDocument()
      expect(screen.getByText('DATA COVERAGE')).toBeInTheDocument()
    })
  })

  it('displays manipulation evidence score', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('46')).toBeInTheDocument() // 45.5 rounded
    })
  })

  it('displays data coverage score', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('72')).toBeInTheDocument() // 72.3 rounded
    })
  })

  it('shows demo fallback mode when active', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Demo Fallback')).toBeInTheDocument()
      expect(screen.getByText('DEMO MODE')).toBeInTheDocument()
    })
  })

  it('displays detector cards', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Copy-Move')).toBeInTheDocument()
      expect(screen.getByText('Local Anomaly')).toBeInTheDocument()
      expect(screen.getByText('Compression')).toBeInTheDocument()
    })
  })

  it('expands detector details on click', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      const copyMoveButton = screen.getByText('Copy-Move Analysis')
      fireEvent.click(copyMoveButton)
      
      expect(screen.getByText('Status:')).toBeInTheDocument()
      expect(screen.getByText('Score:')).toBeInTheDocument()
      expect(screen.getByText('Explanation:')).toBeInTheDocument()
    })
  })

  it('displays heatmap view controls', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Original')).toBeInTheDocument()
      expect(screen.getByText('Heatmap')).toBeInTheDocument()
      expect(screen.getByText('Overlay')).toBeInTheDocument()
    })
  })

  it('switches heatmap views', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      const heatmapButton = screen.getByText('Heatmap')
      fireEvent.click(heatmapButton)
      
      // Verify the button is now active (blue background)
      expect(heatmapButton).toHaveClass('bg-blue-600')
    })
  })

  it('uses the analysis image artifact for the Original view', async () => {
    const { api } = await import('../services/api')
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      fireEvent.click(screen.getByText('Original'))
      expect(api.getArtifactUrl).toHaveBeenCalledWith('test-id-123', 'analysis.png')
    })
  })

  it('displays provenance information', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Provenance')).toBeInTheDocument()
      expect(screen.getByText('Analysis ID:')).toBeInTheDocument()
      expect(screen.getByText('SHA-256:')).toBeInTheDocument()
      expect(screen.getByText('File Type:')).toBeInTheDocument()
    })
  })

  it('displays warnings and limitations', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Warnings & Limitations')).toBeInTheDocument()
      expect(screen.getByText('Test warning')).toBeInTheDocument()
      expect(screen.getByText('Test limitation')).toBeInTheDocument()
    })
  })

  it('navigates to new analysis on button click', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      const newAnalysisButton = screen.getByText('New Analysis')
      fireEvent.click(newAnalysisButton)
      
      expect(mockNavigate).toHaveBeenCalledWith('/')
    })
  })

  it('handles missing analysis ID gracefully', async () => {
    render(
      <MemoryRouter initialEntries={['/results/']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Analysis not found')).toBeInTheDocument()
    })
  })

  it('displays disclaimer', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Test disclaimer')).toBeInTheDocument()
    })
  })
})
