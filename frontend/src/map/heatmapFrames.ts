import type { Heatmap } from '@/api/types'
import { NO_DATA, RISK_LEVELS } from '@/lib/risk'

export function decodeLevels(base64: string) {
  const binary = atob(base64)
  const levels = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) levels[i] = binary.charCodeAt(i)
  return levels
}

export function framePixels(levels: Uint8Array, cells: number, hour: number) {
  const pixels = new Uint8ClampedArray(cells * 4)
  const start = hour * cells
  for (let cell = 0; cell < cells; cell += 1) {
    const level = levels[start + cell]
    // Keep a colour so edge smoothing can't fade to black.
    const { rgb, heatAlpha } = RISK_LEVELS[level === NO_DATA ? 0 : level]
    const offset = cell * 4
    pixels[offset] = rgb[0]
    pixels[offset + 1] = rgb[1]
    pixels[offset + 2] = rgb[2]
    pixels[offset + 3] = level === NO_DATA ? 0 : heatAlpha
  }
  return pixels
}

export function buildFrames(heatmap: Heatmap) {
  const levels = decodeLevels(heatmap.levels)
  const cells = heatmap.rows * heatmap.cols
  return Array.from(
    { length: heatmap.hours },
    (_, hour) => new ImageData(framePixels(levels, cells, hour), heatmap.cols, heatmap.rows),
  )
}
