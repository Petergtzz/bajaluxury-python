import { describe, expect, it } from 'vitest'

import {
  parseUtilitiesFilters,
  reportRange,
  serializeUtilitiesFilters,
  toQueryString,
  UTILITIES_PERIODS,
} from './filters'

const params = (address: string) => new URLSearchParams(address)

describe('utilities filters', () => {
  it('start on this year, showing totals', () => {
    const filters = parseUtilitiesFilters(params(''))
    expect(filters).toMatchObject({ period: 'this-year', view: 'totals' })
    expect(serializeUtilitiesFilters(filters)).toBe('')
    expect(reportRange(filters, '2026-11-25', UTILITIES_PERIODS)).toEqual({
      start: '2026-01-01',
      end: '2026-12-31',
    })
  })

  it('remember the tracker', () => {
    expect(serializeUtilitiesFilters(parseUtilitiesFilters(params('view=tracker')))).toBe(
      'view=tracker',
    )
  })
})

it('writes a download link query, lists as repeated keys', () => {
  expect(
    toQueryString({ start: '2026-01-01', currency: undefined, buckets: ['pool', 'cfe'] }),
  ).toBe('start=2026-01-01&buckets=pool&buckets=cfe')
})
