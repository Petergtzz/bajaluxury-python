import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Checklist } from '@/lib/api/types'
import { HOMEOWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { ChecklistRun } from './checklist-run'
import { Checklists } from './checklists'

const push = vi.fn()
const replace = vi.fn()
let search = 'tab=history'
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace }),
  usePathname: () => '/checklists',
  useSearchParams: () => new URLSearchParams(search),
}))
const toastSuccess = vi.fn()
vi.mock('sonner', () => ({
  toast: { success: (m: string) => toastSuccess(m), error: vi.fn() },
}))

afterEach(() => {
  vi.unstubAllGlobals()
  search = 'tab=history'
  replace.mockReset()
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
  emailed_cc: [],
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

describe('Checklists, the properties tab', () => {
  it('says who hears about each property, and changes it in its dialog', async () => {
    search = ''
    const calls = stubRoutes({
      '/v1/checklists/properties': {
        status: 200,
        body: [
          {
            property_id: 'p1',
            property_name: 'Colinas 21',
            recipients: [
              { user_id: 'u2', email: 'ana@example.com', name: 'Ana', kind: 'to' },
            ],
          },
          { property_id: 'p2', property_name: 'Campo 9', recipients: [] },
        ],
      },
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
            id: 'u4',
            email: 'luis@example.com',
            name: 'Luis',
            role: 'manager',
            property_ids: [],
          },
        ],
      },
      '/v1/checklists/properties/p1': { status: 200, body: {} },
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Checklists />)

    expect(await screen.findByText('Ana')).toBeTruthy()
    expect(screen.getByText('Nobody hears about it')).toBeTruthy()

    await userEvent.click(screen.getByText('Colinas 21'))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(await within(dialog).findByLabelText('Luis'))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Colinas 21 checklists will be sent'),
    )
    expect(calls.find((call) => call.method === 'PUT')).toMatchObject({
      path: '/v1/checklists/properties/p1',
      body: {
        recipients: [
          { user_id: 'u2', kind: 'to' },
          { user_id: 'u4', kind: 'cc' },
        ],
      },
    })
  })

  it('leaves the tabs out for a homeowner, who sees only the walks', async () => {
    search = ''
    const calls = stubRoutes({
      '/v1/checklists/': { status: 200, body: [] },
      '/v1/company': COMPANY,
    })
    renderSignedIn(<Checklists />, HOMEOWNER)

    expect(await screen.findByText('No checklists of your properties yet.')).toBeTruthy()
    expect(screen.queryByRole('tablist')).toBeNull()
    expect(calls.some((call) => call.path === '/v1/checklists/properties')).toBe(false)
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

  it('finishes in one tap, sending to whoever the property names', async () => {
    const calls = stubRoutes({
      '/v1/checklists/c1': { status: 200, body: OPEN },
      '/v1/properties/': PROPERTIES,
      '/v1/checklists/c1/complete': {
        status: 200,
        body: {
          ...OPEN,
          completed_at: '2026-11-20T18:00:00Z',
          emailed_to: ['ana@example.com'],
        },
      },
    })
    renderSignedIn(<ChecklistRun checklistId="c1" />)

    await userEvent.click(await screen.findByRole('button', { name: 'Finish checklist' }))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Checklist finished'))
    expect(
      calls.find((call) => call.path === '/v1/checklists/c1/complete'),
    ).toMatchObject({
      method: 'POST',
      body: undefined,
    })
    // It stays, frozen, as what was sent.
    expect(await screen.findByText('Check-in · 1 of 2 · finished')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Finish checklist' })).toBeNull()
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
