import type { Place, Plan, PlanRequest } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? ''

async function readError(response: Response) {
  const body = await response.json().catch(() => null)
  if (body?.detail) return String(body.detail)
  if (body) return Object.values(body).flat().join(' ')
  return `Request failed (${response.status}).`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init).catch((error) => {
    if (error.name === 'AbortError') throw error
    throw new Error('The server could not be reached.')
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}

export function createPlan(plan: PlanRequest) {
  return request<Plan>('/api/plan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(plan),
  })
}

export async function searchPlaces(query: string, signal: AbortSignal) {
  const params = new URLSearchParams({ q: query })
  const body = await request<{ results: Place[] }>(`/api/geocode?${params}`, { signal })
  return body.results
}
