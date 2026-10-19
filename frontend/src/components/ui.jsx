import { featureLabel, featureReading, riskTone, signed } from '../format'

const base = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor',
  strokeWidth: 1.9, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true,
}

const PATHS = {
  pin: <><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></>,
  list: <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />,
  chart: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
  lock: <><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></>,
  warn: <path d="M12 4l10 17H2L12 4zM12 10v5M12 18h.01" />,
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  download: <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />,
  chevron: <path d="M6 9l6 6 6-6" />,
  drop: <path d="M12 3c3.5 4.2 6 7.2 6 10.5a6 6 0 0 1-12 0C6 10.2 8.5 7.2 12 3z" />,
}

export function Icon({ name, size = 18 }) {
  return <svg {...base} width={size} height={size}>{PATHS[name]}</svg>
}

export function PageHeader({ title, subtitle }) {
  return (
    <header>
      <h1 className="page-title">{title}</h1>
      {subtitle && <p className="page-sub">{subtitle}</p>}
    </header>
  )
}

export function Notice({ kind = 'info', children }) {
  const icon = { warn: 'warn', ok: 'check', info: 'info', error: 'warn' }[kind]
  return (
    <div className={`notice ${kind}`} role={kind === 'error' ? 'alert' : undefined}>
      <Icon name={icon} />
      <span>{children}</span>
    </div>
  )
}

export function RiskBadge({ label, prob, small }) {
  const { bg, fg } = riskTone(prob)
  return <span className={`badge${small ? ' sm' : ''}`} style={{ background: bg, color: fg }}>{label}</span>
}

export function FactorChart({ factors, limit = 8 }) {
  const rows = (factors || []).slice(0, limit).filter((r) => typeof r.shap_value === 'number')
  if (!rows.length) return <p className="hint">No explanation is available for this prediction.</p>
  const top = Math.max(...rows.map((r) => Math.abs(r.shap_value))) || 1
  return (
    <div>
      <div className="legend">
        <span><i style={{ background: 'var(--hot)' }} />Raises the risk</span>
        <span><i style={{ background: 'var(--cool)' }} />Lowers the risk</span>
      </div>
      {rows.map((r) => {
        const w = `${(Math.abs(r.shap_value) / top) * 100}%`
        return (
          <div className="factor" key={r.feature}>
            <div>
              <div className="name">{featureLabel(r.feature)}</div>
              <div className="read">{featureReading(r.feature, r.value)}</div>
            </div>
            <div className="axis" role="img" aria-label={`${featureLabel(r.feature)} ${r.shap_value > 0 ? 'raises' : 'lowers'} the risk`}>
              <div className="neg">{r.shap_value < 0 && <div style={{ width: w }} />}</div>
              <div className="pos">{r.shap_value > 0 && <div style={{ width: w }} />}</div>
            </div>
            <div className="val">{signed(r.shap_value)}</div>
          </div>
        )
      })}
    </div>
  )
}
