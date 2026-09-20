import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Upload from './pages/Upload';
import Processing from './pages/Processing';
import Results from './pages/Results';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/processing/:analysisId" element={<Processing />} />
        <Route path="/results/:analysisId" element={<Results />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
