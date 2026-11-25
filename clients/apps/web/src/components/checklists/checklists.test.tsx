import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Checklist } from '@/lib/api/types'
import { HOMEOWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { ChecklistRun } from './checklist-run'
import { Checklists } from './checklists'

const push = vi.fn()
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
  usePathname: () => '/checklists',
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

const item = (id: string, description: string, is_checked = false) => ({
  id,
  description,
  position: 1,
  is_checked,
  note: null,
  checked_at: null,
})

const OPEN: Checklist = {
  id: 'c1',
  property_id: 'p1',
  type: 'check_in',
  created_by_id: 'u1',
  created_at: '2026-11-20T15:00:00Z',
  completed_at: null,
  emailed_to: [],
  items: [item('i1', 'Water tank', true), item('i2', 'Towels')],
}
const DONE: Checklist = {
  ...OPEN,
  id: 'c2',
  type: 'weekly',
  completed_at: '2026-11-19T18:00:00Z',
  emailed_to: ['ana@example.com'],
  items: [item('i3', 'Pool', true)],
}
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

describe('Checklists', () => {
  it('pins the walks under way and counts what each has ticked', async () => {
    stubRoutes({
      '/v1/checklists/': { status: 200, body: [OPEN, DONE] },
      '/v1/properties/': PROPERTIES,
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Checklists />)

    const open = await screen.findByRole('region', { name: 'In progress' })
    expect(within(open).getByText('1 of 2')).toBeTruthy()
    expect(within(open).getByText('Check-in')).toBeTruthy()
    expect(screen.getByText('Weekly · sent to ana@example.com')).toBeTruthy()

    await userEvent.click(within(open).getByText('Colinas 21'))
    expect(push).toHaveBeenCalledWith('/checklists/c1')
  })

  it('lets a homeowner read, and start nothing', async () => {
    stubRoutes({ '/v1/checklists/': { status: 200, body: [] }, '/v1/company': COMPANY })
    renderSignedIn(<Checklists />, HOMEOWNER)

    expect(await screen.findByText('No checklists of your properties yet.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Start checklist' })).toBeNull()
  })
})

describe('A walk', () => {
  it('ticks an item with one tap on its row', async () => {
    const calls = stubRoutes({
      '/v1/checklists/c1': { status: 200, body: OPEN },
      '/v1/properties/': PROPERTIES,
      '/v1/checklists/c1/items/i2': {
        status: 200,
        body: { ...OPEN, items: [OPEN.items[0], { ...OPEN.items[1], is_checked: true }] },
      },
    })
    renderSignedIn(<ChecklistRun checklistId="c1" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Towels' }))

    await waitFor(() => expect(screen.getByText('Check-in · 2 of 2')).toBeTruthy())
    expect(calls.find((call) => call.method === 'PATCH')).toMatchObject({
      path: '/v1/checklists/c1/items/i2',
      body: { is_checked: true },
    })
  })

  it('emails the finished walk to the property’s owners, and anyone added', async () => {
    const calls = stubRoutes({
      '/v1/checklists/c1': { status: 200, body: OPEN },
      '/v1/properties/': PROPERTIES,
      '/v1/users/': {
        status: 200,
        body: [
          {
            id: 'u2',
            email: 'ana@example.com',
            name: 'Ana',
            role: 'homeowner',
            property_ids: ['p1'],
          },
          {
            id: 'u3',
            email: 'eva@example.com',
            name: 'Eva',
            role: 'homeowner',
            property_ids: ['p9'],
          },
          {
            id: 'u4',
            email: 'luis@example.com',
            name: 'Luis',
            role: 'manager',
            property_ids: [],
          },
        ],
      },
      '/v1/checklists/c1/complete': {
        status: 200,
        body: { ...OPEN, completed_at: '2026-11-20T18:00:00Z' },
      },
    })
    renderSignedIn(<ChecklistRun checklistId="c1" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Finish checklist' }))
    const dialog = await screen.findByRole('dialog')
    // The owner of this property is ticked; one of another property isn't offered.
    await waitFor(() =>
      expect(within(dialog).getByLabelText('Ana').getAttribute('data-state')).toBe(
        'checked',
      ),
    )
    expect(within(dialog).queryByLabelText('Eva')).toBeNull()
    expect(within(dialog).queryByText('To')).toBeNull()
    await userEvent.type(
      within(dialog).getByPlaceholderText('email@example.com'),
      'guest@example.com',
    )
    await userEvent.click(within(dialog).getByRole('button', { name: 'Finish and send' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Checklist finished, sent to 2 people'),
    )
    expect(
      calls.find((call) => call.path === '/v1/checklists/c1/complete')?.body,
    ).toEqual({
      recipients: ['ana@example.com', 'guest@example.com'],
    })
    expect(push).toHaveBeenCalledWith('/checklists')
  })

  it('is read only for a homeowner', async () => {
    stubRoutes({
      '/v1/checklists/c1': { status: 200, body: OPEN },
      '/v1/properties/': PROPERTIES,
    })
    renderSignedIn(<ChecklistRun checklistId="c1" />, HOMEOWNER)

    expect(
      (await screen.findByRole('button', { name: 'Towels' })).hasAttribute('disabled'),
    ).toBe(true)
    expect(screen.queryByRole('button', { name: 'Finish checklist' })).toBeNull()
    expect(screen.queryByRole('button', { name: /note/ })).toBeNull()
  })
})
