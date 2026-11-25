import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderSignedIn, stubLists, stubRoutes } from '@/test/render'

import { Charges } from './charges'
import { CompanySettings } from './company-settings'
import { ConnectionsSettings } from './connections-settings'
import { Options } from './options'

const refresh = vi.fn()
const replace = vi.fn()
let search = ''
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh, replace, push: vi.fn() }),
  usePathname: () => '/settings/charges',
  useSearchParams: () => new URLSearchParams(search),
}))
const toastSuccess = vi.fn()
vi.mock('sonner', () => ({
  toast: { success: (m: string) => toastSuccess(m), error: vi.fn() },
}))

afterEach(() => {
  vi.unstubAllGlobals()
  toastSuccess.mockReset()
  replace.mockReset()
  search = ''
})

const COMPANY = {
  status: 200,
  body: {
    name: 'Baja Luxury',
    currency: 'MXN',
    timezone: 'America/Mazatlan',
    usd_exchange_rate: '17.0000',
  },
}
const PROPERTIES = {
  status: 200,
  body: [
    {
      id: 'p1',
      name: 'Colinas 21',
      address: null,
      is_archived: false,
      balance_methods: ['cash'],
      created_at: '2026-09-01T00:00:00Z',
    },
  ],
}

describe('Options', () => {
  it('rewrites a checklist whole: reworded, moved, added to and trimmed', async () => {
    const calls = stubRoutes({
      '/v1/checklist-templates/': {
        status: 200,
        body: [
          { id: 'a', type: 'check_in', description: 'Keys in the lockbox', position: 1 },
          { id: 'b', type: 'check_in', description: 'Pool is clean', position: 2 },
          { id: 'c', type: 'weekly', description: 'Run every tap', position: 1 },
        ],
      },
      '/v1/checklist-templates/check_in': { status: 200, body: [] },
    })
    renderSignedIn(<Options />)

    expect(await screen.findByText('2 items')).toBeTruthy()
    expect(screen.getByText('Nothing on it yet')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Edit Check-in' }))
    const dialog = await screen.findByRole('dialog')
    const [keys, pool] = within(dialog).getAllByLabelText('What to look at')
    await userEvent.clear(pool!)
    await userEvent.type(pool!, 'Pool and jacuzzi')
    await userEvent.click(
      within(dialog).getByRole('button', { name: 'Move Pool and jacuzzi up' }),
    )
    await userEvent.click(
      within(dialog).getByRole('button', { name: 'Remove Keys in the lockbox' }),
    )
    await userEvent.click(within(dialog).getByRole('button', { name: 'Add item' }))
    await userEvent.type(
      within(dialog).getAllByLabelText('What to look at').at(-1)!,
      'Gas',
    )
    expect(keys).toBeTruthy()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Check-in saved'))
    expect(calls.find((call) => call.method === 'PUT')).toMatchObject({
      path: '/v1/checklist-templates/check_in',
      body: {
        items: [{ id: 'b', description: 'Pool and jacuzzi' }, { description: 'Gas' }],
      },
    })
  })
})

describe('Charges', () => {
  it('sets up what a house is charged every month', async () => {
    const calls = stubRoutes({
      '/v1/recurring-charges/': { status: 200, body: [] },
      '/v1/properties/': PROPERTIES,
      '/v1/shortcut/categories': { status: 200, body: { categories: ['services'] } },
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Charges />)

    expect(
      await screen.findByText(
        'Nothing is charged by itself yet. Add what a house pays every month.',
      ),
    ).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Add charge' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Amount'), '1,500')
    await userEvent.click(within(dialog).getByLabelText('Property'))
    await userEvent.click(await screen.findByRole('option', { name: 'Colinas 21' }))
    await userEvent.type(within(dialog).getByPlaceholderText('services'), 'services')
    await userEvent.type(within(dialog).getByPlaceholderText('gardener'), 'gardener')
    await userEvent.click(within(dialog).getByLabelText('Day of the month'))
    await userEvent.click(await screen.findByRole('option', { name: 'Last day' }))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Add charge' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Colinas 21 is charged monthly'),
    )
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({
      property_id: 'p1',
      amount: '1500',
      category: 'services',
      concept: 'gardener',
      payment_method: 'cash',
      day_of_month: 31,
      description: null,
    })
  })
})

describe('Charges, before the houses have loaded', () => {
  it('still keeps each house’s charges together', async () => {
    const charge = (id: string, property_id: string, day_of_month: number) => ({
      id,
      property_id,
      amount: 100,
      payment_method: 'cash',
      category: 'services',
      concept: `charge ${id}`,
      description: null,
      day_of_month,
      next_charge_on: '2026-12-01',
      created_at: '2026-09-01T00:00:00Z',
    })
    stubRoutes({
      '/v1/recurring-charges/': {
        status: 200,
        body: [charge('a1', 'pa', 1), charge('b2', 'pb', 2), charge('a3', 'pa', 3)],
      },
      // No names yet: every house sorts as the same empty name.
      '/v1/properties/': { status: 200, body: [] },
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Charges />)

    await screen.findByText('Charge a1')
    // One list per house.
    expect(screen.getAllByRole('list')).toHaveLength(2)
  })
})

describe('Charges, filtered', () => {
  const charge = (id: string, property_id: string, concept: string, amount: number) => ({
    id,
    property_id,
    amount,
    payment_method: 'cash',
    category: 'staff',
    concept,
    description: null,
    day_of_month: 10,
    next_charge_on: '2026-12-10',
    created_at: '2026-09-01T00:00:00Z',
  })
  const routes = () => ({
    '/v1/recurring-charges/': {
      status: 200,
      body: [
        charge('a', 'p1', 'property management', 8500),
        charge('b', 'p1', 'landscaping', 7000),
        charge('c', 'p2', 'landscaping', 1500),
      ],
    },
    '/v1/properties/': {
      status: 200,
      body: [
        { ...PROPERTIES.body[0] },
        { ...PROPERTIES.body[0], id: 'p2', name: 'Campo 9' },
      ],
    },
    '/v1/company': COMPANY,
  })

  it('shows one kind of charge, and what it comes to each month', async () => {
    search = 'what=landscaping'
    stubRoutes(routes())
    renderSignedIn(<Charges />)

    expect(await screen.findByText('Landscaping · each month')).toBeTruthy()
    expect(screen.getByText('MX$8,500.00')).toBeTruthy()
    expect(screen.queryByText('Property management')).toBeNull()
    expect(screen.getAllByText('Landscaping')).toHaveLength(2)
  })

  it('narrows to a kind from its chip, keeping it in the address', async () => {
    stubRoutes(routes())
    renderSignedIn(<Charges />)

    expect(await screen.findByText('MX$17,000.00')).toBeTruthy()
    await userEvent.click(screen.getByLabelText('What it is for'))
    await userEvent.click(await screen.findByRole('option', { name: 'Landscaping (2)' }))

    expect(replace).toHaveBeenCalledWith('/settings/charges?what=landscaping', {
      scroll: false,
    })
  })
})

describe('Connections', () => {
  it('shows a new token once, to copy into the Shortcut', async () => {
    const sent = stubLists(
      { '/v1/api-tokens/': [], '/v1/company': COMPANY.body as unknown as unknown[] },
      {
        status: 201,
        body: {
          id: 't1',
          label: 'Ana’s iPhone',
          user: { id: 'u1', email: 'pedro@example.com', name: 'Pedro' },
          last_used_at: null,
          created_at: '2026-11-25T18:00:00Z',
          token: 'baja_at_secret',
        },
      },
    )
    renderSignedIn(<ConnectionsSettings />)

    expect(await screen.findByText('No devices connected yet.')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'New connection' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(
      within(dialog).getByLabelText('Name this device'),
      ' Ana’s iPhone ',
    )
    await userEvent.click(
      within(dialog).getByRole('button', { name: 'Create connection' }),
    )

    expect(await screen.findByText('baja_at_secret')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Copy your token now' })).toBeTruthy()
    expect(sent).toEqual([
      { method: 'POST', path: '/v1/api-tokens/', body: { label: 'Ana’s iPhone' } },
    ])
  })
})

describe('Company', () => {
  it('saves a new exchange rate, said as people say it', async () => {
    const calls = stubRoutes({
      '/v1/company': COMPANY,
    })
    renderSignedIn(<CompanySettings />)

    const rate = await screen.findByLabelText('Exchange rate')
    expect((rate as HTMLInputElement).value).toBe('17')
    await userEvent.clear(rate)
    await userEvent.type(rate, '17.25')
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Company saved'))
    expect(calls.find((call) => call.method === 'PATCH')?.body).toEqual({
      usd_exchange_rate: '17.25',
    })
  })
})
