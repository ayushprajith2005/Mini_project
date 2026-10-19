import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { PredictProvider } from './PredictContext'
import Predict from './pages/Predict'
import Log from './pages/Log'
import Performance from './pages/Performance'
import About from './pages/About'
import Admin from './pages/Admin'

export default function App() {
  return (
    <PredictProvider>
      <div className="shell">
        <Sidebar />
        <main className="content">
          <div className="container">
            <Routes>
              <Route path="/" element={<Predict />} />
              <Route path="/log" element={<Log />} />
              <Route path="/performance" element={<Performance />} />
              <Route path="/about" element={<About />} />
              <Route path="/admin" element={<Admin />} />
              <Route path="*" element={<Predict />} />
            </Routes>
          </div>
        </main>
      </div>
    </PredictProvider>
  )
}
