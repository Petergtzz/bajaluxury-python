import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { api, type schemas, unwrap } from '@/lib/api/client'
import type { toTransactionQuery } from '@/lib/ledger/filters'
import type { Range } from '@/lib/period'

type Query = ReturnType<typeof toTransactionQuery>

const PAGE = 50

/** The ledger a page at a time, newest first. */
export function useTransactions(query: Query) {
  return useInfiniteQuery({
    queryKey: ['ledger', 'transactions', query],
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/v1/transactions/', {
          params: { query: { ...query, page: pageParam, limit: PAGE } },
        }),
      ),
    initialPageParam: 1,
    getNextPageParam: (last, _all, page) =>
      page < last.pagination.max_page ? page + 1 : undefined,
    placeholderData: keepPreviousData,
  })
}

/** What the same filters add up to, across every page. */
export function useTransactionSummary(query: Query) {
  return useQuery({
    queryKey: ['ledger', 'summary', query],
    queryFn: () => unwrap(api.GET('/v1/transactions/summary', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

export function useBalances() {
  return useQuery({
    queryKey: ['ledger', 'balances'],
    queryFn: () =>
      unwrap(api.GET('/v1/balances/', { params: { query: { is_archived: false } } })),
  })
}

/** One house's statement over some days: what the dashboard reads. */
export function useStatement(propertyId: string | undefined, range: Range) {
  return useQuery({
    queryKey: ['ledger', 'statement', propertyId, range],
    queryFn: () =>
      unwrap(
        api.GET('/v1/properties/{property_id}/statement', {
          params: {
            path: { property_id: propertyId as string },
            query: { start: range.from, end: range.to },
          },
        }),
      ),
    enabled: !!propertyId,
    placeholderData: keepPreviousData,
  })
}

/** Every property the caller may see, archived ones too: old rows name them. */
export function useProperties() {
  return useQuery({
    queryKey: ['properties'],
    queryFn: () => unwrap(api.GET('/v1/properties/')),
  })
}

/** The categories in use, most used first, to pick from when recording. */
export function useCategories(enabled: boolean) {
  return useQuery({
    queryKey: ['ledger', 'categories'],
    queryFn: () => unwrap(api.GET('/v1/shortcut/categories')),
    select: (data) => data.categories,
    enabled,
  })
}

/** Every change to the ledger refreshes all of it: lists, sums, balances. */
function useLedgerMutation<Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
) {
  const client = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => client.invalidateQueries({ queryKey: ['ledger'] }),
  })
}

export function useCreateTransaction() {
  return useLedgerMutation((body: schemas['TransactionCreate']) =>
    unwrap(api.POST('/v1/transactions/', { body })),
  )
}

export function useUpdateTransaction() {
  return useLedgerMutation(
    ({ id, body }: { id: string; body: schemas['TransactionUpdate'] }) =>
      unwrap(
        api.PATCH('/v1/transactions/{transaction_id}', {
          params: { path: { transaction_id: id } },
          body,
        }),
      ),
  )
}

export function useDeleteTransaction() {
  return useLedgerMutation((id: string) =>
    unwrap(
      api.DELETE('/v1/transactions/{transaction_id}', {
        params: { path: { transaction_id: id } },
      }),
    ),
  )
}
