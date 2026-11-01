import { describe, expect, it } from 'vitest'
import { NO_DATA, RISK_LEVELS } from '@/lib/risk'
import { decodeLevels, framePixels } from './heatmapFrames'

describe('decodeLevels', () => {
  it('turns base64 back into bytes', () => {
    expect([...decodeLevels(btoa('\u0000\u0004ÿ'))]).toEqual([0, 4, 255])
  })
})

describe('framePixels', () => {
  const twoHoursTwoCells = new Uint8Array([0, 4, NO_DATA, 2])

  it('reads only the requested hour', () => {
    const pixels = framePixels(twoHoursTwoCells, 2, 1)
    expect(pixels[3]).toBe(0)
    expect([...pixels.slice(4, 7)]).toEqual([...RISK_LEVELS[2].rgb])
  })

  it('colours risk levels and raises opacity with risk', () => {
    const pixels = framePixels(twoHoursTwoCells, 2, 0)
    expect([...pixels.slice(4, 7)]).toEqual([...RISK_LEVELS[4].rgb])
    expect(pixels[7]).toBeGreaterThan(pixels[3])
  })

  it('makes cells outside the corridor fully transparent but not black', () => {
    const pixels = framePixels(new Uint8Array([NO_DATA]), 1, 0)
    expect(pixels[3]).toBe(0)
    expect(pixels[0]).toBe(RISK_LEVELS[0].rgb[0])
  })
})
