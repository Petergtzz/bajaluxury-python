import type { User } from './types'

export const SESSION_COOKIE = process.env.BAJA_SESSION_COOKIE_KEY ?? 'baja_session'

/** Set by the proxy on the page it lets through; never trusted from the browser. */
export const USER_HEADER = 'x-baja-user'

export const getAPIURL = (): string => process.env.BAJA_API_URL ?? 'http://127.0.0.1:8000'

export const encodeUser = (user: User): string =>
  Buffer.from(JSON.stringify(user)).toString('base64')

export const decodeUser = (value: string | null): User | null =>
  value ? (JSON.parse(Buffer.from(value, 'base64').toString()) as User) : null
