import { isServer, QueryClient } from '@tanstack/react-query'

import { ClientResponseError } from './api/client'

/** Retry what may work a moment later; a 4xx is the API's answer and stays so. */
export const shouldRetry = (failureCount: number, error: unknown): boolean =>
  failureCount < 3 && !(error instanceof ClientResponseError && error.status < 500)

const makeQueryClient = () =>
  new QueryClient({
    defaultOptions: { queries: { staleTime: 60 * 1000, retry: shouldRetry } },
  })

let browserQueryClient: QueryClient | undefined

export const getQueryClient = (): QueryClient => {
  if (isServer) return makeQueryClient()
  browserQueryClient ??= makeQueryClient()
  return browserQueryClient
}
