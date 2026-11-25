import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SessionProvider } from '@/components/session-context'
import type { User } from '@/lib/api/types'
import { HOMEOWNER, OWNER } from '@/test/fixtures'

import { SettingsLayout, SettingsPage } from './settings-layout'

let pathname = '/settings/options'
const replace = vi.fn()
vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ replace }),
}))

const MANAGER: User = { ...OWNER, id: 'u5', role: 'manager' }

const show = (user: User, title: string) =>
  render(
    <SessionProvider user={user}>
      <SettingsLayout>
        <SettingsPage title={title}>content</SettingsPage>
      </SettingsLayout>
    </SessionProvider>,
  )

const tabs = () =>
  within(screen.getByRole('navigation', { name: 'Settings' }))
    .getAllByRole('link')
    .map((link) => link.textContent)

describe('SettingsLayout', () => {
  it('puts the settings pages in a tab row, marking the open one', () => {
    pathname = '/settings/options'
    show(OWNER, 'Options')

    expect(tabs()).toEqual(['Company', 'Options', 'Charges', 'Connections', 'Profile'])
    expect(
      screen.getByRole('link', { name: 'Options' }).getAttribute('aria-current'),
    ).toBe('page')
    expect(screen.getByRole('heading', { level: 1, name: 'Settings' })).toBeTruthy()
    expect(screen.getByRole('heading', { level: 2, name: 'Options' })).toBeTruthy()
  })

  it('leaves the company to its owners', () => {
    pathname = '/settings/charges'
    show(MANAGER, 'Charges')

    expect(tabs()).toEqual(['Options', 'Charges', 'Connections', 'Profile'])
  })

  it('sends a homeowner who types Charges back to their profile', () => {
    pathname = '/settings/charges'
    replace.mockClear()
    show(HOMEOWNER, 'Charges')

    expect(replace).toHaveBeenCalledWith('/settings/profile')
    // Nothing of the page they may not have is drawn on the way.
    expect(screen.queryByText('content')).toBeNull()
  })
})
