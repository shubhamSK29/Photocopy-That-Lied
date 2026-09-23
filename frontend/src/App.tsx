import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Processing from './pages/Processing';
import Results from './pages/Results';
import History from './pages/History';
import About from './pages/About';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        <Route path="/" element={<Layout><Upload /></Layout>} />
        <Route path="/processing/:analysisId" element={<Layout><Processing /></Layout>} />
        <Route path="/results/:analysisId" element={<Layout><Results /></Layout>} />
        <Route path="/history" element={<Layout><History /></Layout>} />
        <Route path="/about" element={<Layout><About /></Layout>} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
