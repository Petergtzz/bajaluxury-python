import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Invoice } from '@/lib/api/types'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { Invoices } from './invoices'
import { NewInvoice } from './new-invoice'

const push = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => '/invoices',
  useSearchParams: () => new URLSearchParams(),
}))
const toastSuccess = vi.fn()
vi.mock('sonner', () => ({
  toast: { success: (m: string) => toastSuccess(m), error: vi.fn() },
}))

afterEach(() => {
  vi.unstubAllGlobals()
  push.mockReset()
  toastSuccess.mockReset()
})

const PROPERTIES = {
  status: 200,
  body: [{ id: 'p1', name: 'Colinas 21', is_archived: false }],
}
const COMPANY = {
  status: 200,
  body: {
    name: 'Baja Luxury',
    currency: 'MXN',
    timezone: 'America/Mazatlan',
    usd_exchange_rate: 18,
  },
}
const INVOICE: Invoice = {
  id: 'v1',
  number: '2026-007',
  property_id: 'p1',
  recipient_name: 'Ana Guest',
  email: 'ana@example.com',
  issued_on: '2026-11-25',
  due_on: '2026-11-30',
  tax_rate: '0.1600',
  exchange_rate: '18.0000',
  subtotal: 1000,
  tax: 160,
  total: 1160,
  payment_details: null,
  notes: null,
  created_by_id: 'u1',
  sent_at: '2026-11-26T03:00:00Z',
  created_at: '2026-11-26T03:00:00Z',
  lines: [
    {
      id: 'l1',
      position: 1,
      description: 'Groceries',
      quantity: 1,
      unit_price: 1000,
      amount: 1000,
      guest_expense_id: null,
    },
  ],
}

describe('Invoices', () => {
  it('lists each month’s invoices with who, what and when they went', async () => {
    stubRoutes({
      '/v1/invoices/': { status: 200, body: [INVOICE] },
      '/v1/properties/': PROPERTIES,
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Invoices />)

    const month = await screen.findByRole('region', { name: 'November 2026' })
    // Sent in the evening in Los Cabos, which is already the next day in UTC.
    expect(month.textContent).toContain('2026-007 · Colinas 21 · Sent 25 Nov 2026')
    expect(within(month).getByText('MX$1,160.00')).toBeTruthy()
  })

  it('deletes an invoice from its dialog, after asking', async () => {
    const calls = stubRoutes({
      '/v1/invoices/': { status: 200, body: [INVOICE] },
      '/v1/properties/': PROPERTIES,
      '/v1/company': COMPANY,
      '/v1/invoices/v1': { status: 204 },
    })
    renderSignedIn(<Invoices />)

    await userEvent.click(await screen.findByText('Ana Guest'))
    await userEvent.click(await screen.findByRole('button', { name: 'Delete invoice' }))
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Delete invoice',
      }),
    )

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Invoice 2026-007 deleted'),
    )
    expect(
      calls.some((call) => call.method === 'DELETE' && call.path === '/v1/invoices/v1'),
    ).toBe(true)
  })
})

describe('A new invoice', () => {
  it('bills a stay’s guest expenses and sends what it showed', async () => {
    const calls = stubRoutes({
      '/v1/properties/': PROPERTIES,
      '/v1/company': COMPANY,
      '/v1/guest-expenses/': {
        status: 200,
        body: {
          items: [
            {
              id: 'g1',
              amount: 1500,
              concept: 'costco',
              description: null,
              date: '2026-11-20',
            },
            {
              id: 'g2',
              amount: 250.5,
              concept: 'ice',
              description: null,
              date: '2026-11-21',
            },
          ],
          pagination: { total_count: 2, max_page: 1 },
        },
      },
      '/v1/invoices/': { status: 201, body: { ...INVOICE, number: '2026-008' } },
    })
    renderSignedIn(<NewInvoice />)

    await userEvent.click(await screen.findByLabelText('Property'))
    await userEvent.click(await screen.findByRole('option', { name: 'Colinas 21' }))
    await userEvent.type(screen.getByPlaceholderText("Guest's name"), 'Ana Guest')
    await userEvent.type(
      screen.getByPlaceholderText('guest@example.com'),
      'ana@example.com',
    )
    await userEvent.click(
      await screen.findByRole('button', { name: 'Bill guest expenses (2)' }),
    )
    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Add 2 lines',
      }),
    )

    // 1,750.50 plus 16% is 2,030.58: what the server will charge.
    expect(await screen.findByText('MX$2,030.58')).toBeTruthy()
    // Everything there was to bill is on it.
    expect(screen.queryByRole('button', { name: /Bill guest expenses/ })).toBeNull()

    await userEvent.click(screen.getByRole('button', { name: 'Send invoice' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith(
        'Invoice 2026-008 is on its way to ana@example.com',
      ),
    )
    const sent = calls.find((call) => call.method === 'POST')?.body as Record<
      string,
      unknown
    >
    expect(sent).toMatchObject({
      property_id: 'p1',
      recipient_name: 'Ana Guest',
      tax_rate: 0.16,
      notes: 'Tip for staff is not included.',
      lines: [
        { description: 'Costco', quantity: 1, unit_price: 1500, guest_expense_id: 'g1' },
        { description: 'Ice', quantity: 1, unit_price: 250.5, guest_expense_id: 'g2' },
      ],
    })
    expect(push).toHaveBeenCalledWith('/invoices')
  })

  it('says what is missing rather than sending', async () => {
    const calls = stubRoutes({ '/v1/properties/': PROPERTIES, '/v1/company': COMPANY })
    renderSignedIn(<NewInvoice />)

    await userEvent.click(await screen.findByRole('button', { name: 'Send invoice' }))

    expect(await screen.findByText('Pick the property the stay was at.')).toBeTruthy()
    expect(calls.some((call) => call.method === 'POST')).toBe(false)
  })
})
