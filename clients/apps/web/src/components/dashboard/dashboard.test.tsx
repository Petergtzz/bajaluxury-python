import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { HOMEOWNER } from '@/test/fixtures'
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

afterEach(() => {
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

const expense = (
  category: string,
  method: string | null,
  amount: number,
  affects: boolean,
) => ({
  id: `${category}-${method}`,
  date: '2026-11-03',
  type: 'expense',
  category,
  concept: category,
  payment_method: method,
  description: null,
  amount,
  affects_balance: affects,
  balance_after: 0,
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
  income_total: 0,
  expense_total: 8500,
  balance_expense_total: 6000,
  expenses_by_method: [
    { payment_method: 'cash', total: 6000 },
    { payment_method: 'credit card', total: 2500 },
  ],
  expenses_by_category: [
    { category: 'services', total: 6000, entries: [] },
    { category: 'supermarket', total: 2500, entries: [] },
  ],
  entries: [
    expense('services', 'cash', 6000, true),
    expense('supermarket', 'credit card', 2500, false),
  ],
}

const routes = (properties = [house('p1', 'Colinas 21'), house('p2', 'Campo 9')]) => ({
  '/v1/properties/': { status: 200, body: properties },
  '/v1/properties/p2/statement': { status: 200, body: STATEMENT },
})

describe('Dashboard', () => {
  it('shows the first house: what it spent, where and how', async () => {
    const calls = stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    const summary = await screen.findByRole('region', { name: 'Summary' })
    expect(await within(summary).findByText(/8,500\.00/)).toBeTruthy()
    expect(within(summary).getByText('Paid from the balance')).toBeTruthy()
    expect(within(summary).getByText('Balance today')).toBeTruthy()
    expect(calls.requested.find((r) => r.includes('statement'))).toMatch(
      /^\/v1\/properties\/p2\/statement\?start=\d{4}-\d{2}-01&end=/,
    )

    const where = screen.getByRole('region', { name: 'Where it went' })
    expect(
      within(where)
        .getAllByRole('listitem')
        .map((r) => r.textContent),
    ).toEqual([
      expect.stringMatching(/^71%Services.*6,000\.00/),
      expect.stringMatching(/^29%Supermarket.*2,500\.00/),
    ])
    const how = screen.getByRole('region', { name: 'How it was paid' })
    expect(
      within(how)
        .getAllByRole('listitem')
        .map((r) => r.textContent),
    ).toEqual([
      expect.stringContaining('CashFrom balance'),
      expect.stringContaining('Credit cardPaid apart'),
    ])
  })

  it('opens the expenses behind a row on Transactions', async () => {
    stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    await userEvent.click(await screen.findByRole('button', { name: /^Supermarket/ }))
    expect(push).toHaveBeenCalledWith(
      '/transactions?property=p2&type=expense&category=supermarket',
    )
  })

  it('keeps another house in the address', async () => {
    stubRoutes(routes())
    renderSignedIn(<Dashboard />)

    await userEvent.click(await screen.findByLabelText('Property'))
    await userEvent.click(await screen.findByRole('option', { name: 'Colinas 21' }))
    expect(replace).toHaveBeenCalledWith('/dashboard?property=p1', { scroll: false })
  })

  it('offers no choice of house to a homeowner with one', async () => {
    stubRoutes(routes([house('p2', 'Campo 9')]))
    renderSignedIn(<Dashboard />, HOMEOWNER)

    await screen.findByRole('region', { name: 'Where it went' })
    expect(screen.queryByLabelText('Property')).toBeNull()
  })

  it('says when nothing was spent', async () => {
    stubRoutes({
      ...routes(),
      '/v1/properties/p2/statement': {
        status: 200,
        body: {
          ...STATEMENT,
          expense_total: 0,
          balance_expense_total: 0,
          expenses_by_method: [],
          expenses_by_category: [],
          entries: [],
        },
      },
    })
    renderSignedIn(<Dashboard />)

    expect(await screen.findByText(/^Nothing spent · /)).toBeTruthy()
  })
})
