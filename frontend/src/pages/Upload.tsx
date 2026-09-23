import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload as UploadIcon, X, Activity, AlertCircle, CheckCircle, FileImage, HardDrive } from 'lucide-react';
import { api } from '../services/api';
import type { UploadConfig } from '../types';

export default function Upload() {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [config, setConfig] = useState<UploadConfig | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    setConnectionStatus('checking');
    api.getConfig()
      .then((uploadConfig) => {
        if (active) {
          setConfig(uploadConfig);
          setConnectionStatus('connected');
        }
      })
      .catch(() => {
        if (active) {
          setConnectionStatus('disconnected');
          setError('Unable to connect to analysis server. Please ensure the backend is running.');
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFile = async (file: File) => {
    setError(null);
    setSelectedFile(file);
    
    // Create preview
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const analyzeSelectedFile = async () => {
    if (!selectedFile) return;
    
    setError(null);
    setIsUploading(true);

    try {
      const result = await api.analyzeImage(selectedFile);
      navigate(`/results/${result.analysis_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const resetSelection = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setError(null);
  };

  const retryConnection = () => {
    setConnectionStatus('checking');
    setError(null);
    api.getConfig()
      .then((uploadConfig) => {
        setConfig(uploadConfig);
        setConnectionStatus('connected');
      })
      .catch(() => {
        setConnectionStatus('disconnected');
        setError('Still unable to connect to analysis server.');
      });
  };

  return (
    <div className="page-container py-6 animate-fade-in">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 gradient-cyan rounded-2xl mb-6 glow-cyan">
            <UploadIcon className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Upload Claim Image</h1>
          <p className="text-text-muted max-w-2xl mx-auto text-lg">
            Upload a photograph for forensic analysis
          </p>
        </div>

        {/* Connection Status */}
        <div className="mb-6">
          {connectionStatus === 'checking' && (
            <div className="flex items-center justify-center space-x-3 text-sm text-text-muted glass-card rounded-xl p-4">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-cyan-400"></div>
              <span>Connecting to analysis server...</span>
            </div>
          )}
          {connectionStatus === 'connected' && (
            <div className="flex items-center justify-center space-x-3 text-sm text-success glass-card rounded-xl p-4">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Connected to analysis server</span>
            </div>
          )}
          {connectionStatus === 'disconnected' && (
            <div className="flex items-center justify-center space-x-3 text-sm text-danger glass-card rounded-xl p-4">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">Disconnected from analysis server</span>
              <button onClick={retryConnection} className="text-cyan-400 hover:text-cyan-300 underline font-medium ml-4">
                Retry
              </button>
            </div>
          )}
        </div>

        {/* Upload Area */}
        <div
          className={`upload-zone rounded-2xl p-12 text-center transition-all ${
            isDragging ? 'dragging' : ''
          } ${connectionStatus === 'disconnected' ? 'opacity-50 pointer-events-none' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isUploading ? (
            <div className="space-y-6">
              <div className="flex justify-center">
                <div className="relative">
                  <div className="animate-spin rounded-full h-20 w-20 border-4 border-cyan-500/20"></div>
                  <div className="animate-spin rounded-full h-20 w-20 border-4 border-cyan-400 border-t-transparent absolute top-0 left-0"></div>
                </div>
              </div>
              <div className="animate-slide-up">
                <p className="text-xl font-semibold text-white mb-2">Analyzing Image</p>
                <p className="text-text-muted">This may take a few moments...</p>
                <div className="mt-4 w-full max-w-md mx-auto bg-card-light rounded-full h-2">
                  <div className="progress-bar h-2 rounded-full animate-pulse-slow" style={{ width: '60%' }}></div>
                </div>
              </div>
            </div>
          ) : selectedFile && previewUrl ? (
            <div className="space-y-6 animate-slide-up">
              <div className="max-w-md mx-auto">
                <div className="relative rounded-xl overflow-hidden glass-card-light">
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-auto"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
                </div>
              </div>
              
              <div className="glass-card rounded-xl p-6 max-w-md mx-auto">
                <div className="text-left space-y-4">
                  <div className="flex items-center space-x-3 pb-3 border-b border-border">
                    <FileImage className="w-5 h-5 text-cyan-400" />
                    <span className="text-white font-medium truncate flex-1">{selectedFile.name}</span>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="flex items-center space-x-2">
                      <HardDrive className="w-4 h-4 text-text-muted" />
                      <span className="text-text-muted">Size:</span>
                      <span className="text-white font-medium">{(selectedFile.size / 1024 / 1024).toFixed(2)} MB</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Activity className="w-4 h-4 text-text-muted" />
                      <span className="text-text-muted">Type:</span>
                      <span className="text-white font-medium">{selectedFile.type}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex space-x-4 justify-center">
                <button
                  onClick={analyzeSelectedFile}
                  className="btn-primary px-8 py-4 text-white rounded-xl font-medium shadow-lg flex items-center space-x-2"
                >
                  <Activity className="w-5 h-5" />
                  <span>Analyze Image</span>
                </button>
                <button
                  onClick={resetSelection}
                  className="btn-secondary px-8 py-4 text-white rounded-xl font-medium flex items-center space-x-2"
                >
                  <X className="w-5 h-5" />
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="animate-slide-up">
              <div className="mb-8">
                <div className="inline-flex items-center justify-center w-24 h-24 bg-card-light rounded-full mb-6 border border-border">
                  <UploadIcon className="w-12 h-12 text-cyan-400" />
                </div>
              </div>
              <p className="text-2xl font-bold text-white mb-4">
                Drag & drop your image here
              </p>
              <p className="text-text-muted mb-8 text-lg">
                or
              </p>
              <label className="inline-block">
                <span className="btn-primary px-8 py-4 text-white rounded-xl cursor-pointer font-medium shadow-lg inline-flex items-center space-x-2">
                  <UploadIcon className="w-5 h-5" />
                  <span>Choose File</span>
                </span>
                <input
                  type="file"
                  className="hidden"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileInput}
                />
              </label>
              
              {config && (
                <div className="mt-8 flex items-center justify-center space-x-8 text-sm text-text-muted">
                  <div className="flex items-center space-x-2">
                    <FileImage className="w-4 h-4 text-cyan-400" />
                    <span>Formats: {config.allowed_formats.join(', ')}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <HardDrive className="w-4 h-4 text-cyan-400" />
                    <span>Max size: {config.max_file_size_mb} MB</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-6 p-4 glass-card-light rounded-xl text-danger flex items-start space-x-3 animate-fade-in border border-danger/30">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Error</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Security Message */}
        <div className="mt-8 glass-card rounded-xl p-4 text-center">
          <p className="text-text-muted text-sm">
            <Activity className="w-4 h-4 inline mr-2 text-cyan-400" />
            Your analysis is based on the submitted image. All processing is performed securely.
          </p>
        </div>
      </div>
    </div>
  );
}
