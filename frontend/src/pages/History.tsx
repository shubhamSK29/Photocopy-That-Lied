import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Calendar, FileText, ArrowRight, AlertCircle, Upload } from 'lucide-react';
import { api } from '../services/api';

interface HistoryItem {
  analysis_id: string;
  created_at: string;
  image: {
    filename: string;
    width: number;
    height: number;
  };
  manipulation_evidence: number;
  risk_band: string;
}

export default function History() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  useEffect(() => {
    api.getConfig()
      .then(() => {
        // Try to fetch history - this might not be implemented yet
        return fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/analyses`);
      })
      .then(res => res.json())
      .then(data => {
        setHistory(data.items || []);
        setLoading(false);
      })
      .catch(() => {
        setError('History feature not available. The backend may not support analysis history.');
        setLoading(false);
      });
  }, []);

  const getRiskCategory = (score: number) => {
    if (score < 30) return 'Low';
    if (score < 70) return 'Medium';
    return 'High';
  };

  const getRiskColor = (category: string) => {
    if (category === 'Low') return 'text-success';
    if (category === 'Medium') return 'text-warning';
    return 'text-danger';
  };

  const getRiskBadge = (category: string) => {
    if (category === 'Low') return 'risk-low';
    if (category === 'Medium') return 'risk-medium';
    return 'risk-high';
  };

  const filteredHistory = history.filter(item => {
    const matchesSearch = item.image.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const riskCategory = getRiskCategory(item.manipulation_evidence);
    const matchesFilter = filterRisk === 'all' || 
                          (filterRisk === 'high' && riskCategory === 'High') ||
                          (filterRisk === 'medium' && riskCategory === 'Medium') ||
                          (filterRisk === 'low' && riskCategory === 'Low');
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="page-container py-6 animate-fade-in">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container py-6 animate-fade-in">
        <div className="glass-card-light rounded-xl p-6 border border-warning/30 max-w-md">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-6 h-6 text-warning" />
            </div>
            <div>
              <h3 className="font-bold text-warning text-lg">History Not Available</h3>
              <p className="text-sm text-text-muted mt-2">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="page-container py-6 animate-fade-in">
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-24 h-24 bg-card-light rounded-full mb-6 border border-border">
            <FileText className="w-12 h-12 text-text-muted" />
          </div>
          <h3 className="text-2xl font-bold text-white mb-3">No Analysis History</h3>
          <p className="text-text-muted mb-8 max-w-md mx-auto">Upload an image to start your first analysis.</p>
          <Link
            to="/"
            className="btn-primary px-8 py-4 text-white rounded-xl font-medium shadow-lg inline-flex items-center space-x-2"
          >
            <Upload className="w-5 h-5" />
            <span>Start New Analysis</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container py-6 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Analysis History</h1>
        <p className="text-text-muted">Previous image forensic analyses</p>
      </div>

      {/* Search and Filter */}
      <div className="glass-card rounded-xl p-4 mb-6">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-muted" />
            <input
              type="text"
              placeholder="Search by filename..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-forensic w-full pl-10 pr-4 py-2 rounded-lg"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-text-muted" />
            <select
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value as any)}
              className="input-forensic px-4 py-2 rounded-lg"
            >
              <option value="all">All Risk Levels</option>
              <option value="high">High Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="low">Low Risk</option>
            </select>
          </div>
        </div>
      </div>

      {/* History Table */}
      <div className="glass-card rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-card-light border-b border-border">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">
                  <div className="flex items-center space-x-2">
                    <Calendar className="w-4 h-4" />
                    <span>Date & Time</span>
                  </div>
                </th>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">
                  <div className="flex items-center space-x-2">
                    <FileText className="w-4 h-4" />
                    <span>File Name</span>
                  </div>
                </th>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">Risk Score</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">Analysis ID</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-text-muted uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredHistory.map((item) => {
                const riskCategory = getRiskCategory(item.manipulation_evidence);
                return (
                  <tr key={item.analysis_id} className="table-row">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
                      {item.image.filename}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`font-bold ${getRiskColor(riskCategory)}`}>
                        {item.manipulation_evidence.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${getRiskBadge(riskCategory)}`}>
                        {riskCategory}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted font-mono">
                      {item.analysis_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <Link
                        to={`/results/${item.analysis_id}`}
                        className="text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center space-x-1"
                      >
                        <span>View</span>
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {filteredHistory.length === 0 && history.length > 0 && (
        <div className="text-center py-8">
          <p className="text-text-muted">No results match your search criteria.</p>
        </div>
      )}
    </div>
  );
}
