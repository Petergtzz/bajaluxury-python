import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Member, Report } from '@/lib/api/types'
import { renderSignedIn, stubAPI } from '@/test/render'

import { ReportDialog } from './report-dialog'

const toastSuccess = vi.fn()
vi.mock('sonner', () => ({
  toast: { success: (m: string) => toastSuccess(m), error: vi.fn() },
}))

afterEach(() => {
  vi.unstubAllGlobals()
  toastSuccess.mockReset()
})

const member = (
  id: string,
  role: Member['role'],
  name: string | null,
  properties: string[] = role === 'homeowner' ? ['p1'] : [],
) => ({
  id,
  email: `${id}@example.com`,
  name,
  role,
  property_ids: properties,
})

const REPORT: Report = {
  property_id: 'p1',
  property_name: 'Colinas 21',
  recipients: [],
  last_sent_at: null,
  send_day: 1,
}

const members = (...items: ReturnType<typeof member>[]) =>
  [200, items] as [number, unknown]

const show = (report: Report = REPORT) =>
  renderSignedIn(<ReportDialog report={report} open onOpenChange={vi.fn()} />)

describe('ReportDialog', () => {
  it('addresses the homeowner and copies everyone else', async () => {
    const calls = stubAPI(
      members(member('u1', 'manager', 'Luis'), member('u2', 'homeowner', 'Ana')),
      [200, { ...REPORT, recipients: [] }],
    )
    show()

    // Ticking is all it takes: an owner is addressed, the team is copied.
    await userEvent.click(await screen.findByLabelText('Ana'))
    await userEvent.click(screen.getByLabelText('Luis'))
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Colinas 21 reports monthly'),
    )
    expect(calls.at(-1)).toMatchObject({
      method: 'PUT',
      path: '/v1/reports/properties/p1',
      body: {
        recipients: [
          { user_id: 'u2', kind: 'to' },
          { user_id: 'u1', kind: 'cc' },
        ],
      },
    })
  })

  it('says who would be addressed and who copied, before anything is ticked', async () => {
    stubAPI(members(member('u1', 'manager', 'Luis'), member('u2', 'homeowner', 'Ana')))
    show()

    // The owner leads the list and is the addressee; the manager is copied.
    await screen.findByLabelText('Ana')
    const rows = screen.getAllByRole('checkbox')
    expect(rows.map((row) => row.getAttribute('aria-label'))).toEqual(['Ana', 'Luis'])
    expect(screen.getAllByText('To')).toHaveLength(1)
    expect(screen.getAllByText('Cc')).toHaveLength(1)

    // With only the manager ticked there is nobody else to address it to.
    await userEvent.click(screen.getByLabelText('Luis'))
    expect(screen.getAllByText('To')).toHaveLength(2)
    expect(screen.queryByText('Cc')).toBeNull()
  })

  it('addresses the team directly when the owner is left off', async () => {
    const calls = stubAPI(
      members(member('u1', 'manager', 'Luis'), member('u2', 'homeowner', 'Ana')),
      [200, { ...REPORT, recipients: [] }],
    )
    show()

    await screen.findByLabelText('Ana')
    await userEvent.click(screen.getByLabelText('Luis'))

    // There was an owner to tick, so the dialog says what leaving them off did.
    expect(
      screen.getByText('No owner is ticked, so it is addressed to the people who are.'),
    ).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Colinas 21 reports monthly'),
    )
    expect(calls.at(-1)).toMatchObject({
      body: { recipients: [{ user_id: 'u1', kind: 'to' }] },
    })
  })

  it('only offers homeowners who can see the property', async () => {
    stubAPI(
      members(
        member('u1', 'owner', 'Pedro'),
        member('u2', 'homeowner', 'Ana'),
        member('u3', 'homeowner', 'Carlos', ['p9']),
      ),
    )
    show()

    expect(await screen.findByLabelText('Ana')).toBeTruthy()
    expect(screen.getByLabelText('Pedro')).toBeTruthy()
    await waitFor(() => expect(screen.queryByLabelText('Carlos')).toBeNull())
  })

  it('turns the report off when the last person is unticked', async () => {
    const on: Report = {
      ...REPORT,
      recipients: [{ user_id: 'u2', email: 'u2@example.com', name: 'Ana', kind: 'to' }],
    }
    const calls = stubAPI(
      members(member('u1', 'owner', 'Pedro'), member('u2', 'manager', 'Ana')),
      [204],
    )
    show(on)

    await userEvent.click(await screen.findByLabelText('Ana'))
    await userEvent.click(screen.getByRole('button', { name: 'Turn off' }))

    await waitFor(() =>
      expect(toastSuccess).toHaveBeenCalledWith('Colinas 21 stopped sending reports'),
    )
    expect(calls[1]).toMatchObject({
      method: 'DELETE',
      path: '/v1/reports/properties/p1',
    })
  })

  it('says Turn off once, whether or not anybody is still ticked', async () => {
    stubAPI(members(member('u1', 'owner', 'Pedro'), member('u2', 'manager', 'Ana')))
    show({
      ...REPORT,
      recipients: [{ user_id: 'u2', email: 'u2@example.com', name: 'Ana', kind: 'to' }],
    })

    const ana = await screen.findByLabelText('Ana')
    expect(screen.getAllByRole('button', { name: 'Turn off' })).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Save' })).toBeTruthy()

    await userEvent.click(ana)

    expect(screen.getAllByRole('button', { name: 'Turn off' })).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Save' })).toBeNull()
  })

  it('has nothing to save while a report that is off has nobody ticked', async () => {
    stubAPI(members(member('u1', 'owner', 'Pedro')))
    show()

    await screen.findByLabelText('Pedro')

    expect(screen.getByRole('button', { name: 'Save' })).toHaveProperty('disabled', true)
  })

  it('says when nobody can see the property', async () => {
    stubAPI(members())
    show()

    expect(
      await screen.findByText(
        'Nobody can see this property yet. Assign it to someone first.',
      ),
    ).toBeTruthy()
  })
})
