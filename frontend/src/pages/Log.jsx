import { useMemo, useState } from 'react'
import { getRecentPredictions } from '../api'
import { Notice, PageHeader, RiskBadge } from '../components/ui'
import { formatWhen, percent, sentence } from '../format'
import { useLoad } from '../hooks'

export default function Log() {
  const { data, error, loading } = useLoad(() => getRecentPredictions(50))
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState('All levels')

  const levels = useMemo(() => ['All levels', ...new Set((data || []).map((r) => r.risk_level).filter(Boolean))], [data])
  const rows = useMemo(
    () => (data || []).filter((r) =>
      (!query || String(r.matched_region || '').toLowerCase().includes(query.toLowerCase())) &&
      (level === 'All levels' || r.risk_level === level)),
    [data, query, level],
  )

  return (
    <>
      <PageHeader title="Prediction log" subtitle="Every prediction made in the app is saved here so it can be reviewed later." />
      {error && <Notice kind="error">The log could not be loaded: {error}</Notice>}
      {loading && <p className="hint">Loading...</p>}
      {data && (
        <>
          <div className="filters">
            <div className="field">
              <label htmlFor="q">Search by station</label>
              <input id="q" className="text-input" type="search" placeholder="For example, Mumbai" value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div className="field" style={{ flexBasis: 200 }}>
              <label htmlFor="lvl">Risk level</label>
              <select id="lvl" className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
                {levels.map((l) => <option key={l}>{l}</option>)}
              </select>
            </div>
          </div>

          <section className="panel">
            {rows.length === 0 ? (
              <p className="empty">{data.length === 0 ? 'No predictions yet. Run one from the Predict screen and it will show up here.' : 'No predictions match these filters.'}</p>
            ) : (
              <div className="table-wrap" style={{ border: 0 }}>
                <table className="table" style={{ minWidth: 760 }}>
                  <thead>
                    <tr><th>When</th><th>Station</th><th>Risk</th><th className="num">Probability</th><th>Summary</th></tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id}>
                        <td className="nowrap muted">{formatWhen(r.timestamp)}</td>
                        <td className="nowrap" style={{ fontWeight: 500 }}>{r.matched_region}</td>
                        <td><RiskBadge small label={sentence(r.risk_level)} prob={r.probability ?? 0} /></td>
                        <td className="num">{percent(r.probability ?? 0, 1)}</td>
                        <td>{r.plain_language_summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          <p className="hint">Showing {rows.length} of the latest {data.length} predictions.</p>
        </>
      )}
    </>
  )
}
