import { describe, expect, it, vi } from 'vitest'

import {
  formatChatListTime,
  formatDateDivider,
  formatMessageTime,
  shouldShowDateDivider,
} from './formatTime'

describe('formatTime utilities', () => {
  it('formats message timestamps', () => {
    expect(formatMessageTime('2026-06-03T08:30:00.000Z')).toEqual(expect.any(String))
  })

  it('formats today, yesterday, and older chat-list timestamps', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-03T12:00:00.000Z'))

    expect(formatChatListTime('2026-06-03T08:30:00.000Z')).toEqual(expect.any(String))
    expect(formatChatListTime('2026-06-02T08:30:00.000Z')).toEqual(expect.any(String))
    expect(formatChatListTime('2026-05-25T08:30:00.000Z')).toEqual(expect.any(String))

    vi.useRealTimers()
  })

  it('formats date dividers and decides when dividers are needed', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-03T12:00:00.000Z'))

    expect(formatDateDivider('2026-06-03T08:30:00.000Z')).toEqual(expect.any(String))
    expect(formatDateDivider('2026-06-02T08:30:00.000Z')).toEqual(expect.any(String))
    expect(formatDateDivider('2026-05-25T08:30:00.000Z')).toEqual(expect.any(String))
    expect(shouldShowDateDivider({ timestamp: '2026-06-03T08:30:00.000Z' }, null)).toBe(true)
    expect(
      shouldShowDateDivider(
        { timestamp: '2026-06-03T09:30:00.000Z' },
        { timestamp: '2026-06-03T08:30:00.000Z' }
      )
    ).toBe(false)
    expect(
      shouldShowDateDivider(
        { timestamp: '2026-06-03T09:30:00.000Z' },
        { timestamp: '2026-06-02T08:30:00.000Z' }
      )
    ).toBe(true)

    vi.useRealTimers()
  })
})
