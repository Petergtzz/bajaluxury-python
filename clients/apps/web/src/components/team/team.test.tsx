import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { User } from '@/lib/api/types'
import { OWNER } from '@/test/fixtures'
import { renderSignedIn, stubRoutes } from '@/test/render'

import { Properties } from './properties'
import { Users } from './users'

const replace = vi.fn()
let search = ''
vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
  usePathname: () => '/team',
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

const COLINAS = {
  id: 'p1',
  name: 'Colinas 21',
  address: 'Calle 21, Cabo',
  is_archived: false,
  balance_methods: ['cash'],
  created_at: '2026-09-01T00:00:00Z',
}
const SOLD = { ...COLINAS, id: 'p2', name: 'Soleil', address: null, is_archived: true }
const PROPERTIES = { '/v1/properties/': { status: 200, body: [SOLD, COLINAS] } }

const person = (
  id: string,
  name: string,
  role: User['role'],
  property_ids: string[] = [],
) => ({
  id,
  email: `${name.toLowerCase()}@example.com`,
  name,
  role,
  property_ids,
})
const USERS = {
  '/v1/users/': {
    status: 200,
    body: [
      { ...person('u1', 'Pedro', 'owner'), email: OWNER.email },
      person('u2', 'Ana', 'homeowner', ['p1']),
      person('u3', 'Luis', 'manager'),
    ],
  },
}

describe('Properties', () => {
  it('starts on the houses managed today, with what their balance pays', async () => {
    stubRoutes(PROPERTIES)
    renderSignedIn(<Properties />)

    await screen.findByText('Colinas 21')
    expect(screen.getByText('1 property')).toBeTruthy()
    expect(screen.getAllByRole('listitem').map((row) => row.textContent)).toEqual([
      expect.stringContaining('Colinas 21Calle 21, Cabo · Balance pays cash'),
    ])

    await userEvent.click(screen.getByLabelText('Which properties'))
    await userEvent.click(await screen.findByRole('option', { name: 'Archived' }))
    expect(replace).toHaveBeenCalledWith('/team?status=archived', { scroll: false })
  })

  it('shows the archived ones when the address asks', async () => {
    search = 'status=archived'
    stubRoutes(PROPERTIES)
    renderSignedIn(<Properties />)

    expect(await screen.findByText('Soleil')).toBeTruthy()
    expect(screen.queryByText('Colinas 21')).toBeNull()
  })

  it('adds a house that pays debit card expenses from its balance too', async () => {
    const calls = stubRoutes({
      ...PROPERTIES,
      '/v1/properties/': { status: 200, body: [] },
    })
    renderSignedIn(<Properties />)

    await userEvent.click(await screen.findByRole('button', { name: 'Add property' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(within(dialog).getByLabelText('Name'), 'Campo 9')
    await userEvent.click(within(dialog).getByLabelText('Debit card'))
    await userEvent.click(within(dialog).getByRole('button', { name: 'Add property' }))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Property added'))
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({
      name: 'Campo 9',
      address: null,
      balance_methods: ['cash', 'debit card'],
    })
  })
})

describe('Users', () => {
  it('lets an owner add someone, who logs in with that address', async () => {
    const calls = stubRoutes({ ...PROPERTIES, ...USERS })
    renderSignedIn(<Users />)

    await userEvent.click(await screen.findByRole('button', { name: 'Add person' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.type(
      within(dialog).getByLabelText('Email address'),
      'eva@example.com',
    )
    await userEvent.type(within(dialog).getByLabelText('Name'), 'Eva')
    await userEvent.click(within(dialog).getByLabelText('Role'))
    await userEvent.click(await screen.findByRole('option', { name: 'Homeowner' }))
    // A homeowner sees only the houses ticked; one archived isn't offered.
    await userEvent.click(within(dialog).getByLabelText('Colinas 21'))
    expect(within(dialog).queryByLabelText('Soleil')).toBeNull()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Add person' }))

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith('Eva can log in now'))
    expect(calls.find((call) => call.method === 'POST')?.body).toEqual({
      email: 'eva@example.com',
      name: 'Eva',
      role: 'homeowner',
      property_ids: ['p1'],
    })
  })

  it('opens neither owners nor yourself, and says which houses a homeowner sees', async () => {
    stubRoutes({ ...PROPERTIES, ...USERS })
    renderSignedIn(<Users />)

    expect(await screen.findByText('Homeowner · Colinas 21')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Pedro, Owner' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Ana, Homeowner' })).toBeTruthy()
  })

  it('narrows to the homeowners of one house', async () => {
    search = 'property=p1'
    stubRoutes({ ...PROPERTIES, ...USERS })
    renderSignedIn(<Users />)

    expect(await screen.findByText('Ana')).toBeTruthy()
    expect(screen.getByText('1 person')).toBeTruthy()
    expect(screen.queryByText('Luis')).toBeNull()
  })

  it('narrows to a role from its chip', async () => {
    stubRoutes({ ...PROPERTIES, ...USERS })
    renderSignedIn(<Users />)

    await userEvent.click(await screen.findByLabelText('Role'))
    await userEvent.click(await screen.findByRole('option', { name: 'Managers' }))
    expect(replace).toHaveBeenCalledWith('/team?role=manager', { scroll: false })
  })

  it('shows a manager the team, and nothing to change', async () => {
    stubRoutes({ ...PROPERTIES, ...USERS })
    renderSignedIn(<Users />, { ...OWNER, id: 'u3', role: 'manager' })

    expect(await screen.findByText('Ana')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Add person' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Ana, Homeowner' })).toBeNull()
  })
})
