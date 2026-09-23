import { Shield, AlertTriangle, Activity, FileText, ArrowDown, CheckCircle, Code, Database } from 'lucide-react';

export default function About() {
  return (
    <div className="page-container py-6 animate-fade-in">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-24 h-24 gradient-cyan rounded-2xl mb-6 glow-cyan">
            <Shield className="w-12 h-12 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Photocopy That Lied</h1>
          <p className="text-text-muted text-lg">AI-Powered Forensic Analysis for Insurance Claim Images</p>
        </div>

        {/* Problem & Solution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="glass-card rounded-xl p-6 animate-slide-up">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
              <AlertTriangle className="w-6 h-6 text-warning" />
              <span>Problem</span>
            </h2>
            <p className="text-text-muted leading-relaxed">
              Insurance claim photographs may be edited, recompressed, or contain misleading metadata. Traditional manual review is time-consuming and inconsistent.
            </p>
          </div>

          <div className="glass-card rounded-xl p-6 animate-slide-up">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
              <Activity className="w-6 h-6 text-cyan-400" />
              <span>Solution</span>
            </h2>
            <p className="text-text-muted leading-relaxed">
              The system analyzes multiple forensic signals and combines them into an evidence-based result for human reviewers, providing consistent and scalable screening.
            </p>
          </div>
        </div>

        {/* Detection Pipeline */}
        <div className="glass-card rounded-xl p-6 mb-8 animate-slide-up">
          <h2 className="text-xl font-bold text-white mb-6">Detection Pipeline</h2>
          <div className="flex flex-col items-center space-y-4">
            {[
              { step: 'Image Upload', icon: FileText },
              { step: 'Validation', icon: CheckCircle },
              { step: 'Metadata Extraction', icon: Database },
              { step: 'Copy-Move Analysis', icon: Activity },
              { step: 'Local Inconsistency', icon: AlertTriangle },
              { step: 'Compression / Resampling', icon: Activity },
              { step: 'Natural Smartphone Processing', icon: Shield },
              { step: 'Spatial Agreement', icon: Activity },
              { step: 'Evidence Fusion', icon: FileText },
              { step: 'Reviewer Report', icon: Shield },
            ].map((item, index) => (
              <div key={index} className="flex items-center space-x-4 w-full">
                <div className="w-10 h-10 gradient-cyan rounded-lg flex items-center justify-center flex-shrink-0">
                  <item.icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-white font-medium">{item.step}</span>
                {index < 9 && <ArrowDown className="w-5 h-5 text-text-muted flex-shrink-0" />}
              </div>
            ))}
          </div>
        </div>

        {/* Human-in-the-Loop */}
        <div className="glass-card-light rounded-xl p-6 mb-8 border border-warning/30 animate-slide-up">
          <h2 className="text-xl font-bold text-warning mb-4 flex items-center space-x-2">
            <Shield className="w-6 h-6" />
            <span>Human-in-the-Loop</span>
          </h2>
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-6 h-6 text-warning" />
            </div>
            <div>
              <p className="text-text-muted leading-relaxed mb-4">
                The system supports investigators. It does not automatically approve or reject insurance claims. All forensic evidence requires human interpretation and context.
              </p>
              <div className="bg-warning/10 rounded-lg p-4 border border-warning/30">
                <p className="text-warning font-medium text-sm">
                  This system does NOT determine fraud, establish claim validity, or automatically reject insurance claims.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* What It Reports */}
        <div className="glass-card rounded-xl p-6 mb-8 animate-slide-up">
          <h2 className="text-xl font-bold text-white mb-4">What It Reports</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { label: 'Manipulation Evidence (0–100)', desc: 'How much manipulation evidence was found under tested conditions' },
              { label: 'Data Coverage (0–100)', desc: 'How well the submitted image fits tested conditions' },
              { label: 'Risk Band', desc: 'Categorization as low risk, review required, or high-priority review' },
              { label: 'Detector Status', desc: 'Individual forensic detector results (detected, not detected, insufficient evidence)' },
              { label: 'Heatmaps/Regions', desc: 'Approximate forensic signals, not pixel-perfect proof of manipulation' },
              { label: 'Timestamp Integrity', desc: 'EXIF and visible timestamp analysis (never authenticated)' },
            ].map((item, index) => (
              <div key={index} className="glass-card-light rounded-lg p-4">
                <h3 className="font-bold text-white mb-2">{item.label}</h3>
                <p className="text-text-muted text-sm">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Important Limitations */}
        <div className="glass-card-light rounded-xl p-6 mb-8 border border-warning/30 animate-slide-up">
          <h2 className="text-xl font-bold text-warning mb-4 flex items-center space-x-2">
            <AlertTriangle className="w-6 h-6" />
            <span>Important Limitations</span>
          </h2>
          <ul className="space-y-3 text-sm text-text-muted">
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Missing EXIF metadata does NOT prove manipulation</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Compression artifacts do NOT prove manipulation</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Resizing/recompression can create forensic artifacts</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Normal smartphone processing (sharpening, denoising, HDR) can create forensic artifacts</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Timestamp verification is impossible when no usable timestamp evidence remains</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Heatmaps are approximate forensic signals, not pixel-perfect proof of manipulation</span>
            </li>
            <li className="flex items-start space-x-3">
              <span className="text-warning mt-1">•</span>
              <span>Low data coverage reduces confidence in results</span>
            </li>
          </ul>
        </div>

        {/* System Information */}
        <div className="glass-card rounded-xl p-6 animate-slide-up">
          <h2 className="text-xl font-bold text-white mb-4">System Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-card-light rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Code className="w-4 h-4 text-cyan-400" />
                <span className="text-text-muted text-sm">Frontend</span>
              </div>
              <div className="text-white font-medium">React + Vite + TypeScript</div>
            </div>
            <div className="glass-card-light rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Database className="w-4 h-4 text-cyan-400" />
                <span className="text-text-muted text-sm">Backend</span>
              </div>
              <div className="text-white font-medium">FastAPI + Python</div>
            </div>
            <div className="glass-card-light rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="text-text-muted text-sm">Analysis Mode</span>
              </div>
              <div className="text-white font-medium">Demo Fallback (until trained model available)</div>
            </div>
            <div className="glass-card-light rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                <span className="text-text-muted text-sm">Dataset</span>
              </div>
              <div className="text-white font-medium">Synthetic/demo only</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
