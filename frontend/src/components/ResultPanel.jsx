import { useEffect, useState } from 'react'
import { downloadReport, forecast } from '../api'
import { ALERT_THRESHOLD, featureLabel, featureReading, humanize, percent, riskTone, sentence, signed } from '../format'
import { usePredict } from '../PredictContext'
import { FactorChart, Icon, Notice, RiskBadge } from './ui'

function Verdict({ res }) {
  const prob = res.probability ?? 0
  const { fg } = riskTone(prob)
  const mark = ALERT_THRESHOLD * 100
  const impact = res.impact_estimation

  return (
    <div className="row">
      <div className="panel verdict" style={{ flex: '1.4 1 460px' }}>
        <div className="big">
          <div className="pct" aria-label={`${(prob * 100).toFixed(0)} percent`}>{(prob * 100).toFixed(0)}<small>%</small></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-start' }}>
            <RiskBadge label={sentence(res.risk_level)} prob={prob} />
            <span className="hint">Chance of heavy rain in the next 24 hours</span>
          </div>
        </div>
        <div>
          <div className="bar" role="img" aria-label={`Probability ${percent(prob)}, alert threshold ${mark}%`}>
            <div className="bar-fill" style={{ width: `${Math.min(prob, 1) * 100}%`, background: prob >= ALERT_THRESHOLD ? fg : 'var(--accent)' }} />
            <div className="bar-mark" style={{ left: `${mark}%` }} />
          </div>
          <div className="bar-labels">
            <span style={{ left: 0 }}>0%</span>
            <span style={{ left: `${mark}%`, transform: 'translateX(-50%)', color: 'var(--ink)' }}>Alert threshold {mark}%</span>
            <span style={{ right: 0 }}>100%</span>
          </div>
        </div>
        {res.plain_language_summary && <p className="summary">{res.plain_language_summary}</p>}
      </div>

      <div className="panel verdict" style={{ flex: '1 1 300px', gap: 14 }}>
        <h3 className="panel-title" style={{ fontSize: 15 }}>{impact ? 'What it could affect' : 'Closest station'}</h3>
        {impact ? (
          <>
            <dl className="dl">
              <dt>State</dt><dd>{impact.state}</dd>
              <dt>Population</dt><dd>{sentence(impact.density_category)}, about {impact.population_density_sq_km} people per km²</dd>
              <dt>Impact</dt><dd style={{ fontWeight: 600 }}>{sentence(impact.overall_impact_label)}</dd>
            </dl>
            <div className="action"><span>Suggested action</span>{impact.recommendation}</div>
          </>
        ) : (
          <dl className="dl">
            <dt>Region</dt><dd>{res.matched_region}</dd>
            <dt>Distance</dt><dd>{res.distance_km} km</dd>
          </dl>
        )}
      </div>
    </div>
  )
}

function Compare({ res }) {
  const shap = (res.shap_explanation || []).slice(0, 6)
  const lime = (res.lime_explanation || []).slice(0, 6)
  const note = res.shap_lime_comparison?.comparison_note
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <p className="hint" style={{ maxWidth: 720, fontSize: 14 }}>
        Two independent methods explain the same prediction. SHAP scores how much each input pushed the result.
        LIME fits a few simple rules around this one case. When they point the same way, the explanation is easier to trust.
      </p>
      {note && <Notice kind="ok">{humanize(note)}</Notice>}
      <div className="row" style={{ gap: 24 }}>
        <div style={{ flex: '1 1 380px' }}>
          <h4 style={{ fontSize: 14, margin: '0 0 10px' }}>SHAP: top drivers</h4>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Factor</th><th className="num">Reading</th><th className="num">Effect</th></tr></thead>
              <tbody>
                {shap.map((r) => (
                  <tr key={r.feature}>
                    <td>{featureLabel(r.feature)}</td>
                    <td className="num muted">{featureReading(r.feature, r.value)}</td>
                    <td className={`num ${r.shap_value > 0 ? 'hot' : 'cool'}`}>{signed(r.shap_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{ flex: '1 1 380px' }}>
          <h4 style={{ fontSize: 14, margin: '0 0 10px' }}>LIME: local rules</h4>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Rule that applies here</th><th className="num">Weight</th></tr></thead>
              <tbody>
                {lime.map((r) => (
                  <tr key={r.rule}>
                    <td>{humanize(r.rule)}</td>
                    <td className={`num ${r.weight > 0 ? 'hot' : 'cool'}`}>{signed(r.weight)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

function OutlookChart({ days }) {
  const W = 360, H = 190, left = 22, right = 22, top = 28, bottom = 36
  const peak = Math.max(...days.map((d) => d.probability), ALERT_THRESHOLD)
  const max = Math.min(1, Math.ceil((peak + 0.1) * 10) / 10)
  const x = (i) => left + (i * (W - left - right)) / Math.max(days.length - 1, 1)
  const y = (p) => H - bottom - (p / max) * (H - bottom - top)
  const points = days.map((d, i) => `${x(i)},${y(d.probability)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Five-day heavy rain probability against the alert threshold" style={{ display: 'block', maxWidth: 560 }}>
      <line x1={left} x2={W - right} y1={y(ALERT_THRESHOLD)} y2={y(ALERT_THRESHOLD)} stroke="#14232a" strokeWidth="1.5" strokeDasharray="5 4" />
      <text x={W - right} y={y(ALERT_THRESHOLD) - 6} textAnchor="end" fontSize="11" fill="#14232a">Alert {ALERT_THRESHOLD * 100}%</text>
      <polyline points={points} fill="none" stroke="#0b6e8a" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
      {days.map((d, i) => (
        <g key={d.day_label}>
          <circle cx={x(i)} cy={y(d.probability)} r="5" fill="#fff" stroke="#0b6e8a" strokeWidth="2.5" />
          <text x={x(i)} y={y(d.probability) - 11} textAnchor="middle" fontSize="12" fontFamily="IBM Plex Mono, monospace" fill="#14232a">{percent(d.probability)}</text>
          <text x={x(i)} y={H - 12} textAnchor="middle" fontSize="12" fill="#52636b">{d.day_label}</text>
        </g>
      ))}
    </svg>
  )
}

function Outlook({ res }) {
  const { loc } = usePredict()
  const [state, setState] = useState({ days: null, error: '' })

  useEffect(() => {
    let live = true
    const f = res.input_features || {}
    forecast({
      latitude: loc.lat,
      longitude: loc.lon,
      matched_station: res.matched_region,
      rainfall_lag1: f.rainfall_lag1 ?? 10,
      rainfall_lag2: f.rainfall_lag2 ?? 5,
    })
      .then((d) => live && setState({ days: d.forecast_days, error: '' }))
      .catch((e) => live && setState({ days: null, error: e.message }))
    return () => { live = false }
  }, [res, loc.lat, loc.lon])

  if (state.error) return <Notice kind="warn">The outlook is not available right now: {state.error}</Notice>
  if (!state.days) return <p className="hint">Loading the outlook...</p>

  const days = state.days
  const firstBelow = days.find((d) => d.probability < ALERT_THRESHOLD)
  const headline = !firstBelow
    ? 'Risk stays above the alert line for the whole outlook.'
    : days.every((d) => d.probability < ALERT_THRESHOLD)
      ? 'Risk stays below the alert line for the next five days.'
      : `Risk is above the alert line until ${firstBelow.day_label}, then drops below it.`

  return (
    <div className="row" style={{ gap: 32 }}>
      <div style={{ flex: '1 1 380px', maxWidth: 560, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <OutlookChart days={days} />
        <p className="hint">A simple statistical projection from recent rainfall. It is not a full weather model.</p>
      </div>
      <div style={{ flex: '1 1 320px', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <p style={{ fontSize: 16, lineHeight: 1.55, maxWidth: 420 }}>{headline}</p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Day</th><th className="num">Chance</th><th>Status</th></tr></thead>
            <tbody>
              {days.map((d) => (
                <tr key={d.day_label}>
                  <td>{d.day_label}</td>
                  <td className="num">{percent(d.probability)}</td>
                  <td><RiskBadge small prob={d.probability} label={d.probability >= ALERT_THRESHOLD ? 'Above alert' : 'Below alert'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const TABS = [
  { id: 'factors', label: 'Key factors' },
  { id: 'compare', label: 'SHAP vs LIME' },
  { id: 'outlook', label: '5-day outlook' },
]

export default function ResultPanel({ res }) {
  const [tab, setTab] = useState('factors')
  const [pdfError, setPdfError] = useState('')

  async function savePdf() {
    setPdfError('')
    try {
      const blob = await downloadReport(res)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `RainXplain_Report_${String(res.matched_region || 'Region').replace(/\s+/g, '_')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setPdfError(`The PDF could not be created: ${e.message}`)
    }
  }

  return (
    <section id="result" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="result-head">
        <h2 className="result-title">Result for {res.matched_region}</h2>
        <button type="button" className="btn" onClick={savePdf}><Icon name="download" size={16} />Download PDF</button>
      </div>
      {pdfError && <Notice kind="error">{pdfError}</Notice>}
      {(res.confidence_flags || []).map((f) => <Notice key={f} kind="warn">{f}</Notice>)}

      <Verdict res={res} />

      <div className="panel">
        <div className="panel-head">
          <h3 className="panel-title">Why the model says this</h3>
          <div className="tabs" role="tablist" aria-label="Explanation view">
            {TABS.map((t) => (
              <button key={t.id} type="button" role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}>{t.label}</button>
            ))}
          </div>
        </div>
        <div className="tabpanel" role="tabpanel">
          {tab === 'factors' && <div style={{ maxWidth: 880 }}><FactorChart factors={res.shap_explanation} /></div>}
          {tab === 'compare' && <Compare res={res} />}
          {tab === 'outlook' && <Outlook res={res} />}
        </div>
      </div>
    </section>
  )
}
