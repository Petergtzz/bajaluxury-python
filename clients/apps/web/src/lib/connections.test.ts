import { expect, it } from 'vitest'

import type { ApiToken } from '@/lib/api/types'

import { tokenActivity } from './connections'

const TOKEN: ApiToken = {
  id: 't1',
  label: 'Ana’s iPhone',
  user: { id: 'u1', email: 'ana@example.com', name: 'Ana' },
  last_used_at: null,
  created_at: '2026-11-26T03:00:00Z',
}

it('says when a device was last heard from, on the company’s clock', () => {
  // 03:00 UTC on the 26th is the evening of the 25th in Los Cabos.
  expect(tokenActivity(TOKEN, 'America/Mazatlan')).toBe(
    'Created 25 Nov 2026 · never used',
  )
  expect(
    tokenActivity({ ...TOKEN, last_used_at: '2026-11-28T15:00:00Z' }, 'America/Mazatlan'),
  ).toBe('Last used 28 Nov 2026')
})
