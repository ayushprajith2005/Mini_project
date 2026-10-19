export const ALERT_THRESHOLD = 0.35

export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const LABELS = {
  rainfall_lag1: 'Rain yesterday',
  rainfall_lag2: 'Rain 2 days ago',
  rainfall_roll3_sum: 'Rain, last 3 days',
  rainfall_roll7_sum: 'Rain, last 7 days',
  air_pressure: 'Surface pressure',
  wind_speed: 'Wind speed',
  avg_temp: 'Average temperature',
  min_temp: 'Minimum temperature',
  max_temp: 'Maximum temperature',
  elevation: 'Elevation',
  month: 'Month',
  latitude: 'Latitude',
  longitude: 'Longitude',
  day_of_year_sin: 'Time of year',
  day_of_year_cos: 'Time of year',
}

const UNITS = {
  rainfall_lag1: 'mm', rainfall_lag2: 'mm', rainfall_roll3_sum: 'mm', rainfall_roll7_sum: 'mm',
  air_pressure: 'hPa', wind_speed: 'km/h', avg_temp: '°C', min_temp: '°C', max_temp: '°C', elevation: 'm',
}

export function featureLabel(name) {
  if (LABELS[name]) return LABELS[name]
  const text = String(name).replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// "VERY HEAVY / EXTREME RISK" -> "Very heavy / extreme risk"
export function sentence(text) {
  const s = String(text ?? '').toLowerCase()
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// Swap raw feature names inside free text (LIME rules, comparison notes) for readable ones.
export function humanize(text) {
  return String(text ?? '').replace(/[a-z]+(?:_[a-z0-9]+)+/g, (name) => LABELS[name] ?? name.replace(/_/g, ' '))
}

export function featureReading(name, value) {
  if (name === 'month') return MONTHS[Number(value) - 1]?.slice(0, 3) ?? String(value)
  const n = Number(value)
  if (Number.isNaN(n)) return String(value)
  const text = String(Math.round(n * 100) / 100)
  return UNITS[name] ? `${text} ${UNITS[name]}` : text
}

export function riskTone(prob) {
  if (prob >= ALERT_THRESHOLD) return { bg: '#FBE3D6', fg: '#9A3412' }
  if (prob >= 0.15) return { bg: '#FFF0CC', fg: '#7A5200' }
  return { bg: '#DDF0E4', fg: '#1E6B3A' }
}

export const signed = (v, digits = 2) => `${v > 0 ? '+' : '−'}${Math.abs(v).toFixed(digits)}`
export const percent = (p, digits = 0) => `${(p * 100).toFixed(digits)}%`

export function formatWhen(ts) {
  if (!ts) return ''
  const d = new Date(String(ts).includes('Z') || String(ts).includes('+') ? ts : `${ts}Z`)
  if (Number.isNaN(d.getTime())) return String(ts)
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
