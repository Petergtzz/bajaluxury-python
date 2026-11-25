import { describe, expect, it } from 'vitest'

import {
  parseStatementFilters,
  parseUtilitiesFilters,
  reportRange,
  serializeStatementFilters,
  serializeUtilitiesFilters,
  STATEMENT_PERIODS,
  toQueryString,
  UTILITIES_PERIODS,
} from './filters'

const params = (address: string) => new URLSearchParams(address)

describe('statement filters', () => {
  it('start on last month and leave it out of the address', () => {
    const filters = parseStatementFilters(params(''))
    expect(filters).toMatchObject({ period: 'last-month', property: '', currency: '' })
    expect(serializeStatementFilters(filters)).toBe('')
    expect(reportRange(filters, '2026-01-15', STATEMENT_PERIODS)).toEqual({
      start: '2025-12-01',
      end: '2025-12-31',
    })
  })

  it('refuse a period a report has no end for', () => {
    expect(parseStatementFilters(params('period=all')).period).toBe('last-month')
  })

  it('keep the property and currency', () => {
    const filters = parseStatementFilters(
      params('period=this-year&property=p1&currency=USD&x=1'),
    )
    expect(serializeStatementFilters(filters)).toBe(
      'period=this-year&property=p1&currency=USD',
    )
    expect(parseStatementFilters(params('currency=EUR')).currency).toBe('')
  })
})

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
