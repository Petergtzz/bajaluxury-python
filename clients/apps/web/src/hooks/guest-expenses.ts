import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { api, type schemas, unwrap } from '@/lib/api/client'
import type { toGuestExpenseQuery } from '@/lib/guest-expenses/filters'

type Query = ReturnType<typeof toGuestExpenseQuery>

const PAGE = 50

export function useGuestExpenses(query: Query) {
  return useInfiniteQuery({
    queryKey: ['guest-expenses', 'list', query],
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/v1/guest-expenses/', {
          params: { query: { ...query, page: pageParam, limit: PAGE } },
        }),
      ),
    initialPageParam: 1,
    getNextPageParam: (last, _all, page) =>
      page < last.pagination.max_page ? page + 1 : undefined,
    placeholderData: keepPreviousData,
  })
}

export function useGuestExpenseSummary(query: Query) {
  return useQuery({
    queryKey: ['guest-expenses', 'summary', query],
    queryFn: () => unwrap(api.GET('/v1/guest-expenses/summary', { params: { query } })),
    placeholderData: keepPreviousData,
  })
}

function useGuestExpenseMutation<Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
) {
  const client = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () => client.invalidateQueries({ queryKey: ['guest-expenses'] }),
  })
}

export function useCreateGuestExpense() {
  return useGuestExpenseMutation((body: schemas['GuestExpenseCreate']) =>
    unwrap(api.POST('/v1/guest-expenses/', { body })),
  )
}

export function useUpdateGuestExpense() {
  return useGuestExpenseMutation(
    ({ id, body }: { id: string; body: schemas['GuestExpenseUpdate'] }) =>
      unwrap(
        api.PATCH('/v1/guest-expenses/{guest_expense_id}', {
          params: { path: { guest_expense_id: id } },
          body,
        }),
      ),
  )
}

export function useDeleteGuestExpense() {
  return useGuestExpenseMutation((id: string) =>
    unwrap(
      api.DELETE('/v1/guest-expenses/{guest_expense_id}', {
        params: { path: { guest_expense_id: id } },
      }),
    ),
  )
}
