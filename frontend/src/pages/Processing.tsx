import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Activity, CheckCircle, Shield, FileText, AlertTriangle } from 'lucide-react';

export default function Processing() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);

  const steps = [
    { name: 'Validating file', icon: FileText },
    { name: 'Calculating SHA-256', icon: Shield },
    { name: 'Extracting metadata', icon: FileText },
    { name: 'Running forensic detectors', icon: Activity },
    { name: 'Comparing suspicious regions', icon: AlertTriangle },
    { name: 'Evaluating natural image-processing artifacts', icon: Activity },
    { name: 'Fusing forensic evidence', icon: Shield },
    { name: 'Preparing reviewer report', icon: FileText },
  ];

  useEffect(() => {
    let stepIndex = 0;
    const interval = setInterval(() => {
      if (stepIndex < steps.length) {
        setCurrentStep(stepIndex);
        setProgress(((stepIndex + 1) / steps.length) * 100);
        stepIndex++;
      } else {
        clearInterval(interval);
        // Navigate to results when done
        if (analysisId) {
          navigate(`/results/${analysisId}`);
        }
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [analysisId, navigate]);

  return (
    <div className="page-container py-6 animate-fade-in">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-24 h-24 gradient-cyan rounded-full mb-6 glow-cyan">
            <Activity className="w-12 h-12 text-white animate-spin-slow" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-4">Analyzing Image...</h1>
          <p className="text-text-muted text-lg">Running forensic analysis pipeline</p>
        </div>

        {/* Progress Bar */}
        <div className="glass-card rounded-xl p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <span className="text-text-muted">Progress</span>
            <span className="text-cyan-400 font-bold">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-card-light rounded-full h-3">
            <div 
              className="progress-bar h-3 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* Processing Pipeline */}
        <div className="glass-card rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-6">Processing Pipeline</h2>
          <div className="space-y-4">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isCompleted = index < currentStep;
              const isCurrent = index === currentStep;

              return (
                <div
                  key={index}
                  className={`flex items-center space-x-4 p-4 rounded-lg transition-all ${
                    isCompleted ? 'bg-success/10 border border-success/30' :
                    isCurrent ? 'bg-cyan-500/10 border border-cyan-500/30' :
                    'bg-card-light border border-border'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    isCompleted ? 'bg-success' :
                    isCurrent ? 'gradient-cyan glow-cyan' :
                    'bg-card-light border border-border'
                  }`}>
                    {isCompleted ? (
                      <CheckCircle className="w-5 h-5 text-white" />
                    ) : isCurrent ? (
                      <Icon className="w-5 h-5 text-white animate-pulse" />
                    ) : (
                      <Icon className="w-5 h-5 text-text-muted" />
                    )}
                  </div>
                  <div className="flex-1">
                    <span className={`font-medium ${
                      isCompleted ? 'text-success' :
                      isCurrent ? 'text-white' :
                      'text-text-muted'
                    }`}>
                      {step.name}
                    </span>
                  </div>
                  {isCompleted && (
                    <CheckCircle className="w-5 h-5 text-success" />
                  )}
                  {isCurrent && (
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-cyan-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Info Message */}
        <div className="mt-8 glass-card rounded-xl p-4 text-center">
          <p className="text-text-muted text-sm">
            <Activity className="w-4 h-4 inline mr-2 text-cyan-400" />
            This may take a few moments depending on image size and complexity.
          </p>
        </div>
      </div>
    </div>
  );
}