import ConditionsForm from '../components/ConditionsForm'
import MapPicker from '../components/MapPicker'
import ResultPanel from '../components/ResultPanel'
import { Notice, PageHeader } from '../components/ui'
import { usePredict } from '../PredictContext'

export default function Predict() {
  const { result, error } = usePredict()
  return (
    <>
      <PageHeader
        title="Predict heavy rain"
        subtitle="Choose a place on the map, check the weather conditions, and see the chance of 64.5 mm or more of rain in 24 hours, with the reasons behind it."
      />
      {error && <Notice kind="error">{error}</Notice>}
      <div className="row">
        <MapPicker />
        <ConditionsForm />
      </div>
      {result && <ResultPanel res={result} />}
    </>
  )
}
