import { useEffect } from 'react'
import PropTypes from 'prop-types'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/useAuthStore'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ChatPage from './pages/ChatPage'
import DevChatPage from './pages/DevChatPage'

function ProtectedRoute({ children }) {
  const { user, isInitialized } = useAuthStore()
  if (!isInitialized) return <div className="flex h-screen items-center justify-center text-tsmc-blue">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

function PublicRoute({ children }) {
  const { user, isInitialized } = useAuthStore()
  if (!isInitialized) return <div className="flex h-screen items-center justify-center text-tsmc-blue">Loading...</div>
  if (user) return <Navigate to="/chat" replace />
  return children
}

ProtectedRoute.propTypes = {
  children: PropTypes.node.isRequired,
}

PublicRoute.propTypes = {
  children: PropTypes.node.isRequired,
}

export default function App() {
  const initAuth = useAuthStore((s) => s.initAuth)
  const isInitialized = useAuthStore((s) => s.isInitialized)

  useEffect(() => {
    initAuth()
  }, [initAuth])

  if (!isInitialized) {
    return <div className="flex h-screen items-center justify-center text-tsmc-blue">Loading...</div>
  }

  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />
      {import.meta.env.DEV && <Route path="/dev/chat" element={<DevChatPage />} />}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
