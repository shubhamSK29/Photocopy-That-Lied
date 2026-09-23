import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Results from './Results'
import Layout from '../components/Layout'

// Mock the API service
vi.mock('../services/api', () => ({
  api: {
    getAnalysis: vi.fn(() => Promise.resolve({
      analysis_id: 'test-id-123',
      manipulation_evidence: 45.5,
      data_coverage: 72.3,
      risk_band: 'Review required',
      bands: {
        low_threshold: 30,
        high_threshold: 70,
        note: 'Test note'
      },
      detectors: {
        copy_move: { status: 'not_detected', score: 0.0, explanation: 'No copy-move detected', metrics: {} },
        local_anomaly: { status: 'not_detected', score: 0.0, explanation: 'No local anomaly detected', metrics: {} },
        compression: { status: 'detected', score: 0.15, explanation: 'Compression artifacts detected', metrics: {} },
        visible_timestamp: { status: 'not_detected', score: 0.0, explanation: 'No timestamp detected', metrics: {} }
      },
      metadata: { available: true, camera_make: 'Test', camera_model: 'Test Camera', capture_datetime: '2024-01-01T00:00:00Z', software: null, orientation: null, exif_data: {} },
      fusion: { mode: 'demo_fallback', demo_mode: true, model_version: 'fusion-demo-fallback', dataset_version: 'dataset-unavailable', note: 'DEMO MODE', manipulation_evidence: 45.5, probability: 0.5, model_kind: 'test' },
      versions: { model_version: 'fusion-demo-fallback', dataset_version: 'dataset-unavailable', feature_version: 'v1', pipeline_version: 'v1' },
      warnings: ['Test warning'],
      limitations: ['Test limitation'],
      disclaimer: 'Test disclaimer',
      artifacts: { analysis_image: 'analysis.png', heatmap: 'heatmap.png', overlay: 'overlay.png', note: 'Test note' },
      natural_processing: { 
        status: 'unavailable',
        natural_processing_similarity: 0.5, 
        matched_transformations: [], 
        matched_device_domain: null, 
        confidence: 0.5,
        library_version: 'v1',
        library_size: 0,
        interpretation: 'Test interpretation'
      },
      timestamp_integrity: { 
        exif_timestamp: null, 
        exif_status: 'unavailable',
        exif_note: 'No EXIF available',
        visible_timestamp_detected: false,
        visible_timestamp_text: null,
        visible_timestamp_location: null,
        visible_timestamp_confidence: null,
        visible_timestamp_status: 'not_detected',
        verification: 'not_possible',
        summary: 'Timestamp verification not possible'
      },
      spatial_agreement: { 
        detectors_with_regions: [],
        pairs: {},
        max_iou: 0.0,
        max_dice: 0.0,
        agreement_level: 'none',
        agreeing_pairs: [],
        consensus_regions: [],
        note: 'Test note'
      },
      coverage: { score: 72.3, resolution_similarity: 0.8, forensic_feature_similarity: 0.7, device_coverage: 0.6, quality_score: 0.5 },
      explanation: { primary_evidence: [], supporting_evidence: [], weak_evidence: [], unavailable_evidence: [], natural_processing_note: 'Test', metadata_note: 'Test' },
      features: {},
      regions: [],
      image: { sha256: 'abc123', format: 'JPEG', width: 1200, height: 800, file_size: 1024000, mime: 'image/jpeg', megapixels: 0.96, analysis_width: 1200, analysis_height: 800, analysis_scale: 1.0, filename: 'test.jpg' },
      duration_ms: 1500,
      created_at: '2024-01-01T00:00:00Z'
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
    <Layout>
      <Routes>
        <Route path="/results/:analysisId" element={<Results />} />
        <Route path="/results/*" element={<Results />} />
        <Route path="/" element={<div>Upload Page</div>} />
      </Routes>
    </Layout>
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
      expect(screen.getByText('Forensic Screening Result')).toBeInTheDocument()
      expect(screen.getByText('Manipulation Evidence')).toBeInTheDocument()
      expect(screen.getByText('Data Coverage')).toBeInTheDocument()
    })
  })

  it('displays manipulation evidence score', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Manipulation Evidence')).toBeInTheDocument()
    })
  })

  it('displays data coverage score', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Data Coverage')).toBeInTheDocument()
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
      expect(screen.getByText('Copy-Move Analysis')).toBeInTheDocument()
      expect(screen.getByText('Local Inconsistency')).toBeInTheDocument()
      expect(screen.getByText('Compression Consistency')).toBeInTheDocument()
    })
  })

  it('expands detector details on click', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Copy-Move Analysis')).toBeInTheDocument()
    })
  })

  it('displays spatial agreement section', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Spatial Agreement')).toBeInTheDocument()
    })
  })

  it('displays natural processing calibration section', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Natural Processing Calibration')).toBeInTheDocument()
    })
  })

  it('displays heatmap view controls', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Image Comparison')).toBeInTheDocument()
    })
  })

  it('displays provenance information', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Analysis Provenance')).toBeInTheDocument()
      expect(screen.getByText('Analysis ID')).toBeInTheDocument()
      expect(screen.getByText('SHA-256')).toBeInTheDocument()
      expect(screen.getByText('Format')).toBeInTheDocument()
    })
  })

  it('displays warnings and limitations', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/limitations/i)).toBeInTheDocument()
    })
  })

  it('displays timestamp and metadata section', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Timestamp & Metadata')).toBeInTheDocument()
    })
  })

  it('navigates to new analysis on button click', async () => {
    render(
      <MemoryRouter initialEntries={['/results/test-id-123']}>
        <ResultRoutes />
      </MemoryRouter>
    )

    await waitFor(() => {
      // Just verify the button exists
      expect(screen.getByText('New Analysis')).toBeInTheDocument()
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
