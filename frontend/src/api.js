const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep statusText */
    }
    const err = new Error(detail)
    err.status = res.status
    throw err
  }
  return res
}

const json = async (path, options) => (await request(path, options)).json()
const post = (path, body, headers) =>
  json(path, { method: 'POST', body: JSON.stringify(body), headers })

let stationCache = null
export async function getStations() {
  if (!stationCache) stationCache = (await json('/stations')).stations
  return stationCache
}

export const matchGeo = (latitude, longitude) => post('/match-geo', { latitude, longitude })
export const explain = (payload) => post('/explain', payload)
export const forecast = (payload) => post('/forecast/multi-day?days=5', payload)
export const getPerformance = () => json('/metrics/performance')
export const getRecentPredictions = async (limit = 50) =>
  (await json(`/predictions/recent?limit=${limit}`)).predictions
export const subscribe = (email, region, latitude, longitude) =>
  post('/subscribe', { email, region_or_latlon: region, latitude, longitude })

export async function downloadReport(result) {
  const res = await request('/report/from-result', { method: 'POST', body: JSON.stringify(result) })
  return res.blob()
}

export const adminLogin = (username, password) => post('/admin/login', { username, password })
export const adminOverview = (token) =>
  json('/admin/overview', { headers: { Authorization: `Bearer ${token}` } })
