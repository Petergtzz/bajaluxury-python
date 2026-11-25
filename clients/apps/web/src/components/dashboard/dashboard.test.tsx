import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { HOMEOWNER, OWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { Dashboard } from './dashboard'

const replace = vi.fn()
const push = vi.fn()
let search = ''
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => '/dashboard',
  useSearchParams: () => new URLSearchParams(search),
}))

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-25T18:00:00Z'))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  replace.mockReset()
  push.mockReset()
  search = ''
})

const house = (id: string, name: string) => ({
  id,
  name,
  address: null,
  is_archived: false,
  balance_methods: ['cash'],
  created_at: '2026-09-01T00:00:00Z',
})

const balance = (property_id: string, amount: number) => ({
  property_id,
  property_name: property_id,
  balance: amount,
  first_activity_date: '2026-09-14',
  last_income_date: null,
  last_activity_date: '2026-11-03',
})

const STATEMENT = {
  property_id: 'p2',
  property_name: 'Campo 9',
  start: '2026-11-01',
  end: '2026-11-30',
  currency: 'MXN',
  exchange_rate: null,
  opening_balance: 10000,
  closing_balance: 1500,
  income_total: 3440,
  expense_total: 8600,
  balance_expense_total: 6000,
  expenses_by_method: [
    { payment_method: 'cash', total: 6020 },
    { payment_method: 'credit card', total: 2580 },
  ],
  expenses_by_category: [
    { category: 'utilities', total: 6020, entries: [] },
    { category: 'supermarket', total: 2580, entries: [] },
  ],
  entries: [],
}

const COMPANY = {
  status: 200,
  body: {
    name: 'Baja Luxury',
    currency: 'MXN',
    timezone: 'America/Mazatlan',
    usd_exchange_rate: '17.2000',
  },
}

const routes = (properties = [house('p1', 'Colinas 21'), house('p2', 'Campo 9')]) => ({
  '/v1/company': COMPANY,
  '/v1/properties/': { status: 200, body: properties },
  '/v1/balances/': { status: 200, body: [balance('p1', 100), balance('p2', -1720)] },
  '/v1/properties/p2/statement': { status: 200, body: STATEMENT },
})

const rows = (name: string) =>
  within(screen.getByRole('region', { name }))
    .getAllByRole('listitem')
    .map((row) => row.textContent)

describe('Dashboard', () => {
  it('leads with the balance today, then the month by method and by category', async () => {
    const calls = stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    const summary = await screen.findByRole('region', { name: 'Summary' })
    expect(await within(summary).findByText('-MX$1,720.00')).toBeTruthy()
    expect(within(summary).getByText('+MX$3,440.00')).toBeTruthy()
    expect(within(summary).getByText('Spent in November')).toBeTruthy()
    expect(within(summary).getByText('MX$8,600.00')).toBeTruthy()
    expect(calls.requested).toContain(
      '/v1/properties/p2/statement?start=2026-11-01&end=2026-11-30',
    )
    expect(rows('Spent by payment method')).toEqual([
      'CashMX$6,020.00',
      'Credit cardMX$2,580.00',
    ])
    expect(rows('Where it went')).toEqual([
      'UtilitiesMX$6,020.0070%',
      'SupermarketMX$2,580.0030%',
    ])
  })

  it('shows every amount in dollars to someone who reads dollars', async () => {
    stubRoutes(routes())
    renderSignedIn(<Dashboard />, { ...OWNER, display_currency: 'USD' })

    const summary = await screen.findByRole('region', { name: 'Summary' })
    expect(await within(summary).findByText('-US$100.00')).toBeTruthy()
    expect(within(summary).getByText('+US$200.00')).toBeTruthy()
    expect(within(summary).getByText('US$500.00')).toBeTruthy()
    expect(rows('Spent by payment method')).toEqual([
      'CashUS$350.00',
      'Credit cardUS$150.00',
    ])
  })

  it('opens the expenses behind a row on Transactions', async () => {
    stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    await userEvent.click(await screen.findByRole('button', { name: /^Credit card/ }))
    await userEvent.click(screen.getByRole('button', { name: /^Supermarket/ }))
    expect(push.mock.calls).toEqual([
      ['/transactions?property=p2&type=expense&method=credit+card'],
      ['/transactions?property=p2&type=expense&category=supermarket'],
    ])
  })

  it('picks a month since the first entry, and keeps it in the address', async () => {
    stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    await userEvent.click(await screen.findByRole('combobox', { name: 'Month' }))
    expect(
      (await screen.findAllByRole('option')).map((option) => option.textContent),
    ).toEqual(['November 2026', 'October 2026', 'September 2026'])
    await userEvent.click(screen.getByRole('option', { name: 'September 2026' }))
    expect(replace).toHaveBeenCalledWith('/dashboard?month=2026-09', { scroll: false })
  })

  it('offers no choice of house to a homeowner with one', async () => {
    stubRoutes(routes([house('p2', 'Campo 9')]))
    renderSignedIn(<Dashboard />, HOMEOWNER)

    await screen.findByRole('region', { name: 'Where it went' })
    expect(screen.queryByRole('combobox', { name: 'Property' })).toBeNull()
  })

  it('says when nothing was spent', async () => {
    stubRoutes({
      ...routes(),
      '/v1/properties/p2/statement': {
        status: 200,
        body: {
          ...STATEMENT,
          expense_total: 0,
          expenses_by_method: [],
          expenses_by_category: [],
        },
      },
    })
    renderSignedIn(<Dashboard />)

    expect(await screen.findByText('Nothing spent in November 2026')).toBeTruthy()
  })
})
