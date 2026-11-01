export type Place = { label: string; lat: number; lon: number }

export type PlanRequest = {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_miles: 10 | 25 | 50
}

export type Checkpoint = {
  mile: number
  lat: number
  lon: number
  eta: string
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
  risk: number
  risk_label: string
  risk_driver: 'wind' | 'rain' | 'snow'
}

export type Segment = { risk: number; path: [number, number][] }

export type Route = {
  id: string
  distance_miles: number
  duration_s: number
  arrival: string
  no_travel_miles: number
  severe_miles: number
  high_miles: number
  average_risk: number
  checkpoints: Checkpoint[]
  segments: Segment[]
}

export type Heatmap = {
  bounds: [number, number, number, number]
  rows: number
  cols: number
  hours: number
  start: string
  levels: string
}

export type Plan = {
  departure: string
  load_lb: number
  interval_miles: number
  recommended_route: string
  blocked: boolean
  reason: string
  routes: Route[]
  heatmap: Heatmap
}
