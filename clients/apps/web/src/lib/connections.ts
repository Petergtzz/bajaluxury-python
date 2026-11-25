import type { ApiToken } from '@/lib/api/types'

const day = (value: string, timeZone: string) =>
  new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone,
  }).format(new Date(value))

/** The line under a token's name: when it was last used, or that it wasn't. */
export const tokenActivity = (token: ApiToken, timeZone: string): string =>
  token.last_used_at
    ? `Last used ${day(token.last_used_at, timeZone)}`
    : `Created ${day(token.created_at, timeZone)} · never used`
