import { Activity } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  showLiveBadge?: boolean;
}

export default function Header({ title, subtitle, showLiveBadge = true }: HeaderProps) {
  return (
    <div className="border-b border-border bg-card-light">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">{title}</h1>
            {subtitle && (
              <p className="text-sm text-text-muted">{subtitle}</p>
            )}
          </div>
          
          {showLiveBadge && (
            <div className="flex items-center space-x-4">
              <div className="status-live px-4 py-2 rounded-full flex items-center space-x-2">
                <div className="w-2 h-2 bg-success rounded-full animate-pulse"></div>
                <span className="text-sm font-semibold">LIVE DEMO</span>
              </div>
              <div className="hidden md:flex items-center space-x-2 text-xs text-text-muted">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Detect Manipulation • Verify Authenticity • Support Human Review</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}