import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { matchGeo } from './api'

const Ctx = createContext(null)
export const usePredict = () => useContext(Ctx)

export const INDIA_BOUNDS = { minLat: 6, maxLat: 38, minLon: 68, maxLon: 98 }

const DEFAULT_FORM = {
  rain1: 5, rain2: 2.5, rain3: 7.5, rain7: 12.5,
  pressure: 1008, wind: 10, avgTemp: 28, minTemp: 23.5, maxTemp: 33, elevation: 100, month: 7,
}

// Station data arrives with long decimals; show values the way a person would type them.
const round = (v, fallback, digits = 1) => (v == null ? fallback : Math.round(v * 10 ** digits) / 10 ** digits)

// Rain history defaults follow yesterday's rain unless the user has edited them.
function withDerivedRain(form, rain1, touched) {
  const next = { ...form, rain1 }
  if (!touched.has('rain2')) next.rain2 = rain1 * 0.5
  if (!touched.has('rain3')) next.rain3 = rain1 + next.rain2
  if (!touched.has('rain7')) next.rain7 = rain1 * 2.5
  return next
}

// Keeps the Predict screen's state alive while the user visits other screens.
export function PredictProvider({ children }) {
  const [loc, setLoc] = useState({ lat: 19.076, lon: 72.8777 })
  const [matched, setMatched] = useState(null)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const touched = useRef(new Set())

  const applyMatch = useCallback((m) => {
    setMatched(m)
    setForm((f) => ({
      ...f,
      pressure: round(m.air_pressure, f.pressure),
      wind: round(m.wind_speed, f.wind),
      avgTemp: round(m.avg_temp, f.avgTemp),
      minTemp: round(m.min_temp, f.minTemp),
      maxTemp: round(m.max_temp, f.maxTemp),
      elevation: round(m.elevation, f.elevation, 0),
    }))
  }, [])

  const selectLocation = useCallback(async (lat, lon) => {
    setLoc({ lat, lon })
    setResult(null)
    setError('')
    try {
      applyMatch(await matchGeo(lat, lon))
    } catch (e) {
      setError(`Could not look up the nearest station: ${e.message}`)
    }
  }, [applyMatch])

  const applyPreset = useCallback(async (p) => {
    touched.current = new Set()
    setLoc({ lat: p.lat, lon: p.lon })
    setResult(null)
    setError('')
    try {
      const m = await matchGeo(p.lat, p.lon)
      setMatched(m)
      setForm((f) => withDerivedRain({
        ...f,
        avgTemp: round(m.avg_temp, f.avgTemp),
        minTemp: round(m.min_temp, f.minTemp),
        maxTemp: round(m.max_temp, f.maxTemp),
        elevation: round(m.elevation, f.elevation, 0),
        pressure: p.pressure,
        wind: p.wind,
        month: p.month,
      }, p.rain1, touched.current))
    } catch (e) {
      setError(`Could not look up the nearest station: ${e.message}`)
    }
  }, [])

  const setField = useCallback((key, value) => {
    setForm((f) => {
      if (key === 'rain1') return withDerivedRain(f, value, touched.current)
      if (['rain2', 'rain3', 'rain7'].includes(key)) touched.current.add(key)
      return { ...f, [key]: value }
    })
  }, [])

  useEffect(() => {
    if (!matched) selectLocation(loc.lat, loc.lon)
    // first load only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const value = useMemo(
    () => ({ loc, matched, form, result, error, setResult, setError, selectLocation, applyPreset, setField }),
    [loc, matched, form, result, error, selectLocation, applyPreset, setField],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
