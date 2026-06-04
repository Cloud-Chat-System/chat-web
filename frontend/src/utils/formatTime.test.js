import { describe, expect, it } from 'vitest'

import { parseBackendTimestamp } from './formatTime'

describe('parseBackendTimestamp', () => {
  it('treats offset-less backend timestamps as UTC', () => {
    expect(parseBackendTimestamp('2026-06-04T08:30:00').toISOString()).toBe(
      '2026-06-04T08:30:00.000Z'
    )
  })

  it('keeps explicit timezone offsets intact', () => {
    expect(parseBackendTimestamp('2026-06-04T16:30:00+08:00').toISOString()).toBe(
      '2026-06-04T08:30:00.000Z'
    )
  })
})
