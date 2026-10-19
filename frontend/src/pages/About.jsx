import { PageHeader } from '../components/ui'

export default function About() {
  return (
    <>
      <PageHeader title="About RainXplain" />
      <section className="panel prose">
        <p>
          RainXplain estimates the chance of heavy rain (64.5 mm or more in 24 hours, the IMD threshold) at any location in
          India, using an XGBoost model trained on historical station data.
        </p>
        <p>
          <strong>Every prediction comes with reasons.</strong> SHAP and LIME show which inputs pushed the result up or down,
          so the output can be checked instead of taken on faith. A forecast nobody can inspect is hard to act on in an emergency.
        </p>
        <p>
          <strong>Why it matters for infrastructure (UN SDG 9).</strong> Early warning gives city planners and transport
          operators time to clear storm drains, reroute transit, and protect power and telecom lines before damage is done.
        </p>
        <p>
          <strong>How locations are matched.</strong> The nearest of 406 weather stations is found with a pre-built spatial
          index, so lookups keep working without an internet connection.
        </p>
        <p>
          <strong>What to keep in mind.</strong> Heavy-rain days are rare, so the model is tuned to catch more of them at the
          cost of some false alarms. The 5-day outlook is a simple statistical projection, not a full weather model.
        </p>
      </section>
    </>
  )
}
