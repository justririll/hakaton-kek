/**
 * Загрузка данных витрины.
 *
 * Конвейер на бэкенде считается один раз при старте и дальше не меняется, а
 * весь объём — двадцать организаций. Поэтому витрина забирает всё одним заходом
 * при открытии и дальше работает без сетевых задержек: переключение разделов
 * и фильтров мгновенное, а не «спиннер на каждый клик».
 */

import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from './api'
import type {
  Anomaly, Clusters, Meta, Organization, Overview, PlanRow,
  Quality, Recommendation, Validation,
} from './types'

export interface Data {
  overview: Overview
  organizations: Organization[]
  clusters: Clusters
  validation: Validation
  recommendations: Recommendation[]
  plan: PlanRow[]
  anomalies: Anomaly[]
  quality: Quality
  meta: Meta
}

export interface Derived {
  byId: Map<string, Organization>
  planById: Map<string, PlanRow>
  clusterById: Map<number, Clusters['profiles'][number]>
  recsByOrg: Map<string, Recommendation[]>
  anomaliesByOrg: Map<string, Anomaly[]>
  qualityByOrg: Map<string, Quality['issues']>
  nameOf: (id: string) => string
}

type State =
  | { phase: 'loading'; progress: number }
  | { phase: 'error'; error: string }
  | { phase: 'ready'; data: Data; derived: Derived }

const Ctx = createContext<State | null>(null)

function derive(data: Data): Derived {
  const byId = new Map(data.organizations.map((o) => [o.org_id, o]))
  const planById = new Map(data.plan.map((p) => [p.org_id, p]))
  const clusterById = new Map(data.clusters.profiles.map((p) => [p.cluster_id, p]))

  const group = <T extends { org_id: string }>(rows: T[]) => {
    const map = new Map<string, T[]>()
    for (const row of rows) {
      const list = map.get(row.org_id)
      if (list) list.push(row)
      else map.set(row.org_id, [row])
    }
    return map
  }

  return {
    byId,
    planById,
    clusterById,
    recsByOrg: group(data.recommendations),
    anomaliesByOrg: group(data.anomalies),
    qualityByOrg: group(data.quality.issues),
    nameOf: (id: string) => byId.get(id)?.short_name ?? id,
  }
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State>({ phase: 'loading', progress: 0 })

  useEffect(() => {
    let alive = true
    const requests = [
      api.overview(), api.organizations(), api.clusters(), api.validation(),
      api.recommendations(), api.plan(), api.anomalies(), api.quality(), api.meta(),
    ] as const
    let done = 0
    for (const request of requests) {
      void (request as Promise<unknown>).then(() => {
        done += 1
        if (alive) setState((s) => (s.phase === 'loading' ? { phase: 'loading', progress: done / requests.length } : s))
      }).catch(() => {})
    }

    Promise.all(requests)
      .then(([overview, organizations, clusters, validation, recommendations, plan, anomalies, quality, meta]) => {
        if (!alive) return
        const data: Data = {
          overview, organizations, clusters, validation,
          recommendations: recommendations.items, plan,
          anomalies: anomalies.items, quality, meta,
        }
        setState({ phase: 'ready', data, derived: derive(data) })
      })
      .catch((error: Error) => {
        if (alive) setState({ phase: 'error', error: error.message })
      })

    return () => { alive = false }
  }, [])

  return <Ctx.Provider value={state}>{children}</Ctx.Provider>
}

export function useAppState(): State {
  const state = useContext(Ctx)
  if (!state) throw new Error('DataProvider отсутствует в дереве компонентов')
  return state
}

/** Данные внутри разделов: до них доходит только готовое состояние. */
export function useData(): { data: Data; derived: Derived } {
  const state = useAppState()
  if (state.phase !== 'ready') throw new Error('данные ещё не загружены')
  return useMemo(() => ({ data: state.data, derived: state.derived }), [state])
}
