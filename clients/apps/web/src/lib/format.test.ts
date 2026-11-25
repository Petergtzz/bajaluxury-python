import { describe, expect, it } from 'vitest'

import {
  counted,
  formatDate,
  formatMomentDay,
  formatDayHeading,
  formatMoney,
  formatRange,
  groupConsecutive,
  sentence,
  todayIn,
} from './format'

describe('format', () => {
  it('writes money to the cent', () => {
    expect(formatMoney(1250.5, 'MXN')).toBe('MX$1,250.50')
    expect(formatMoney(-0.1, 'MXN')).toBe('-MX$0.10')
  })

  it('reads dates as days, whatever the browser zone', () => {
    expect(formatDate('2026-03-04')).toBe('4 Mar 2026')
    expect(formatDayHeading('2026-02-12', '2026-11-25')).toBe('12 February')
    expect(formatDayHeading('2025-12-11', '2026-11-25')).toBe('11 December 2025')
  })

  it('knows today where the company is', () => {
    // 03:00 UTC on Dec 1 is still Nov 30 in Mazatlan.
    expect(todayIn('America/Mazatlan', new Date('2026-12-01T03:00:00Z'))).toBe(
      '2026-11-30',
    )
  })

  it('writes a span of days as people do', () => {
    expect(formatRange('2026-07-01', '2026-07-31')).toBe('1–31 Jul 2026')
    expect(formatRange('2026-06-28', '2026-07-03')).toBe('28 Jun – 3 Jul 2026')
    expect(formatRange('2025-12-01', '2026-01-31')).toBe('1 Dec 2025 – 31 Jan 2026')
    expect(formatRange('2026-07-04', '2026-07-04')).toBe('4 Jul 2026')
  })

  it('groups neighbours', () => {
    expect(groupConsecutive([1, 1, 2, 1], (n) => n)).toEqual([
      { key: 1, items: [1, 1] },
      { key: 2, items: [2] },
      { key: 1, items: [1] },
    ])
  })

  it('words things', () => {
    expect(sentence('credit card')).toBe('Credit card')
    expect(sentence(null)).toBe('')
    expect(counted(1, 'property', 'properties')).toBe('1 property')
    expect(counted(5, 'property', 'properties')).toBe('5 properties')
  })
})

it('says the day a moment fell on where the company is', () => {
  // 03:00 UTC on the 26th is the evening of the 25th in Los Cabos.
  expect(formatMomentDay('2026-11-26T03:00:00Z', 'America/Mazatlan')).toBe('25 Nov 2026')
  expect(formatMomentDay('2026-11-26T03:00:00Z', 'Europe/Madrid')).toBe('26 Nov 2026')
})
