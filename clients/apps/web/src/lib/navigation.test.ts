import { expect, it } from 'vitest'

import { getNavSections, getSettingsTabs } from './navigation'

const OWNER = { manages: true, ownsCompany: true }
const MANAGER = { manages: true, ownsCompany: false }
const HOMEOWNER = { manages: false, ownsCompany: false }

it('opens on the dashboard, for everyone', () => {
  for (const can of [OWNER, HOMEOWNER]) {
    expect(getNavSections(can)[0]?.href).toBe('/dashboard')
  }
})

it('folds the ledgers under Activity, for everyone', () => {
  const activity = getNavSections(HOMEOWNER).find((s) => s.title === 'Activity')
  expect(activity?.items?.map((item) => item.href)).toEqual([
    '/transactions',
    '/guest-expenses',
  ])
})

it('names the balances page for who reads it', () => {
  const titles = (can: typeof OWNER) => getNavSections(can).map((s) => s.title)
  expect(titles(MANAGER)).toContain('Balances')
  expect(titles(HOMEOWNER)).toContain('Balance')
})

it('gives those who run the houses invoices and the team', () => {
  expect(getNavSections(MANAGER).map((s) => s.href)).toEqual([
    '/dashboard',
    '/transactions',
    '/balances',
    '/checklists',
    '/invoices',
    '/reports',
    '/team/properties',
    '/settings/options',
  ])
  const team = getNavSections(MANAGER).find((s) => s.title === 'Team')
  expect(team?.items?.map((item) => item.href)).toEqual([
    '/team/properties',
    '/team/users',
  ])
  expect(getNavSections(HOMEOWNER).map((s) => s.href)).toEqual([
    '/dashboard',
    '/transactions',
    '/balances',
    '/checklists',
    '/reports',
    '/settings/profile',
  ])
})

it('keeps one Settings entry that lands on the first tab someone has', () => {
  const settings = (can: typeof OWNER) =>
    getNavSections(can).find((s) => s.title === 'Settings')
  expect(settings(OWNER)).toMatchObject({ href: '/settings/company', match: '/settings' })
  expect(settings(HOMEOWNER)?.href).toBe('/settings/profile')
})

it('lists only the settings someone may change', () => {
  const titles = (can: typeof OWNER) => getSettingsTabs(can).map((tab) => tab.title)
  expect(titles(OWNER)).toEqual([
    'Company',
    'Options',
    'Charges',
    'Connections',
    'Profile',
  ])
  expect(titles(MANAGER)).toEqual(['Options', 'Charges', 'Connections', 'Profile'])
  expect(titles(HOMEOWNER)).toEqual(['Profile'])
})
