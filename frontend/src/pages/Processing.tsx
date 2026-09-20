import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';

interface ProcessingStep {
  name: string;
  status: 'pending' | 'complete' | 'error';
}

const STEPS: ProcessingStep[] = [
  { name: 'Image validated', status: 'pending' },
  { name: 'File fingerprint generated', status: 'pending' },
  { name: 'Metadata analyzed', status: 'pending' },
  { name: 'Copy-move analysis', status: 'pending' },
  { name: 'Local anomaly analysis', status: 'pending' },
  { name: 'Compression analysis', status: 'pending' },
  { name: 'Natural-processing comparison', status: 'pending' },
  { name: 'Evidence fusion', status: 'pending' },
  { name: 'Report generated', status: 'pending' },
];

export default function Processing() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const [steps, setSteps] = useState<ProcessingStep[]>(STEPS);

  useEffect(() => {
    if (!analysisId) return;

    let stepIndex = 0;
    const interval = setInterval(() => {
      if (stepIndex < steps.length) {
        setSteps((prev) => {
          const updated = [...prev];
          updated[stepIndex] = { ...updated[stepIndex], status: 'complete' as const };
          return updated;
        });
        stepIndex++;
      } else {
        clearInterval(interval);
        // Try to fetch the result
        api.getAnalysis(analysisId)
          .then(() => {
            navigate(`/results/${analysisId}`);
          })
          .catch(() => {
            // If not ready, continue polling
          });
      }
    }, 800);

    // Also poll the API
    const pollInterval = setInterval(async () => {
      try {
        await api.getAnalysis(analysisId);
        clearInterval(pollInterval);
        clearInterval(interval);
        navigate(`/results/${analysisId}`);
      } catch {
        // Not ready yet
      }
    }, 2000);

    return () => {
      clearInterval(interval);
      clearInterval(pollInterval);
    };
  }, [analysisId, navigate, steps.length]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-8">
      <div className="max-w-2xl w-full">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-900">
          Analyzing Image
        </h1>

        <div className="bg-white rounded-lg shadow-sm p-8">
          {steps.map((step, index) => (
            <div key={index} className="flex items-center mb-4 last:mb-0">
              <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center">
                {step.status === 'complete' ? (
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />
                )}
              </div>
              <span className={`ml-3 ${step.status === 'complete' ? 'text-gray-900' : 'text-gray-400'}`}>
                {step.name}
              </span>
            </div>
          ))}
        </div>

      </div>
    </div>
  );
}
