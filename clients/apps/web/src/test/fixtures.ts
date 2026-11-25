import type { User } from '@/lib/api/types'

/** Pedro owns the company, so a test renders with everything allowed by default. */
export const OWNER: User = {
  id: 'u1',
  email: 'pedro@example.com',
  name: 'Pedro',
  role: 'owner',
  display_currency: null,
}

/** A homeowner: they may look at their own properties, and change nothing. */
export const HOMEOWNER: User = {
  id: 'u9',
  email: 'ana@example.com',
  name: 'Ana',
  role: 'homeowner',
  display_currency: null,
}
