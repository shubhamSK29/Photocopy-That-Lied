import { Link } from 'react-router-dom';
import { Shield, AlertTriangle, FileText, Activity, Upload, ArrowRight } from 'lucide-react';

export default function Dashboard() {
  const stats = [
    { label: 'Images Analyzed', value: '128', icon: FileText, color: 'cyan' },
    { label: 'High-Risk Images', value: '24', icon: AlertTriangle, color: 'danger' },
    { label: 'Human Review Required', value: '31', icon: Shield, color: 'warning' },
    { label: 'Backend Status', value: 'Connected', icon: Activity, color: 'success' },
  ];

  return (
    <div className="page-container py-6 animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Forensic Image Analysis</h1>
        <p className="text-text-muted max-w-2xl">
          Analyze insurance claim photographs for manipulation evidence, metadata inconsistencies, and suspicious image-processing patterns.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div key={index} className="glass-card rounded-xl p-6 card-hover">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                  stat.color === 'cyan' ? 'gradient-cyan' :
                  stat.color === 'danger' ? 'gradient-danger' :
                  stat.color === 'warning' ? 'gradient-warning' :
                  'bg-success/20'
                }`}>
                  <Icon className={`w-6 h-6 ${
                    stat.color === 'success' ? 'text-success' : 'text-white'
                  }`} />
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-white">{stat.value}</div>
                  <div className="text-xs text-text-muted">{stat.label}</div>
                </div>
              </div>
              <div className="text-xs text-text-dim">
                * Demo values
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="glass-card rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <Link
              to="/"
              className="flex items-center justify-between p-4 rounded-lg bg-card-light hover:bg-card border border-border hover:border-cyan-500/50 transition-all group"
            >
              <div className="flex items-center space-x-3">
                <Upload className="w-5 h-5 text-cyan-400" />
                <span className="text-white">Upload New Image</span>
              </div>
              <ArrowRight className="w-5 h-5 text-text-muted group-hover:text-cyan-400 transition-colors" />
            </Link>
            <Link
              to="/history"
              className="flex items-center justify-between p-4 rounded-lg bg-card-light hover:bg-card border border-border hover:border-cyan-500/50 transition-all group"
            >
              <div className="flex items-center space-x-3">
                <FileText className="w-5 h-5 text-cyan-400" />
                <span className="text-white">View Analysis History</span>
              </div>
              <ArrowRight className="w-5 h-5 text-text-muted group-hover:text-cyan-400 transition-colors" />
            </Link>
          </div>
        </div>

        <div className="glass-card rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">System Information</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 rounded-lg bg-card-light">
              <span className="text-text-muted">Backend Version</span>
              <span className="text-white font-mono text-sm">v1.0.0</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-card-light">
              <span className="text-text-muted">Analysis Mode</span>
              <span className="text-cyan-400 text-sm">Demo Fallback</span>
            </div>
            <div className="flex justify-between items-center p-3 rounded-lg bg-card-light">
              <span className="text-text-muted">Dataset</span>
              <span className="text-white text-sm">Synthetic/Demo</span>
            </div>
          </div>
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="glass-card rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-6">Analysis Workflow</h2>
        <div className="flex items-center justify-between">
          {[
            { step: 'UPLOAD', icon: Upload, path: '/' },
            { step: 'ANALYZE', icon: Activity, path: '#' },
            { step: 'PROCESS', icon: Shield, path: '#' },
            { step: 'EVIDENCE', icon: AlertTriangle, path: '#' },
            { step: 'RESULTS', icon: FileText, path: '#' },
            { step: 'REVIEW', icon: Shield, path: '#' },
          ].map((item, index) => {
            const Icon = item.icon;
            return (
              <div key={index} className="flex flex-col items-center">
                <Link
                  to={item.path}
                  className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                    item.path !== '#'
                      ? 'gradient-cyan glow-cyan hover:scale-110 cursor-pointer'
                      : 'bg-card-light border border-border'
                  }`}
                >
                  <Icon className={`w-7 h-7 ${item.path !== '#' ? 'text-white' : 'text-text-muted'}`} />
                </Link>
                <span className="text-xs text-text-muted mt-2">{item.step}</span>
                {index < 5 && (
                  <div className="hidden md:block absolute left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 to-transparent top-1/2 transform -translate-y-1/2" style={{ width: '60px', marginLeft: '40px' }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Project Phase */}
      <div className="glass-card rounded-xl p-6 mt-6">
        <h2 className="text-xl font-bold text-white mb-4">Current Project Phase</h2>
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-text-muted">Product Prototype + Forensic Backend Verification</span>
            <span className="text-cyan-400 font-bold">80% Complete</span>
          </div>
          <div className="w-full bg-card-light rounded-full h-2">
            <div className="progress-bar h-2 rounded-full" style={{ width: '80%' }}></div>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-sm font-semibold text-success mb-2">Completed</h3>
            <ul className="space-y-1 text-sm text-text-muted">
              <li className="flex items-center"><span className="text-success mr-2">✓</span> Frontend / UI</li>
              <li className="flex items-center"><span className="text-success mr-2">✓</span> Backend / API integration</li>
              <li className="flex items-center"><span className="text-success mr-2">✓</span> Startup / Deployment</li>
              <li className="flex items-center"><span className="text-success mr-2">✓</span> User workflow</li>
              <li className="flex items-center"><span className="text-success mr-2">✓</span> Results dashboard</li>
              <li className="flex items-center"><span className="text-success mr-2">✓</span> Human-review interface</li>
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-warning mb-2">In Progress / Verification</h3>
            <ul className="space-y-1 text-sm text-text-muted">
              <li className="flex items-center"><span className="text-warning mr-2">⚠</span> Forensic detection pipeline</li>
              <li className="flex items-center"><span className="text-warning mr-2">⚠</span> Dataset and ML training</li>
              <li className="flex items-center"><span className="text-warning mr-2">⚠</span> Natural smartphone-processing calibration</li>
              <li className="flex items-center"><span className="text-warning mr-2">⚠</span> Timestamp forensics</li>
              <li className="flex items-center"><span className="text-warning mr-2">⚠</span> Research evaluation</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}