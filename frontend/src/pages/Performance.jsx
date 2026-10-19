import { getPerformance } from '../api'
import { Notice, PageHeader } from '../components/ui'
import { featureLabel } from '../format'
import { useLoad } from '../hooks'

function RocChart({ roc }) {
  const fpr = roc.fpr || []
  const tpr = roc.tpr || []
  const step = Math.max(1, Math.floor(fpr.length / 160))
  const pts = fpr.map((f, i) => [f, tpr[i]]).filter((_, i) => i % step === 0 || i === fpr.length - 1)
  const X = (v) => 50 + v * 330
  const Y = (v) => 270 - v * 250
  const line = pts.map(([f, t]) => `${X(f)},${Y(t)}`).join(' ')
  return (
    <svg viewBox="0 0 400 310" width="100%" role="img" aria-label={`ROC curve, area under the curve ${roc.roc_auc}`} style={{ display: 'block' }}>
      {[0.25, 0.5, 0.75, 1].map((g) => <line key={g} x1="50" x2="380" y1={Y(g)} y2={Y(g)} stroke="#e4e9eb" />)}
      {[0.25, 0.5, 0.75, 1].map((g) => <line key={`v${g}`} y1="20" y2="270" x1={X(g)} x2={X(g)} stroke="#e4e9eb" />)}
      <path d="M50 270H380M50 20V270" stroke="#8fa3ab" strokeWidth="1.5" fill="none" />
      <line x1="50" y1="270" x2="380" y2="20" stroke="#8fa3ab" strokeWidth="1.5" strokeDasharray="5 4" />
      <polygon points={`50,270 ${line} 380,270`} fill="#e3f1f5" fillOpacity="0.7" />
      <polyline points={line} fill="none" stroke="#0b6e8a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <g fontSize="12" fill="#52636b" textAnchor="middle"><text x="50" y="290">0</text><text x="215" y="290">False alarms</text><text x="380" y="290">1</text></g>
      <g fontSize="12" fill="#52636b" textAnchor="end"><text x="42" y="274">0</text><text x="42" y="24">1</text></g>
      <text x="170" y="200" fontSize="14" fontFamily="IBM Plex Mono, monospace" fill="#08546b">AUC {Number(roc.roc_auc).toFixed(3)}</text>
    </svg>
  )
}

function Matrix({ m }) {
  const [[tn, fp], [fn, tp]] = m
  const cell = (n, label, bg, fg) => (
    <div className="c" style={{ background: bg, color: fg }}><b>{n.toLocaleString()}</b><span>{label}</span></div>
  )
  return (
    <div className="matrix">
      <div />
      <div className="h">Predicted: not heavy</div>
      <div className="h">Predicted: heavy</div>
      <div className="s">Actual: not heavy</div>
      {cell(tn, 'Correctly ignored', '#1b5e78', '#fff')}
      {cell(fp, 'False alarms', '#f4e4dc', '#14232a')}
      <div className="s">Actual: heavy</div>
      {cell(fn, 'Missed', '#f4e4dc', '#14232a')}
      {cell(tp, 'Correctly flagged', '#2f86a6', '#fff')}
    </div>
  )
}

export default function Performance() {
  const { data, error, loading } = useLoad(getPerformance)
  const metrics = data?.metrics || {}
  const matrix = data?.confusion_matrix?.matrix
  const caught = matrix?.[1]?.[1]
  const heavyDays = matrix ? matrix[1][0] + matrix[1][1] : null
  const total = matrix ? matrix.flat().reduce((a, b) => a + b, 0) : null
  const recall = metrics['test_recall_tuned_0.35']
  const shap = (data?.global_shap || []).slice(0, 10)
  const topShap = Math.max(...shap.map((s) => s.mean_abs_shap), 0.0001)

  return (
    <>
      <PageHeader
        title="How well the model works"
        subtitle="Tested on 2024 to 2025 data that the model never saw during training. Heavy-rain days are rare, so the numbers below should be read with that in mind."
      />
      {error && <Notice kind="error">Model performance could not be loaded: {error}</Notice>}
      {loading && <p className="hint">Loading...</p>}
      {data && (
        <>
          <section className="panel">
            <div className="panel-body row" style={{ alignItems: 'center', gap: '24px 40px' }}>
              {matrix && recall != null && (
                <p className="takeaway" style={{ flex: '1 1 360px' }}>
                  Out of <strong>{heavyDays.toLocaleString()}</strong> heavy-rain days in the test period, the model flagged{' '}
                  <strong>{caught.toLocaleString()}</strong> at the default cut-off. Lowering the alert threshold to 0.35 raises that to{' '}
                  <strong>{(recall * 100).toFixed(0)}%</strong>, at the cost of more false alarms.
                </p>
              )}
              <div className="metrics" style={{ flex: '1 1 420px' }}>
                {metrics.test_roc_auc != null && <div className="metric"><div className="l">ROC-AUC</div><div className="v">{metrics.test_roc_auc.toFixed(3)}</div></div>}
                {recall != null && <div className="metric"><div className="l">Recall at 0.35</div><div className="v">{(recall * 100).toFixed(1)}%</div></div>}
                {metrics.test_accuracy != null && <div className="metric"><div className="l">Accuracy</div><div className="v">{(metrics.test_accuracy * 100).toFixed(1)}%</div></div>}
                {metrics.test_pr_auc != null && <div className="metric"><div className="l">PR-AUC</div><div className="v">{metrics.test_pr_auc.toFixed(3)}</div></div>}
              </div>
            </div>
          </section>

          <div className="row">
            {data.roc_curve && (
              <section className="panel panel-body" style={{ flex: '1 1 440px' }}>
                <h2 className="panel-title">Catching rain without crying wolf</h2>
                <p className="hint">The closer the line hugs the top-left corner, the better. The dashed line is a coin flip.</p>
                <RocChart roc={data.roc_curve} />
              </section>
            )}
            {matrix && (
              <section className="panel panel-body" style={{ flex: '1 1 440px' }}>
                <h2 className="panel-title">What it got right and wrong</h2>
                <p className="hint">All {total.toLocaleString()} test records, at the default 0.5 cut-off.</p>
                <Matrix m={matrix} />
              </section>
            )}
          </div>

          {shap.length > 0 && (
            <section className="panel panel-body bars">
              <h2 className="panel-title">What the model pays attention to overall</h2>
              <p className="hint">Average SHAP impact across the whole test set. A longer bar means the factor shifts predictions more.</p>
              {shap.map((s) => (
                <div className="factor" key={s.feature}>
                  <div className="name">{featureLabel(s.feature)}</div>
                  <div className="track"><div style={{ width: `${(s.mean_abs_shap / topShap) * 100}%` }} /></div>
                  <div className="val">{s.mean_abs_shap.toFixed(2)}</div>
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </>
  )
}
