import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'
import type { Currency } from '@/lib/reports/filters'

export type StatementQuery = { start: string; end: string; currency?: Currency }

export function useStatement(propertyId: string, query: StatementQuery) {
  return useQuery({
    queryKey: ['reports', 'statement', propertyId, query],
    queryFn: () =>
      unwrap(
        api.GET('/v1/properties/{property_id}/statement', {
          params: { path: { property_id: propertyId }, query },
        }),
      ),
    enabled: !!propertyId,
    placeholderData: keepPreviousData,
  })
}

export type UtilitiesQuery = {
  start: string
  end: string
  property_id?: string
  currency?: Currency
  buckets?: string[]
}

export function useUtilities(query: UtilitiesQuery, enabled = true) {
  return useQuery({
    queryKey: ['reports', 'utilities', query],
    queryFn: () => unwrap(api.GET('/v1/reports/utilities', { params: { query } })),
    enabled,
    placeholderData: keepPreviousData,
  })
}

/** Every kind of bill a report can show, in the order a concept is sorted into them. */
export function useBuckets() {
  return useQuery({
    queryKey: ['reports', 'buckets'],
    queryFn: () => unwrap(api.GET('/v1/reports/buckets')),
    staleTime: Infinity,
  })
}
