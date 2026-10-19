import { useEffect, useState } from 'react'

// Runs an async loader on mount and reports { data, error, loading }.
export function useLoad(loader, deps = []) {
  const [state, setState] = useState({ data: null, error: '', loading: true })
  useEffect(() => {
    let live = true
    setState((s) => ({ ...s, loading: true }))
    loader()
      .then((data) => live && setState({ data, error: '', loading: false }))
      .catch((e) => live && setState({ data: null, error: e.message, loading: false }))
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}
