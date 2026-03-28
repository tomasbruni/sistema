import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { BASE_URL } from '../api/api.js'
import './AuthPage.css'


export default function AuthPage() {
  const { login, expirada } = useAuth()
  const navigate  = useNavigate()

  const [usuario,  setUsuario]  = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState(null)
  const [loading,  setLoading]  = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      // El endpoint /auth/token espera form-urlencoded (OAuth2PasswordRequestForm)
      const body = new URLSearchParams()
      body.append('username', usuario)
      body.append('password', password)

      const res = await fetch(`${BASE_URL}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Credenciales incorrectas')
      }

      const datos = await res.json()
      login(datos)          // guarda token + nombre + rol en el context/localStorage
      navigate('/')   // redirige al inicio de la app
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h1 className="auth-title">CELULAR STORE</h1>
        <p className="auth-subtitle">Ingresá tus credenciales para continuar</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-group">
            <label htmlFor="usuario">Usuario</label>
            <input
              id="usuario"
              type="text"
              value={usuario}
              onChange={e => setUsuario(e.target.value)}
              placeholder="Tu nombre de usuario"
              required
              autoFocus
            />
          </div>

          <div className="auth-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <p className="auth-error">{error}</p>}
          {expirada && <p className="auth-error">{expirada}</p>}

          <button type="submit" className="auth-btn" disabled={loading}>
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  )
}