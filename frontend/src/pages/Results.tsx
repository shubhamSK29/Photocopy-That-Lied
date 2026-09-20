import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import type { AnalysisResult } from '../types';

export default function Results() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heatmapView, setHeatmapView] = useState<'original' | 'heatmap' | 'overlay'>('overlay');
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  useEffect(() => {
    if (!analysisId) {
      setLoading(false);
      return;
    }

    api.getAnalysis(analysisId)
      .then(setResult)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [analysisId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-red-700 max-w-md">
          {error || 'Analysis not found'}
        </div>
      </div>
    );
  }

  const getRiskBandColor = (band: string) => {
    if (band.includes('No significant')) return 'bg-green-100 text-green-800';
    if (band.includes('Review required')) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getDetectorStrength = (score: number) => {
    if (score >= 0.6) return 'Strong';
    if (score >= 0.3) return 'Moderate';
    if (score > 0) return 'Weak';
    return 'None';
  };

  const toggleCard = (cardName: string) => {
    setExpandedCard(expandedCard === cardName ? null : cardName);
  };

  const artifactName = {
    original: result.artifacts.analysis_image,
    heatmap: result.artifacts.heatmap,
    overlay: result.artifacts.overlay,
  }[heatmapView];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            PHOTOCOPY THAT LIED
          </h1>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
          >
            New Analysis
          </button>
        </div>

        {/* Scores Section */}
        <div className="bg-white rounded-lg shadow-sm p-8 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-2">MANIPULATION EVIDENCE</h2>
              <div className="text-5xl font-bold text-gray-900 mb-2">
                {result.manipulation_evidence.toFixed(0)} <span className="text-2xl text-gray-500">/ 100</span>
              </div>
              <div className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getRiskBandColor(result.risk_band)}`}>
                {result.risk_band.toUpperCase()}
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-700 mb-2">DATA COVERAGE</h2>
              <div className="text-5xl font-bold text-gray-900 mb-2">
                {result.data_coverage.toFixed(0)} <span className="text-2xl text-gray-500">/ 100</span>
              </div>
              <p className="text-sm text-gray-500">
                How well the image fits tested conditions
              </p>
            </div>
          </div>
        </div>

        {/* Evidence Summary */}
        <div className={`rounded-lg border p-4 mb-6 ${result.fusion.demo_mode ? 'bg-amber-50 border-amber-300 text-amber-900' : 'bg-emerald-50 border-emerald-300 text-emerald-900'}`}>
          <span className="font-semibold">Analysis Mode: </span>
          {result.fusion.demo_mode ? 'Demo Fallback' : 'Trained Fusion Model'}
          <span className="ml-3 text-sm">{result.fusion.model_version} · {result.fusion.dataset_version}</span>
          <p className="text-sm mt-1">{result.fusion.note}</p>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Evidence Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-1">Copy-Move</div>
              <div className="font-semibold">{getDetectorStrength(result.detectors.copy_move.score)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-1">Local Anomaly</div>
              <div className="font-semibold">{getDetectorStrength(result.detectors.local_anomaly.score)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-1">Compression</div>
              <div className="font-semibold">{getDetectorStrength(result.detectors.compression.score)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-1">Natural Match</div>
              <div className="font-semibold">{getDetectorStrength(result.natural_processing.natural_processing_similarity)}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-600 mb-1">Spatial Agreement</div>
              <div className="font-semibold">{getDetectorStrength(result.spatial_agreement.combined_dice)}</div>
            </div>
          </div>
        </div>

        {/* Evidence Details */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Evidence Details</h3>

          {[
            { key: 'copy_move', label: 'Copy-Move Analysis', detector: result.detectors.copy_move },
            { key: 'local_anomaly', label: 'Local Inconsistency', detector: result.detectors.local_anomaly },
            { key: 'compression', label: 'Compression / Resampling', detector: result.detectors.compression },
            { key: 'natural', label: 'Natural Processing', detector: null, custom: result.natural_processing },
            { key: 'timestamp', label: 'Timestamp Integrity', detector: null, custom: result.timestamp_integrity },
            { key: 'metadata', label: 'Metadata', detector: null, custom: result.metadata },
          ].map((item) => (
            <div key={item.key} className="border-b border-gray-200 last:border-0">
              <button
                onClick={() => toggleCard(item.key)}
                className="w-full py-4 px-4 flex justify-between items-center hover:bg-gray-50 transition-colors"
              >
                <span className="font-medium text-gray-900">{item.label}</span>
                <svg
                  className={`w-5 h-5 text-gray-500 transition-transform ${expandedCard === item.key ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {expandedCard === item.key && (
                <div className="px-4 pb-4 text-sm text-gray-600">
                  {item.detector && (
                    <>
                      <div className="mb-2">
                        <span className="font-medium">Status:</span> {item.detector.status}
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Score:</span> {(item.detector.score * 100).toFixed(1)}%
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Explanation:</span> {item.detector.explanation}
                      </div>
                      {item.detector.metrics && Object.keys(item.detector.metrics).length > 0 && (
                        <div>
                          <span className="font-medium">Metrics:</span>
                          <pre className="mt-1 bg-gray-50 p-2 rounded overflow-x-auto">
                            {JSON.stringify(item.detector.metrics, null, 2)}
                          </pre>
                        </div>
                      )}
                    </>
                  )}
                  {item.custom && (
                    <pre className="bg-gray-50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(item.custom, null, 2)}
                    </pre>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Heatmap Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Forensic Heatmap</h3>
          <div className="mb-4">
            <div className="flex gap-2">
              <button
                onClick={() => setHeatmapView('original')}
                className={`px-4 py-2 rounded ${heatmapView === 'original' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
              >
                Original
              </button>
              <button
                onClick={() => setHeatmapView('heatmap')}
                className={`px-4 py-2 rounded ${heatmapView === 'heatmap' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
              >
                Heatmap
              </button>
              <button
                onClick={() => setHeatmapView('overlay')}
                className={`px-4 py-2 rounded ${heatmapView === 'overlay' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'}`}
              >
                Overlay
              </button>
            </div>
          </div>
          <div className="relative bg-gray-100 rounded-lg overflow-hidden" style={{ minHeight: '400px' }}>
            <img
              src={api.getArtifactUrl(result.analysis_id, artifactName)}
              alt={heatmapView}
              className="w-full h-auto"
              onError={(e) => {
                e.currentTarget.src = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect fill="#f3f4f6" width="400" height="300"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#9ca3af">Image not available</text></svg>');
              }}
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">{result.artifacts.note}</p>
        </div>

        {/* Provenance Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Provenance</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Analysis ID:</span>
              <div className="font-mono text-gray-900">{result.analysis_id}</div>
            </div>
            <div>
              <span className="text-gray-600">SHA-256:</span>
              <div className="font-mono text-gray-900 break-all">{result.image.sha256}</div>
            </div>
            <div>
              <span className="text-gray-600">File Type:</span>
              <div className="font-mono text-gray-900">{result.image.format}</div>
            </div>
            <div>
              <span className="text-gray-600">Dimensions:</span>
              <div className="font-mono text-gray-900">{result.image.width} × {result.image.height}</div>
            </div>
            <div>
              <span className="text-gray-600">File Size:</span>
              <div className="font-mono text-gray-900">{(result.image.file_size / 1024 / 1024).toFixed(2)} MB</div>
            </div>
            <div>
              <span className="text-gray-600">Analysis Time:</span>
              <div className="font-mono text-gray-900">{result.duration_ms} ms</div>
            </div>
            <div>
              <span className="text-gray-600">Model / Dataset:</span>
              <div className="font-mono text-gray-900">{result.versions.model_version} / {result.versions.dataset_version}</div>
            </div>
          </div>
        </div>

        {/* Warnings and Limitations */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold text-yellow-900 mb-4">Warnings & Limitations</h3>
          <ul className="space-y-2 text-sm text-yellow-800">
            {result.warnings.map((warning, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">⚠️</span>
                <span>{warning}</span>
              </li>
            ))}
            {result.limitations.map((limitation, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">ℹ️</span>
                <span>{limitation}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Disclaimer */}
        <div className="bg-gray-100 rounded-lg p-6 text-center text-sm text-gray-600">
          {result.disclaimer}
        </div>
      </div>
    </div>
  );
}
