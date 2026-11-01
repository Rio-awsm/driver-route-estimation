import { describe, expect, it } from 'vitest'
import { formatDuration, toLocalInputValue } from './format'

describe('formatDuration', () => {
  it.each([
    [59 * 60, '59m'],
    [3600, '1h 0m'],
    [57_329, '15h 55m'],
    [3599.9, '1h 0m'],
  ])('formats %d seconds', (seconds, expected) => {
    expect(formatDuration(seconds)).toBe(expected)
  })
})

describe('toLocalInputValue', () => {
  it('produces a value that reads back as the same moment', () => {
    const moment = new Date('2026-11-02T14:30:00Z')
    expect(new Date(toLocalInputValue(moment)).getTime()).toBe(moment.getTime())
  })
})
