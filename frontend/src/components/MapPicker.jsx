import { useEffect, useState } from 'react'
import L from 'leaflet'
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import { getStations, subscribe } from '../api'
import { INDIA_BOUNDS, usePredict } from '../PredictContext'
import { Notice } from './ui'

import { ATTRIBUTION, TILES } from '../tiles'

const bounds = [[INDIA_BOUNDS.minLat, INDIA_BOUNDS.minLon], [INDIA_BOUNDS.maxLat, INDIA_BOUNDS.maxLon]]

function pinIcon(hot) {
  return L.divIcon({ className: '', html: `<div class="pin${hot ? ' hot' : ''}"></div>`, iconSize: [0, 0] })
}

function ClickHandler({ onPick }) {
  useMapEvents({
    click(e) {
      const lat = Math.round(e.latlng.lat * 1e4) / 1e4
      const lon = Math.round(e.latlng.lng * 1e4) / 1e4
      const inside = lat >= INDIA_BOUNDS.minLat && lat <= INDIA_BOUNDS.maxLat && lon >= INDIA_BOUNDS.minLon && lon <= INDIA_BOUNDS.maxLon
      if (inside) onPick(lat, lon)
    },
  })
  return null
}

function Recenter({ lat, lon }) {
  const map = useMap()
  useEffect(() => {
    map.panTo([lat, lon], { animate: true })
  }, [lat, lon, map])
  return null
}

function AlertSignup({ matched, loc }) {
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState(null)

  async function submit(e) {
    e.preventDefault()
    if (!email.includes('@')) return setStatus({ kind: 'warn', text: 'Please enter a valid email address.' })
    try {
      await subscribe(email, matched?.matched_station || 'Target region', loc.lat, loc.lon)
      setStatus({ kind: 'ok', text: `Subscribed ${email} to alerts for ${matched?.matched_station || 'this region'}.` })
    } catch (err) {
      setStatus({ kind: 'error', text: `Subscription failed: ${err.message}` })
    }
  }

  return (
    <div style={{ borderTop: '1px solid var(--line-soft)', padding: '4px 20px' }}>
      <button type="button" className="link-btn" aria-expanded={open} onClick={() => setOpen(!open)}>
        Get email alerts for this region
      </button>
      {open && (
        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '4px 0 16px', maxWidth: 360 }}>
          <div className="field">
            <label htmlFor="alert-email">Email address</label>
            <input id="alert-email" className="text-input" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <button type="submit" className="btn">Subscribe</button>
          {status && <Notice kind={status.kind}>{status.text}</Notice>}
        </form>
      )}
    </div>
  )
}

export default function MapPicker() {
  const { loc, matched, result, selectLocation } = usePredict()
  const [stations, setStations] = useState([])
  const [stationError, setStationError] = useState(false)

  useEffect(() => {
    getStations().then(setStations).catch(() => setStationError(true))
  }, [])

  const heavy = result?.prediction === 1

  return (
    <section className="panel" style={{ flex: '1.25 1 440px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-head">
        <h2 className="panel-title">1. Location</h2>
        <span className="coords">{loc.lat.toFixed(4)} N, {loc.lon.toFixed(4)} E</span>
      </div>
      <div className="map-box">
        <MapContainer center={[loc.lat, loc.lon]} zoom={5} minZoom={4} maxZoom={12} maxBounds={bounds} scrollWheelZoom={false}>
          <TileLayer url={TILES} attribution={ATTRIBUTION} />
          {stations.filter((_, i) => i % 2 === 0).map((s) => (
            <CircleMarker key={s.station_name} center={[s.latitude, s.longitude]} radius={3}
              pathOptions={{ color: '#0b6e8a', fillColor: '#0b6e8a', fillOpacity: 0.55, weight: 1 }}>
              <Tooltip>{s.station_name}</Tooltip>
            </CircleMarker>
          ))}
          <Marker position={[loc.lat, loc.lon]} icon={pinIcon(heavy)} />
          <ClickHandler onPick={selectLocation} />
          <Recenter lat={loc.lat} lon={loc.lon} />
        </MapContainer>
        <div className="map-note">Click the map to move the pin</div>
      </div>
      <div className="strip">
        <div><span>Nearest station</span><strong>{matched ? `${matched.matched_station}, ${matched.matched_state}` : '...'}</strong></div>
        <div><span>Distance</span><strong>{matched?.distance_km ?? '-'} km</strong></div>
        <div><span>Elevation</span><strong>{matched?.elevation ?? '-'} m</strong></div>
      </div>
      {stationError && <div style={{ padding: '0 20px 12px' }}><Notice kind="warn">Station markers could not be loaded. The map still works.</Notice></div>}
      <AlertSignup matched={matched} loc={loc} />
    </section>
  )
}
