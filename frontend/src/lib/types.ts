/** Типы ответов аналитического API. Повторяют то, что реально отдаёт бэкенд. */

export type PlanStatus = 'опережение' | 'в графике' | 'риск' | 'срыв' | 'без базы'
export type Severity = 'error' | 'warning' | 'info'

export interface DynamicsRow {
  key: 'audience' | 'formats' | 'products' | 'revenue'
  label: string
  unit: string
  baseline_2025: number | null
  baseline_orgs: number
  baseline_coverage: number
  fact_comparable: number | null
  fact_ytd: number
  run_rate_year: number
  growth_ytd: number | null
  growth_year: number | null
  target_2026: number | null
  reported_months: number
}

export interface ImpactEntry {
  total: number
  unit: string
  count: number
}

export interface Overview {
  organizations: number
  audience_total: number
  formats_total: number
  products_total: number
  residents_total: number
  revenue_total: number
  publications_total: number
  federal_events_total: number
  ip_total: number
  median_audience_per_format: number
  median_product_rate: number
  plan_status: Record<string, number>
  plan_at_risk: number
  clusters: number
  recommendations: {
    total: number
    by_type: Record<string, number>
    impact: Record<string, ImpactEntry>
    impact_verified: Record<string, ImpactEntry>
    flagged: number
    flagged_orgs: string[]
    mean_priority: number
    mean_confidence: number
  }
  anomalies: number
  data_quality: Record<string, number>
  dynamics: DynamicsRow[]
  build_seconds: number
}

export interface Organization {
  org_id: string
  short_name: string
  full_name: string
  center: string
  year: number
  report_date: string
  source_file: string
  audience_total: number
  supply_total: number
  audience_per_format: number
  products_total: number
  product_rate: number
  residents_total: number
  resident_rate: number
  revenue_total: number
  revenue_per_participant: number
  media_publications: number
  federal_events: number
  publicity_per_format: number
  ip_total: number
  cluster: number
  completion: number | null
  status: PlanStatus
  run_rate_forecast: number | null
  target_2026: number | null
  silhouette: number
  [key: string]: string | number | null
}

export interface Distinctive {
  feature: string
  description: string
  z: number
  label: string
}

export interface ClusterProfile {
  cluster_id: number
  name: string
  summary: string
  size: number
  members: string[]
  member_names: string[]
  distinctive: Distinctive[]
  mean_silhouette: number
  centroid: Record<string, number>
}

export interface EmbeddingPoint {
  org_id: string
  name: string
  cluster: number
  silhouette: number
  audience_total: number
  pc1: number
  pc2: number
  pc3: number
  pc4: number
  pc5: number
}

export interface KCandidate {
  k: number
  silhouette: number
  calinski_harabasz: number
  davies_bouldin: number
  stability: number
  balance: number
  score: number
  sizes: number[]
}

export interface Clusters {
  k: number
  algorithm: string
  profiles: ClusterProfile[]
  embedding: EmbeddingPoint[]
  explained_variance: number[]
  components: number
  loadings: Array<{ feature: string } & Record<string, number | string>>
  agreement: Record<string, number>
  candidates: KCandidate[]
  dendrogram: { icoord: number[][]; dcoord: number[][]; ivl: string[]; merge_heights: number[] }
  feature_descriptions: Record<string, string>
  feature_blocks: Record<string, string[]>
}

export interface Validation {
  clustering: {
    observed_silhouette: number
    permutation_mean: number
    permutation_std: number
    permutation_p_value: number
    effect_size: number
    loo_mean_ari: number
    loo_min_ari: number
    membership_confidence: Record<string, number>
    unstable_members: string[]
    verdict: string
  }
  recommendations: {
    total: number
    runs: number
    stable_share: number
    mean_survival: number
    unstable: Array<{ org_id: string; rec_type: string; channel: string | null; rate: number }>
  }
  co_assignment: Array<{ org_id: string } & Record<string, number | string>>
}

export type RecType =
  | 'fix_format'
  | 'expand_format'
  | 'launch_format'
  | 'raise_conversion'
  | 'monetize'
  | 'amplify_visibility'
  | 'plan_risk'

export interface Recommendation {
  org_id: string
  org_name: string
  rec_type: RecType
  title: string
  action: string
  channel: string | null
  priority: number
  raw_score: number
  confidence: number
  impact_metric: string | null
  impact_value: number | null
  impact_unit: string | null
  rationale: string
  evidence: Record<string, number | string | null>
  data_flag: boolean
}

export interface PlanRow {
  org_id: string
  short_name: string
  baseline_2025: number | null
  target_growth: number | null
  target_2026: number | null
  fact_ytd: number
  completion: number | null
  run_rate_forecast: number | null
  forecast_gap: number | null
  required_remaining: number | null
  required_monthly_rate: number | null
  current_monthly_rate: number | null
  status: PlanStatus
}

export interface Anomaly {
  org_id: string
  org_name: string
  kind: string
  metric: string
  severity: Severity
  value: number | null
  reference: number | null
  score: number
  message: string
}

export interface QualityIssue {
  org_id: string
  severity: Severity
  kind: string
  indicator: string
  message: string
}

export interface Quality {
  organizations: number
  indicators: number
  cell_coverage: number
  issues_total: number
  issues_by_severity: Record<string, number>
  issues: QualityIssue[]
}

export interface Meta {
  indicators: Array<{ key: string; title: string; unit: string; group: string; form: string; code: string }>
  channels: Array<{ key: string; label: string; audience_key: string; product_key: string }>
  recommendation_types: Record<string, string>
}

export interface OrgDetail {
  org_id: string
  passport: Record<string, string | number>
  facts: Record<string, number>
  profile: Record<string, number>
  plan: Omit<PlanRow, 'org_id' | 'short_name'>
  cluster: {
    id: number
    name: string
    summary: string
    size: number
    peers: string[]
    membership_confidence: number | null
    silhouette: number
  }
  recommendations: Recommendation[]
  anomalies: Anomaly[]
}

export interface AiSummary {
  status: string
  model?: string
  generated_at?: string
  content?: string
  elapsed_seconds?: number
  tokens?: { prompt: number; candidates: number; total: number }
  cached?: boolean
  stale?: boolean
  detail?: string
}
