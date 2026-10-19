import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { adminLogin, adminOverview } from '../api'
import { Notice, PageHeader } from '../components/ui'
import { formatWhen } from '../format'
import { ATTRIBUTION, TILES } from '../tiles'

const TOKEN_KEY = 'rx_admin_token'
const getToken = () => { try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null } }
const setToken = (t) => { try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* private mode */ } }

function Login({ onLogin }) {
  const [user, setUser] = useState('')
  const [pass, setPass] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const { token } = await adminLogin(user, pass)
      setToken(token)
      onLogin(token)
    } catch (err) {
      setError(err.status === 401 ? 'Invalid credentials.' : `Could not log in: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="panel login" onSubmit={submit}>
      <p className="hint">Restricted to administrators.</p>
      <div className="field">
        <label htmlFor="adm-user">Username</label>
        <input id="adm-user" className="text-input" autoComplete="username" value={user} onChange={(e) => setUser(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="adm-pass">Password</label>
        <input id="adm-pass" className="text-input" type="password" autoComplete="current-password" value={pass} onChange={(e) => setPass(e.target.value)} />
      </div>
      {error && <Notice kind="error">{error}</Notice>}
      <button type="submit" className="btn btn-primary" disabled={busy}>{busy ? 'Logging in...' : 'Log in'}</button>
    </form>
  )
}

function Overview({ token, onLogout }) {
  const [state, setState] = useState({ data: null, error: '' })

  useEffect(() => {
    adminOverview(token)
      .then((data) => setState({ data, error: '' }))
      .catch((e) => {
        if (e.status === 401) onLogout()
        else setState({ data: null, error: e.message })
      })
  }, [token, onLogout])

  if (state.error) return <Notice kind="error">Could not load stats: {state.error}</Notice>
  if (!state.data) return <p className="hint">Loading...</p>

  const { stats, predictions, alerts } = state.data
  const counts = predictions.reduce((acc, p) => ({ ...acc, [p.risk_level]: (acc[p.risk_level] || 0) + 1 }), {})
  const peak = Math.max(...Object.values(counts), 1)
  const located = predictions.filter((p) => p.latitude != null && p.longitude != null)
  const alertCols = alerts[0] ? Object.keys(alerts[0]) : []

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button type="button" className="btn" onClick={onLogout}>Log out</button>
      </div>
      <div className="stat-grid">
        {[
          ['Predictions made', stats.total_predictions_logged],
          ['Heavy rain events', stats.heavy_rain_events_logged],
          ['Active subscriptions', stats.active_subscriptions],
          ['Alerts sent', stats.alerts_sent_count],
        ].map(([l, v]) => (
          <div className="panel stat" key={l}><div className="l">{l}</div><div className="v">{v ?? 0}</div></div>
        ))}
      </div>

      {predictions.length > 0 && (
        <div className="row">
          <section className="panel panel-body bars" style={{ flex: '1 1 360px' }}>
            <h2 className="panel-title">Risk level distribution</h2>
            {Object.entries(counts).map(([level, n]) => (
              <div className="factor" key={level}>
                <div className="name">{level}</div>
                <div className="track"><div style={{ width: `${(n / peak) * 100}%` }} /></div>
                <div className="val">{n}</div>
              </div>
            ))}
          </section>
          <section className="panel" style={{ flex: '1 1 360px', overflow: 'hidden' }}>
            <div className="panel-head"><h2 className="panel-title">Most queried regions</h2></div>
            <div className="map-box" style={{ height: 300 }}>
              <MapContainer center={[20.6, 78.9]} zoom={4} scrollWheelZoom={false}>
                <TileLayer url={TILES} attribution={ATTRIBUTION} />
                {located.map((p) => (
                  <CircleMarker key={p.id} center={[p.latitude, p.longitude]} radius={5}
                    pathOptions={{ color: p.prediction === 1 ? '#b4400f' : '#0b6e8a', fillOpacity: 0.6 }}>
                    <Tooltip>{p.matched_region}: {p.risk_level} ({formatWhen(p.timestamp)})</Tooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            </div>
          </section>
        </div>
      )}

      {alerts.length > 0 && (
        <section className="panel panel-body">
          <h2 className="panel-title">Alerts sent</h2>
          <div className="table-wrap">
            <table className="table">
              <thead><tr>{alertCols.map((c) => <th key={c}>{c.replace(/_/g, ' ')}</th>)}</tr></thead>
              <tbody>{alerts.map((a, i) => <tr key={a.id ?? i}>{alertCols.map((c) => <td key={c}>{String(a[c] ?? '')}</td>)}</tr>)}</tbody>
            </table>
          </div>
        </section>
      )}
    </>
  )
}

export default function Admin() {
  const [token, setTokenState] = useState(getToken)
  const logout = () => { setToken(null); setTokenState(null) }

  return (
    <>
      <PageHeader title="Admin" subtitle="Usage and alert activity across the app." />
      {token ? <Overview token={token} onLogout={logout} /> : <Login onLogin={setTokenState} />}
    </>
  )
}
