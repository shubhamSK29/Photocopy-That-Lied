import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  Shield, AlertTriangle, Activity, FileText, Upload, Copy, 
  XCircle, Info, Eye, HardDrive, Fingerprint, Clock
} from 'lucide-react';
import { api } from '../services/api';
import type { AnalysisResult } from '../types';

export default function Results() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [heatmapView, setHeatmapView] = useState<'original' | 'heatmap' | 'overlay'>('overlay');
  const [activeTab, setActiveTab] = useState<'summary' | 'evidence' | 'metadata' | 'timestamp' | 'limitations' | 'provenance'>('summary');

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
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400"></div>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="p-6">
        <div className="glass-card-light rounded-xl p-6 max-w-md border border-danger/30">
          <div className="flex items-center space-x-3 mb-4">
            <XCircle className="w-6 h-6 text-danger" />
            <span className="font-semibold text-danger">Error</span>
          </div>
          <p className="text-text-muted mb-4">{error || 'Analysis not found'}</p>
          <Link
            to="/"
            className="btn-primary px-4 py-2 text-white rounded-lg text-sm font-medium inline-flex items-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>Return to Upload</span>
          </Link>
        </div>
      </div>
    );
  }

  const getRiskCategory = (score: number) => {
    if (!result.bands) return 'REVIEW REQUIRED';
    if (score < result.bands.low_threshold) return 'LOW RISK';
    if (score < result.bands.high_threshold) return 'REVIEW REQUIRED';
    return 'HIGH RISK';
  };

  const getDetectorStrength = (score: number) => {
    if (score >= 0.6) return { label: 'Strong', color: 'text-danger' };
    if (score >= 0.3) return { label: 'Moderate', color: 'text-warning' };
    if (score > 0) return { label: 'Weak', color: 'text-cyan-400' };
    return { label: 'None', color: 'text-text-muted' };
  };

  const artifactName = {
    original: result.artifacts.analysis_image,
    heatmap: result.artifacts.heatmap,
    overlay: result.artifacts.overlay,
  }[heatmapView];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="page-container py-6 animate-fade-in">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Analysis Results</h1>
            <p className="text-text-muted">Analysis ID: {result.analysis_id}</p>
          </div>
          <Link
            to="/"
            className="btn-primary px-6 py-3 text-white rounded-xl font-medium shadow-lg inline-flex items-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>New Analysis</span>
          </Link>
        </div>

        {/* Main Results Grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
          {/* Left: Image with Heatmap */}
          <div className="glass-card rounded-xl p-6">
            <h2 className="text-xl font-bold text-white mb-4">Image Analysis</h2>
            
            {/* View Toggle */}
            <div className="flex gap-2 mb-4">
              {['original', 'heatmap', 'overlay'].map((view) => (
                <button
                  key={view}
                  onClick={() => setHeatmapView(view as any)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    heatmapView === view
                      ? 'btn-primary'
                      : 'btn-secondary'
                  }`}
                >
                  {view === 'original' ? 'Original' : view === 'heatmap' ? 'Heatmap' : 'Overlay'}
                </button>
              ))}
            </div>

            {/* Image Display */}
            <div className="relative bg-card-light rounded-xl overflow-hidden border border-border" style={{ minHeight: '400px' }}>
              <img
                src={api.getArtifactUrl(result.analysis_id, artifactName)}
                alt={heatmapView}
                className="w-full h-auto"
                onError={(e) => {
                  e.currentTarget.src = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect fill="#0f1425" width="400" height="300"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#718096">Image not available</text></svg>');
                }}
              />
            </div>
            
            {/* Legend */}
            {heatmapView !== 'original' && (
              <div className="mt-4 flex items-center justify-center space-x-6 text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 rounded bg-danger"></div>
                  <span className="text-text-muted">High evidence</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 rounded bg-warning"></div>
                  <span className="text-text-muted">Medium evidence</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 rounded bg-cyan-500"></div>
                  <span className="text-text-muted">Low evidence</span>
                </div>
              </div>
            )}
          </div>

          {/* Right: Score and Risk */}
          <div className="space-y-6">
            {/* Risk Score */}
            <div className="glass-card rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">Manipulation Evidence Score</h2>
              
              <div className="flex items-center justify-center mb-6">
                <div className="relative">
                  <svg className="w-48 h-48 transform -rotate-90">
                    <circle
                      cx="96"
                      cy="96"
                      r="88"
                      stroke="#1e3a5f"
                      strokeWidth="12"
                      fill="none"
                    />
                    <circle
                      cx="96"
                      cy="96"
                      r="88"
                      stroke="url(#gradient)"
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${2 * Math.PI * 88}`}
                      strokeDashoffset={`${2 * Math.PI * 88 * (1 - result.manipulation_evidence / 100)}`}
                      strokeLinecap="round"
                    />
                    <defs>
                      <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#00b8ff" />
                        <stop offset="100%" stopColor="#00f3bc" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-4xl font-bold text-white">
                        {result.manipulation_evidence.toFixed(0)}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-center mb-4">
                <div className={`inline-block px-6 py-3 rounded-xl font-bold text-lg ${
                  getRiskCategory(result.manipulation_evidence) === 'LOW RISK' ? 'risk-low' :
                  getRiskCategory(result.manipulation_evidence) === 'REVIEW REQUIRED' ? 'risk-medium' :
                  'risk-high'
                }`}>
                  {getRiskCategory(result.manipulation_evidence)}
                </div>
              </div>

              <div className="glass-card-light rounded-lg p-4 text-center">
                <div className="flex items-center justify-center space-x-2 text-warning">
                  <Shield className="w-5 h-5" />
                  <span className="font-semibold">Human Review Required</span>
                </div>
                <p className="text-text-muted text-sm mt-2">
                  This system provides forensic screening evidence to support human review. It does not determine fraud.
                </p>
              </div>
            </div>

            {/* Data Coverage */}
            <div className="glass-card rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">Data Coverage</h3>
              <div className="flex items-center space-x-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-text-muted">Coverage Score</span>
                    <span className="text-sm font-bold text-white">{result.data_coverage.toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-card-light rounded-full h-2">
                    <div 
                      className="progress-bar h-2 rounded-full transition-all duration-300"
                      style={{ width: `${result.data_coverage}%` }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs Section */}
        <div className="glass-card rounded-xl p-6">
          {/* Tab Navigation */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {[
              { key: 'summary', label: 'Summary', icon: FileText },
              { key: 'evidence', label: 'Evidence', icon: Activity },
              { key: 'metadata', label: 'Metadata', icon: HardDrive },
              { key: 'timestamp', label: 'Timestamp', icon: Clock },
              { key: 'limitations', label: 'Limitations', icon: Info },
              { key: 'provenance', label: 'Provenance', icon: Fingerprint },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key as any)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                    activeTab === tab.key
                      ? 'btn-primary'
                      : 'btn-secondary'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          {activeTab === 'summary' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold text-white mb-4">Key Findings</h3>
                <ul className="space-y-3 text-text-muted">
                  <li className="flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                    <span>Suspicious region detected in the submitted image</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <Activity className="w-5 h-5 text-cyan-400 flex-shrink-0 mt-0.5" />
                    <span>Forensic analysis completed with {result.manipulation_evidence.toFixed(0)}% manipulation evidence</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <Info className="w-5 h-5 text-text-muted flex-shrink-0 mt-0.5" />
                    <span>Multiple forensic detectors indicate potential manipulation</span>
                  </li>
                </ul>
              </div>

              <div className="glass-card-light rounded-lg p-4">
                <h4 className="font-bold text-white mb-2">Reviewer Recommendation</h4>
                <p className="text-text-muted">
                  Human review required before making any insurance decision. This system provides screening evidence only.
                </p>
              </div>
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-4">
              {[
                { key: 'copy_move', label: 'Copy-Move Detection', detector: result.detectors.copy_move },
                { key: 'local_anomaly', label: 'Local Inconsistency', detector: result.detectors.local_anomaly },
                { key: 'compression', label: 'Compression / Resampling', detector: result.detectors.compression },
                { key: 'visible_timestamp', label: 'Visible Timestamp Detection', detector: result.detectors.visible_timestamp },
              ].map((item) => {
                const strength = getDetectorStrength(item.detector.score);
                return (
                  <div key={item.key} className="glass-card-light rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-bold text-white">{item.label}</h4>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${strength.color}`}>
                        {strength.label}
                      </span>
                    </div>
                    <div className="text-sm text-text-muted mb-2">
                      <span className="text-white font-medium">Status:</span> {item.detector.status}
                    </div>
                    <div className="text-sm text-text-muted">
                      <span className="text-white font-medium">Explanation:</span> {item.detector.explanation}
                    </div>
                    <div className="text-sm text-text-muted mt-2">
                      <span className="text-white font-medium">Score:</span> {(item.detector.score * 100).toFixed(1)}%
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {activeTab === 'metadata' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="glass-card-light rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <HardDrive className="w-4 h-4 text-cyan-400" />
                    <span className="text-text-muted text-sm">Filename</span>
                  </div>
                  <div className="text-white font-mono text-sm">{result.image.filename}</div>
                </div>
                <div className="glass-card-light rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <HardDrive className="w-4 h-4 text-cyan-400" />
                    <span className="text-text-muted text-sm">File Size</span>
                  </div>
                  <div className="text-white">{(result.image.file_size / 1024 / 1024).toFixed(2)} MB</div>
                </div>
                <div className="glass-card-light rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <Activity className="w-4 h-4 text-cyan-400" />
                    <span className="text-text-muted text-sm">Dimensions</span>
                  </div>
                  <div className="text-white">{result.image.width} × {result.image.height}</div>
                </div>
                <div className="glass-card-light rounded-lg p-4">
                  <div className="flex items-center space-x-2 mb-2">
                    <FileText className="w-4 h-4 text-cyan-400" />
                    <span className="text-text-muted text-sm">Format</span>
                  </div>
                  <div className="text-white">{result.image.format}</div>
                </div>
              </div>

              {result.metadata.available && (
                <div className="glass-card-light rounded-lg p-4">
                  <h4 className="font-bold text-white mb-3">Camera Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Make:</span>
                      <span className="text-white">{result.metadata.camera_make || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Model:</span>
                      <span className="text-white">{result.metadata.camera_model || 'Unknown'}</span>
                    </div>
                    {result.metadata.software && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Software:</span>
                        <span className="text-white">{result.metadata.software}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'timestamp' && (
            <div className="space-y-4">
              <div className="glass-card-light rounded-lg p-4">
                <h4 className="font-bold text-white mb-3">Timestamp Information</h4>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center space-x-2 mb-2">
                      <Clock className="w-4 h-4 text-cyan-400" />
                      <span className="text-text-muted text-sm">EXIF Timestamp</span>
                    </div>
                    {result.timestamp_integrity.exif_timestamp ? (
                      <div className="text-white font-mono text-sm">{result.timestamp_integrity.exif_timestamp}</div>
                    ) : (
                      <div className="text-warning text-sm">Missing / Inconsistent</div>
                    )}
                  </div>
                  
                  <div>
                    <div className="flex items-center space-x-2 mb-2">
                      <Eye className="w-4 h-4 text-cyan-400" />
                      <span className="text-text-muted text-sm">Visible Timestamp</span>
                    </div>
                    {result.timestamp_integrity.visible_timestamp_detected ? (
                      <div className="text-white text-sm">{result.timestamp_integrity.visible_timestamp_text}</div>
                    ) : (
                      <div className="text-text-muted text-sm">Not Detected</div>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center space-x-2 mb-2">
                      <Shield className="w-4 h-4 text-cyan-400" />
                      <span className="text-text-muted text-sm">Verification Status</span>
                    </div>
                    <div className="text-warning text-sm">Unavailable — insufficient evidence</div>
                  </div>
                </div>
              </div>

              <div className="glass-card-light rounded-lg p-4 border border-warning/30">
                <div className="flex items-start space-x-3">
                  <Info className="w-5 h-5 text-warning flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-text-muted">
                    <strong className="text-warning">Important:</strong> Timestamp verification is limited to evidence available in the submitted image. The system cannot recover an original timestamp when supporting evidence has been removed.
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'limitations' && (
            <div className="space-y-4">
              <div className="glass-card-light rounded-lg p-4 border border-warning/30">
                <h4 className="font-bold text-warning mb-4 flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Analysis Limitations</span>
                </h4>
                <ul className="space-y-3 text-sm text-text-muted">
                  {result.limitations.map((limitation, index) => (
                    <li key={index} className="flex items-start space-x-3">
                      <span className="text-warning mt-1">•</span>
                      <span>{limitation}</span>
                    </li>
                  ))}
                  <li className="flex items-start space-x-3">
                    <span className="text-warning mt-1">•</span>
                    <span>Results are based only on the submitted image</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="text-warning mt-1">•</span>
                    <span>Missing metadata reduces confidence</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="text-warning mt-1">•</span>
                    <span>Natural smartphone processing can create forensic artifacts</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="text-warning mt-1">•</span>
                    <span>A forensic score is evidence, not proof of fraud</span>
                  </li>
                  <li className="flex items-start space-x-3">
                    <span className="text-warning mt-1">•</span>
                    <span>Final insurance decisions require human investigation</span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'provenance' && (
            <div className="space-y-4">
              <div className="glass-card-light rounded-lg p-4">
                <h4 className="font-bold text-white mb-4">Image Provenance</h4>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted text-sm">SHA-256 Hash</span>
                    <button
                      onClick={() => copyToClipboard(result.image.sha256)}
                      className="text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                    >
                      <Copy className="w-4 h-4" />
                      <span className="text-xs">Copy</span>
                    </button>
                  </div>
                  <div className="text-white font-mono text-xs break-all bg-card p-2 rounded">
                    {result.image.sha256}
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-text-muted">Filename:</span>
                      <div className="text-white">{result.image.filename}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Analysis ID:</span>
                      <div className="text-white font-mono text-xs">{result.analysis_id}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Upload Time:</span>
                      <div className="text-white">{new Date(result.created_at).toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">File Format:</span>
                      <div className="text-white">{result.image.format}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Dimensions:</span>
                      <div className="text-white">{result.image.width} × {result.image.height}</div>
                    </div>
                    <div>
                      <span className="text-text-muted">Analysis Duration:</span>
                      <div className="text-white">{result.duration_ms} ms</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="mt-6 glass-card-light rounded-xl p-4 text-center">
          <p className="text-text-muted text-sm">
            <Info className="w-4 h-4 inline mr-2 text-cyan-400" />
            {result.disclaimer}
          </p>
        </div>
      </div>
    </div>
  );
}