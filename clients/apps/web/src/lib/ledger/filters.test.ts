import { describe, expect, it } from 'vitest'

import { parseFilters, serializeFilters, toTransactionQuery } from './filters'
import { getPeriodLabel, getRange } from './period'

const parse = (address: string) => parseFilters(new URLSearchParams(address))

describe('ledger filters', () => {
  it('reads the address and writes it back without the defaults', () => {
    const filters = parse(
      'period=this-year&property=p1&type=income&method=cash&category=staff',
    )
    expect(filters).toMatchObject({
      period: 'this-year',
      property: 'p1',
      type: 'income',
      method: 'cash',
      category: 'staff',
    })
    expect(serializeFilters(filters)).toBe(
      'period=this-year&property=p1&type=income&method=cash&category=staff',
    )
    expect(serializeFilters(parse(''))).toBe('')
  })

  it('drops what it does not know', () => {
    expect(parse('period=forever&type=refund&method=gold')).toMatchObject({
      period: 'this-month',
      type: '',
      method: '',
    })
  })

  it('keeps a custom period only when its days make sense', () => {
    expect(parse('period=custom&from=2026-01-01&to=2026-03-31')).toMatchObject({
      period: 'custom',
      from: '2026-01-01',
    })
    expect(parse('period=custom&from=2026-03-31&to=2026-01-01').period).toBe('this-month')
    expect(parse('period=custom&from=yesterday&to=2026-01-01').period).toBe('this-month')
  })

  it("asks the API for the period's days", () => {
    expect(toTransactionQuery(parse('property=p1'), '2026-02-14')).toEqual({
      start_date: '2026-02-01',
      end_date: '2026-02-28',
      property_id: 'p1',
    })
    expect(toTransactionQuery(parse('period=all'), '2026-02-14')).toEqual({})
  })
})

describe('periods', () => {
  it('spans months, a year, across the new year', () => {
    expect(getRange('last-month', '2026-01-10')).toEqual({
      from: '2025-12-01',
      to: '2025-12-31',
    })
    expect(getRange('this-month', '2028-02-03')).toEqual({
      from: '2028-02-01',
      to: '2028-02-29',
    })
    expect(getRange('this-year', '2026-07-01')).toEqual({
      from: '2026-01-01',
      to: '2026-12-31',
    })
    expect(getRange('all', '2026-07-01')).toBeNull()
  })

  it('names them', () => {
    expect(getPeriodLabel('this-month', '2026-11-25')).toBe('November 2026')
    expect(getPeriodLabel('last-month', '2026-01-25')).toBe('December 2025')
    expect(getPeriodLabel('this-year', '2026-11-25')).toBe('2026')
  })
})
