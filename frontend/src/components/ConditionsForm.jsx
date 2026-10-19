import { useState } from 'react'
import { explain } from '../api'
import { MONTHS } from '../format'
import { usePredict } from '../PredictContext'
import { Icon } from './ui'

const PRESETS = [
  { label: 'Mumbai storm', lat: 19.076, lon: 72.8777, rain1: 95, pressure: 998, wind: 32, month: 7 },
  { label: 'Cherrapunji', lat: 25.2986, lon: 91.5822, rain1: 180, pressure: 992, wind: 25, month: 6 },
  { label: 'Delhi dry spell', lat: 28.6139, lon: 77.209, rain1: 0, pressure: 1014, wind: 6, month: 1 },
  { label: 'Chennai monsoon', lat: 13.0827, lon: 80.2707, rain1: 70, pressure: 1001, wind: 28, month: 11 },
]

function NumberField({ id, label, unit, name }) {
  const { form, setField } = usePredict()
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        <input id={id} type="number" inputMode="decimal" step="any" value={form[name]}
          onChange={(e) => setField(name, e.target.value === '' ? '' : Number(e.target.value))} />
        <span className="unit">{unit}</span>
      </div>
    </div>
  )
}

export default function ConditionsForm() {
  const { loc, form, matched, setField, setResult, setError, applyPreset } = usePredict()
  const [more, setMore] = useState(false)
  const [busy, setBusy] = useState(false)
  const [activePreset, setActivePreset] = useState(null)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const n = (v) => Number(v) || 0
      const res = await explain({
        latitude: loc.lat,
        longitude: loc.lon,
        avg_temp: n(form.avgTemp),
        min_temp: n(form.minTemp),
        max_temp: n(form.maxTemp),
        air_pressure: n(form.pressure),
        wind_speed: n(form.wind),
        elevation: n(form.elevation),
        rainfall_lag1: n(form.rain1),
        rainfall_lag2: n(form.rain2),
        rainfall_roll3_sum: n(form.rain3),
        rainfall_roll7_sum: n(form.rain7),
        month: n(form.month),
      })
      setResult(res)
      setTimeout(() => document.getElementById('result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (err) {
      setResult(null)
      setError(`The prediction could not be completed: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" style={{ flex: '1 1 380px' }}>
      <div className="panel-head"><h2 className="panel-title">2. Conditions</h2></div>
      <form className="panel-body" onSubmit={submit}>
        <div>
          <div className="hint" style={{ marginBottom: 8 }}>Start from a known scenario, or enter your own values.</div>
          <div className="chips">
            {PRESETS.map((p) => (
              <button key={p.label} type="button" className={`chip${activePreset === p.label ? ' on' : ''}`}
                onClick={() => { setActivePreset(p.label); applyPreset(p) }}>
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div className="fields">
          <NumberField id="f-rain1" name="rain1" label="Rain yesterday" unit="mm" />
          <NumberField id="f-rain7" name="rain7" label="Rain, last 7 days" unit="mm" />
          <NumberField id="f-pressure" name="pressure" label="Surface pressure" unit="hPa" />
          <NumberField id="f-wind" name="wind" label="Wind speed" unit="km/h" />
          <NumberField id="f-temp" name="avgTemp" label="Average temperature" unit="°C" />
          <div className="field">
            <label htmlFor="f-month">Month</label>
            <select id="f-month" className="select" value={form.month} onChange={(e) => setField('month', Number(e.target.value))}>
              {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
            </select>
          </div>
        </div>

        <button type="button" className="link-btn" aria-expanded={more} onClick={() => setMore(!more)}>
          <Icon name="chevron" size={14} />
          {more ? 'Fewer inputs' : 'More inputs (elevation, min and max temperature)'}
        </button>
        {more && (
          <div className="fields">
            <NumberField id="f-min" name="minTemp" label="Minimum temperature" unit="°C" />
            <NumberField id="f-max" name="maxTemp" label="Maximum temperature" unit="°C" />
            <NumberField id="f-elev" name="elevation" label="Elevation" unit="m" />
            <NumberField id="f-rain2" name="rain2" label="Rain 2 days ago" unit="mm" />
            <NumberField id="f-rain3" name="rain3" label="Rain, last 3 days" unit="mm" />
          </div>
        )}

        <button type="submit" className="btn btn-primary" disabled={busy || !matched}>
          {busy ? 'Running the model...' : 'Run prediction'}
        </button>
      </form>
    </section>
  )
}
