import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPlan, searchPlaces } from './client'
import type { PlanRequest } from './types'

const request = {} as PlanRequest

function respondWith(status: number, body: string) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status })))
}

afterEach(() => vi.unstubAllGlobals())

describe('API errors', () => {
  it('shows the message from a provider failure', async () => {
    respondWith(422, '{"detail":"No truck route was found between these places."}')
    await expect(createPlan(request)).rejects.toThrow('No truck route was found between these places.')
  })

  it('joins field validation messages', async () => {
    respondWith(400, '{"load_lb":["Too low."],"departure":["Departure cannot be in the past."]}')
    await expect(createPlan(request)).rejects.toThrow('Too low. Departure cannot be in the past.')
  })

  it('falls back to the status when the body is not JSON', async () => {
    respondWith(502, '<html>Bad gateway</html>')
    await expect(createPlan(request)).rejects.toThrow('Request failed (502).')
  })
})

describe('searchPlaces', () => {
  it('encodes the query and returns the results', async () => {
    respondWith(200, '{"results":[{"label":"Denver, CO","lat":39.7,"lon":-105}]}')
    const places = await searchPlaces('St. Louis & co', new AbortController().signal)
    const url = vi.mocked(fetch).mock.calls[0][0]
    expect(url).toContain('q=St.+Louis+%26+co')
    expect(places[0].label).toBe('Denver, CO')
  })
})
