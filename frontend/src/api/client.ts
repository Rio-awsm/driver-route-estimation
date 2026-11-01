import type { Place, Plan, PlanRequest } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? ''

async function readError(response: Response) {
  const body = await response.json().catch(() => null)
  if (body?.detail) return String(body.detail)
  if (body) return Object.values(body).flat().join(' ')
  return `Request failed (${response.status}).`
}

export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/api/health`)
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}

export async function createPlan(request: PlanRequest): Promise<Plan> {
  const response = await fetch(`${API_URL}/api/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) throw new Error(await readError(response))
  return response.json()
}

export async function searchPlaces(query: string, signal: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({ q: query })
  const response = await fetch(`${API_URL}/api/geocode?${params}`, { signal })
  if (!response.ok) throw new Error(await readError(response))
  const body = await response.json()
  return body.results
}
