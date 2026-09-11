export interface Metrics {
  total_attendees: number
  algorithm_used: string
  silhouette_score: number
  initial_attendance_rate: number
  optimized_attendance_rate: number
  growth_percent: number
}

export interface Cluster {
  id: number
  name: string
  tag: string
  color: string
  count: number
  share_percent: number
  key_interests: string[]
}

export interface ScatterPoint {
  x: number
  y: number
  cluster_id: number
  name: string
  target: string
}

export interface ScheduleItem {
  id: string
  title: string
  hall: string
  cluster_id: number
  time_slot: string
  has_conflict: boolean
  optimized_time_slot: string
}

export interface Recommendation {
  event_id: string
  event_title: string
  action: string
  from_slot: string
  to_slot: string
  reason: string
  impact: string
}

export interface AnalyticsDashboard {
  metrics: Metrics
  clusters: Cluster[]
  scatter_points: ScatterPoint[]
  schedule: ScheduleItem[]
  recommendations: Recommendation[]
}
