import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, unwrap } from '@/lib/api/client'
import type { RecipientKind } from '@/lib/api/types'
export const reportKeys = {
  all: () => ['reports', 'properties'] as const,
  sends: () => ['reports', 'sends'] as const,
  failed: () => ['reports', 'failed'] as const,
}

export const useReports = (enabled = true) =>
  useQuery({
    enabled,
    queryKey: reportKeys.all(),
    queryFn: () => unwrap(api.GET('/v1/reports/properties/')),
  })

/** Every statement that has gone out, newest month first. */
export const useSentStatements = () =>
  useQuery({
    queryKey: reportKeys.sends(),
    queryFn: () => unwrap(api.GET('/v1/reports/sends/')),
  })

/** How many statements didn't go, for the count beside Reports. */
export const useFailedStatementCount = (enabled = true) =>
  useQuery({
    enabled,
    queryKey: reportKeys.failed(),
    queryFn: () => unwrap(api.GET('/v1/reports/sends/count')),
    select: (data) => data.count,
  })

const useRefreshReports = () => {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ['reports'] })
}

/** Turns a property's report on, or changes who receives it. */
export const useSaveReport = () => {
  const refresh = useRefreshReports()
  return useMutation({
    mutationFn: ({
      propertyId,
      recipients,
      sendDay,
    }: {
      propertyId: string
      recipients: { user_id: string; kind: RecipientKind }[]
      sendDay: number
    }) =>
      unwrap(
        api.PUT('/v1/reports/properties/{property_id}', {
          params: { path: { property_id: propertyId } },
          body: { recipients, send_day: sendDay },
        }),
      ),
    onSuccess: refresh,
  })
}

export const useTurnOffReport = () => {
  const refresh = useRefreshReports()
  return useMutation({
    mutationFn: (propertyId: string) =>
      unwrap(
        api.DELETE('/v1/reports/properties/{property_id}', {
          params: { path: { property_id: propertyId } },
        }),
      ),
    onSuccess: refresh,
  })
}

/** Sends a month now, without waiting for its day. */
export const useSendReport = () => {
  const refresh = useRefreshReports()
  return useMutation({
    mutationFn: ({
      propertyId,
      month,
    }: {
      propertyId: string
      /** Any day in the month; omitted, the last complete one is sent. */
      month?: string
    }) =>
      unwrap(
        api.POST('/v1/reports/properties/{property_id}/send', {
          params: { path: { property_id: propertyId } },
          body: { month: month ?? null },
        }),
      ),
    onSuccess: refresh,
  })
}

/** The statement as it was sent, kept by the API: a plain same-origin link. */
export const statementURL = (sendId: string) =>
  `/v1/reports/sends/${sendId}/statement.pdf`
