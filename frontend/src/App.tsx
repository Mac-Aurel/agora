import { Routes, Route } from 'react-router-dom'

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <div className="flex min-h-screen items-center justify-center bg-gray-50">
            <h1 className="text-4xl font-bold text-gray-900">Agora</h1>
          </div>
        }
      />
    </Routes>
  )
}
