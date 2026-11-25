import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Report, SentStatement } from '@/lib/api/types'
import { HOMEOWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { Reports } from './reports'

let search = ''
const replace = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
  usePathname: () => '/reports',
  useSearchParams: () => new URLSearchParams(search),
}))
const toastSuccess = vi.fn()
const toastError = vi.fn()
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => toastSuccess(m),
    error: (m: string) => toastError(m),
  },
}))

const REPORTS = '/v1/reports/properties/'
const SENDS = '/v1/reports/sends/'
const FAILED = '/v1/reports/sends/count'

/** Answers each endpoint by its path: the page asks for three things at once. */

const list = (items: unknown[]) => ({ status: 200, body: items })

const OFF: Report = {
  property_id: 'p1',
  property_name: 'Colinas 21',
  recipients: [],
  last_sent_at: null,
  send_day: 1,
}

const ON: Report = {
  property_id: 'p2',
  property_name: 'Casa Azul 12',
  recipients: [{ user_id: 'u2', email: 'ana@example.com', name: 'Ana Ruiz', kind: 'to' }],
  last_sent_at: '2026-09-01T06:00:00Z',
  send_day: 5,
}

const SENT: SentStatement = {
  id: 's1',
  property_id: 'p2',
  property_name: 'Casa Azul 12',
  month: '2026-08-01',
  status: 'sent',
  sent_at: '2026-09-05T14:00:00Z',
  to: ['ana@example.com'],
  cc: ['luis@example.com'],
  error: null,
  has_statement: true,
}

const FAILED_SEND: SentStatement = {
  ...SENT,
  id: 's2',
  property_id: 'p1',
  property_name: 'Colinas 21',
  status: 'failed',
  sent_at: null,
  to: ['rosa@example.com'],
  cc: [],
  error: 'The mailbox was full.',
  has_statement: false,
}

beforeEach(() => {
  search = ''
  replace.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
  toastSuccess.mockReset()
  toastError.mockReset()
})

describe('Reports, the properties tab', () => {
  it('says who each property reports to, and when', async () => {
    stubRoutes({ [REPORTS]: list([OFF, ON]) })
    renderSignedIn(<Reports />)

    expect(await screen.findByText('Colinas 21')).toBeTruthy()
    expect(screen.getByText('Not sending')).toBeTruthy()
    expect(screen.getByText('Monthly to Ana Ruiz · on the 5th')).toBeTruthy()
    // When it last went is the History tab's business, not this one's.
    expect(screen.queryByText(/^Sent /)).toBeNull()
    // Each row opens its property, and nothing else waits at its end.
    expect(screen.queryByRole('button', { name: /^More for/ })).toBeNull()
    expect(screen.queryByRole('button', { name: /^(Set up|Edit) / })).toBeNull()
  })

  it('opens a property from its row', async () => {
    stubRoutes({ [REPORTS]: list([OFF]) })
    renderSignedIn(<Reports />)

    await userEvent.click(await screen.findByText('Colinas 21'))

    expect(await screen.findByRole('heading', { name: 'Colinas 21' })).toBeTruthy()
  })

  it('sends from the page, offering only properties that are set up', async () => {
    const calls = stubRoutes({
      [REPORTS]: list([OFF, ON]),
      [`${REPORTS}p2/send`]: {
        status: 200,
        body: { month: '2026-08-01', recipient_count: 2 },
      },
    })
    renderSignedIn(<Reports />)

    await userEvent.click(await screen.findByRole('button', { name: 'Send report' }))

    // A property with nobody on its report has nowhere to send, so it is not
    // offered; the one that is set up is already chosen.
    await userEvent.click(await screen.findByLabelText('Property'))
    expect((await screen.findAllByRole('option')).map((one) => one.textContent)).toEqual([
      'Casa Azul 12',
    ])
    await userEvent.keyboard('{Escape}')

    await userEvent.click(screen.getByRole('button', { name: 'Send statement' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith(
        'August so far is on its way to 2 people',
      ),
    )
    expect(
      calls.some((call) => call.method === 'POST' && call.path === `${REPORTS}p2/send`),
    ).toBe(true)
  })

  it('sends a statement now and says where it went', async () => {
    const calls = stubRoutes({
      [REPORTS]: list([ON]),
      '/v1/reports/properties/p2/send': {
        status: 202,
        body: { month: '2026-08-01', recipient_count: 2 },
      },
    })
    renderSignedIn(<Reports />)
    await userEvent.click(await screen.findByRole('button', { name: 'Send report' }))

    // The dialog opens on the only property that is set up and on the last
    // complete month, which is what the schedule would send next.
    await userEvent.click(await screen.findByRole('button', { name: 'Send statement' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith(
        'August so far is on its way to 2 people',
      ),
    )
    const sent = calls.find(
      (call) => call.method === 'POST' && call.path === '/v1/reports/properties/p2/send',
    )
    // A month always goes with it, rather than the server guessing.
    const body = sent?.body as { month: string } | undefined
    expect(body?.month).toMatch(/^\d{4}-\d{2}-01$/)
  })

  it('offers no property to send while none is set up', async () => {
    stubRoutes({ [REPORTS]: list([OFF]) })
    renderSignedIn(<Reports />)

    await userEvent.click(await screen.findByRole('button', { name: 'Send report' }))

    // An empty list would open onto nothing: the row is held, and says why.
    const property = await screen.findByLabelText('Property')
    expect(property).toHaveProperty('disabled', true)
    expect(property.textContent).toContain('None set up')
    expect(
      screen.getByText(
        'No property is set up to report yet. Choose who receives one first.',
      ),
    ).toBeTruthy()
  })

  it('reports why a send was refused', async () => {
    stubRoutes({
      [REPORTS]: list([ON]),
      '/v1/reports/properties/p2/send': {
        status: 429,
        body: {
          error: 'TooManyRequests',
          detail: 'This report was just sent. Please wait before sending it again.',
        },
      },
    })
    renderSignedIn(<Reports />)
    await userEvent.click(await screen.findByRole('button', { name: 'Send report' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Send statement' }))

    // The refusal lands in the dialog, which stays open: the month is still
    // chosen and trying again is one click, not five.
    expect(
      await screen.findByText(
        'This report was just sent. Please wait before sending it again.',
      ),
    ).toBeTruthy()
    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('turns a report off from its dialog', async () => {
    const calls = stubRoutes({
      [REPORTS]: list([ON]),
      '/v1/reports/properties/p2': { status: 204 },
    })
    renderSignedIn(<Reports />)
    await userEvent.click(await screen.findByText('Casa Azul 12'))

    await userEvent.click(
      within(await screen.findByRole('dialog')).getByRole('button', {
        name: 'Turn off',
      }),
    )

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Casa Azul 12 stopped sending reports'),
    )
    expect(
      calls.some(
        (call) => call.method === 'DELETE' && call.path === '/v1/reports/properties/p2',
      ),
    ).toBe(true)
  })

  it('asks for a property before it can report on one', async () => {
    stubRoutes({ [REPORTS]: list([]) })
    renderSignedIn(<Reports />)

    expect(
      await screen.findByText(
        'No properties yet. Add one, then choose who hears about it.',
      ),
    ).toBeTruthy()
  })
})

describe('Reports, the history tab', () => {
  beforeEach(() => {
    search = 'tab=history'
  })

  it('lists what went out, grouped by the month it covers', async () => {
    stubRoutes({
      [REPORTS]: list([OFF, ON]),
      [SENDS]: list([SENT, FAILED_SEND]),
      [FAILED]: { status: 200, body: { count: 1 } },
    })
    renderSignedIn(<Reports />)

    const month = await screen.findByRole('region', { name: 'August 2026' })
    expect(month).toBeTruthy()
    expect(screen.getByText('to ana@example.com, cc luis@example.com')).toBeTruthy()
    expect(screen.getByText('Sent 5 Sept 2026')).toBeTruthy()
    // The month that didn't go says so plainly, and has no file to download.
    expect(screen.getByText('Not sent')).toBeTruthy()
    expect(screen.getByLabelText('Download Casa Azul 12, August 2026')).toBeTruthy()
    expect(screen.queryByLabelText('Download Colinas 21, August 2026')).toBeNull()
  })

  it('announces a month that did not go, once, above the list', async () => {
    stubRoutes({
      [REPORTS]: list([OFF, ON]),
      [SENDS]: list([SENT, FAILED_SEND]),
      [FAILED]: { status: 200, body: { count: 1 } },
    })
    renderSignedIn(<Reports />)

    const notice = await screen.findByRole('status')
    expect(notice.textContent).toContain("August 2026 didn't reach Colinas 21.")
    expect(notice.textContent).toContain('The mailbox was full.')
  })

  it('says nothing has gone out yet', async () => {
    stubRoutes({ [REPORTS]: list([ON]), [SENDS]: list([]) })
    renderSignedIn(<Reports />)

    expect(
      await screen.findByText(
        'Nothing has been sent yet. A statement shows up here on the day its property reports.',
      ),
    ).toBeTruthy()
    expect(screen.queryByRole('status')).toBeNull()
  })
})

describe('Reports, for a homeowner', () => {
  beforeEach(() => {
    search = ''
  })

  it('shows the statements of their properties and nothing to set up', async () => {
    const calls = stubRoutes({ [SENDS]: list([SENT]) })
    renderSignedIn(<Reports />, HOMEOWNER)

    // The record is the whole page: no tabs to choose, and it opens on it.
    expect(await screen.findByRole('region', { name: 'August 2026' })).toBeTruthy()
    expect(screen.queryByRole('tablist', { name: 'Reports' })).toBeNull()
    expect(screen.getByLabelText('Download Casa Azul 12, August 2026')).toBeTruthy()

    // Neither the setup list nor the failure count is theirs to ask for.
    expect(calls.some((call) => call.path === REPORTS)).toBe(false)
    expect(calls.some((call) => call.path === FAILED)).toBe(false)
  })
})
