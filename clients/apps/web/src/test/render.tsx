import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { vi } from 'vitest'

import { SessionProvider } from '@/components/session-context'
import type { User } from '@/lib/api/types'

import { OWNER } from './fixtures'

export const renderWithQueryClient = (ui: ReactElement) =>
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
          },
        })
      }
    >
      {ui}
    </QueryClientProvider>,
  )

/** Like renderWithQueryClient, signed in as Pedro, who owns the company. */
export const renderSignedIn = (ui: ReactElement, user: User = OWNER) =>
  renderWithQueryClient(<SessionProvider user={user}>{ui}</SessionProvider>)

export type APICall = { method: string; path: string; body: unknown }

/** Stubs fetch with answers in order and records what was sent. */
export const stubAPI = (...answers: Array<[number, unknown?]>) => {
  const calls: APICall[] = []
  const queue = [...answers]
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      const text = await request.text()
      calls.push({
        method: request.method,
        path: new URL(request.url).pathname,
        body: text ? JSON.parse(text) : undefined,
      })
      const [status, body] = queue.shift() ?? [500, {}]
      return body === undefined
        ? new Response(null, { status, headers: { 'Content-Length': '0' } })
        : new Response(JSON.stringify(body), {
            status,
            headers: { 'Content-Type': 'application/json' },
          })
    }),
  )
  return calls
}

export type Answer = { status: number; body?: unknown }

const respond = ({ status, body }: Answer) =>
  body === undefined
    ? new Response(null, { status, headers: { 'Content-Length': '0' } })
    : new Response(JSON.stringify(body), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })

/**
 * Stubs fetch with an answer per path, for a page that asks for several things
 * at once and doesn't care in which order they come back.
 *
 * A path nobody answered comes back an empty list, so a test only says what it
 * is actually about. A path with its query answers that one request only.
 */
export const stubRoutes = (answers: Record<string, Answer>) => {
  const calls: APICall[] = []
  const requested: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      const url = new URL(request.url)
      const text = await request.text()
      requested.push(`${url.pathname}${url.search}`)
      calls.push({
        method: request.method,
        path: url.pathname,
        body: text ? JSON.parse(text) : undefined,
      })
      return respond(
        answers[`${url.pathname}${url.search}`] ??
          answers[url.pathname] ?? { status: 200, body: [] },
      )
    }),
  )
  return Object.assign(calls, { requested })
}

/**
 * Stubs fetch with a list per path for reads, and answers the writes in order.
 *
 * The settings pages all work this way: they load a list, change one row, and
 * the test cares about what was sent rather than what came back.
 */
export const stubLists = (lists: Record<string, unknown[]>, ...changes: Answer[]) => {
  const sent: APICall[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname
      if (request.method === 'GET') {
        return Response.json(lists[path] ?? [])
      }
      const text = await request.text()
      sent.push({
        method: request.method,
        path,
        body: text ? JSON.parse(text) : undefined,
      })
      const answer = changes.shift() ?? { status: 500, body: {} }
      return answer.status === 204
        ? new Response(null, { status: 204 })
        : Response.json(answer.body ?? {}, { status: answer.status })
    }),
  )
  return sent
}
