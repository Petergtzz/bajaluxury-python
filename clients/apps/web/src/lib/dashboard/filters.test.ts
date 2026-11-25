import { describe, expect, it } from 'vitest'

import type { Property } from '@/lib/api/types'

import {
  balanceLabel,
  chooseProperty,
  dashboardProperties,
  dashboardRange,
  expensesHref,
  parseDashboardFilters,
  serializeDashboardFilters,
  share,
} from './filters'

const house = (id: string, name: string, is_archived = false): Property => ({
  id,
  name,
  address: null,
  is_archived,
  balance_methods: ['cash'],
  created_at: '2026-09-01T00:00:00Z',
})
const SOLD = house('p0', 'Acacia', true)
const COLINAS = house('p1', 'Colinas 21')
const CAMPO = house('p2', 'Campo 9')
const TODAY = '2026-11-25'

describe('the address', () => {
  it('leaves this month and the first house out', () => {
    const filters = parseDashboardFilters(new URLSearchParams())
    expect(filters).toEqual({ period: 'this-month', from: '', to: '', property: '' })
    expect(serializeDashboardFilters(filters)).toBe('')
    expect(
      serializeDashboardFilters({ ...filters, period: 'last-month', property: 'p1' }),
    ).toBe('period=last-month&property=p1')
  })

  it('refuses all time, which has no first day', () => {
    expect(parseDashboardFilters(new URLSearchParams('period=all')).period).toBe(
      'this-month',
    )
  })
})

describe('the house shown', () => {
  it('is the one asked for, else the first in use by name', () => {
    const all = [SOLD, COLINAS, CAMPO]
    expect(chooseProperty(all, '')?.name).toBe('Campo 9')
    expect(chooseProperty(all, 'gone')?.name).toBe('Campo 9')
    expect(chooseProperty(all, 'p0')?.name).toBe('Acacia')
    expect(chooseProperty([SOLD], '')).toBeUndefined()
  })

  it('is picked among those in use, and an archived one only once asked for', () => {
    const names = (asked: string) =>
      dashboardProperties([SOLD, COLINAS, CAMPO], asked).map((p) => p.name)
    expect(names('')).toEqual(['Campo 9', 'Colinas 21'])
    expect(names('p0')).toEqual(['Acacia', 'Campo 9', 'Colinas 21'])
  })
})

describe('the figures', () => {
  it('name the balance for its day', () => {
    const month = dashboardRange(parseDashboardFilters(new URLSearchParams()), TODAY)
    const last = dashboardRange(
      parseDashboardFilters(new URLSearchParams('period=last-month')),
      TODAY,
    )
    expect(month).toEqual({ from: '2026-11-01', to: '2026-11-30' })
    expect(balanceLabel(month, TODAY)).toBe('Balance today')
    expect(balanceLabel(last, TODAY)).toBe('Balance on 31 Oct 2026')
  })

  it('open the expenses they add up, on the same house and days', () => {
    const filters = parseDashboardFilters(new URLSearchParams('period=last-month'))
    expect(expensesHref(filters, 'p1', { category: 'services' })).toBe(
      '/transactions?period=last-month&property=p1&type=expense&category=services',
    )
    expect(expensesHref(filters, 'p1', { method: 'credit card' })).toBe(
      '/transactions?period=last-month&property=p1&type=expense&method=credit+card',
    )
  })

  it('round shares, never calling a sliver nothing', () => {
    expect([share(1, 3), share(1, 1000), share(0, 10), share(5, 0)]).toEqual([
      '33%',
      '<1%',
      '0%',
      '0%',
    ])
  })
})
