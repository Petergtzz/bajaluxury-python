import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type schemas, unwrap } from '@/lib/api/client'
import type { ChecklistType } from '@/lib/api/types'

/**
 * A change in Settings or Team refreshes every list that names what changed:
 * a renamed property is in the ledger's rows too, and a new person in Reports.
 */
const useSettingsMutation = <Variables, Result>(
  mutationFn: (variables: Variables) => Promise<Result>,
  areas: string[][],
) => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    onSuccess: () =>
      Promise.all(areas.map((queryKey) => queryClient.invalidateQueries({ queryKey }))),
  })
}

export const useSaveProperty = () =>
  useSettingsMutation(
    (
      save:
        | { propertyId: null; body: schemas['PropertyCreate'] }
        | { propertyId: string; body: schemas['PropertyUpdate'] },
    ) =>
      save.propertyId === null
        ? unwrap(api.POST('/v1/properties/', { body: save.body }))
        : unwrap(
            api.PATCH('/v1/properties/{property_id}', {
              params: { path: { property_id: save.propertyId } },
              body: save.body,
            }),
          ),
    [['properties'], ['ledger'], ['reports'], ['checklists']],
  )

export const useSaveUser = () =>
  useSettingsMutation(
    (
      save:
        | { userId: null; body: schemas['ManagedUserCreate'] }
        | { userId: string; body: schemas['ManagedUserUpdate'] },
    ) =>
      save.userId === null
        ? unwrap(api.POST('/v1/users/', { body: save.body }))
        : unwrap(
            api.PATCH('/v1/users/{user_id}', {
              params: { path: { user_id: save.userId } },
              body: save.body,
            }),
          ),
    [['users'], ['reports'], ['checklists']],
  )

export const useRemoveUser = () =>
  useSettingsMutation(
    (userId: string) =>
      unwrap(
        api.DELETE('/v1/users/{user_id}', { params: { path: { user_id: userId } } }),
      ),
    [['users'], ['reports'], ['checklists'], ['api-tokens']],
  )

export const useUpdateCompany = () =>
  useSettingsMutation(
    (body: schemas['CompanyUpdate']) => unwrap(api.PATCH('/v1/company', { body })),
    [['company']],
  )

export const useUpdateProfile = () =>
  useSettingsMutation(
    (body: schemas['UserUpdate']) => unwrap(api.PATCH('/v1/users/me', { body })),
    [['users']],
  )

/** A type's whole list, kept, reworded, added to and removed from in one go. */
export const useSaveTemplate = () =>
  useSettingsMutation(
    ({ type, items }: { type: ChecklistType; items: schemas['TemplateItemWrite'][] }) =>
      unwrap(
        api.PUT('/v1/checklist-templates/{type}', {
          params: { path: { type } },
          body: { items },
        }),
      ),
    [['checklists', 'templates']],
  )

export const useRecurringCharges = () =>
  useQuery({
    queryKey: ['recurring-charges'],
    queryFn: () => unwrap(api.GET('/v1/recurring-charges/')),
  })

export const useSaveRecurringCharge = () =>
  useSettingsMutation(
    (
      save:
        | { chargeId: null; body: schemas['RecurringChargeCreate'] }
        | { chargeId: string; body: schemas['RecurringChargeUpdate'] },
    ) =>
      save.chargeId === null
        ? unwrap(api.POST('/v1/recurring-charges/', { body: save.body }))
        : unwrap(
            api.PATCH('/v1/recurring-charges/{recurring_charge_id}', {
              params: { path: { recurring_charge_id: save.chargeId } },
              body: save.body,
            }),
          ),
    [['recurring-charges']],
  )

export const useStopRecurringCharge = () =>
  useSettingsMutation(
    (chargeId: string) =>
      unwrap(
        api.DELETE('/v1/recurring-charges/{recurring_charge_id}', {
          params: { path: { recurring_charge_id: chargeId } },
        }),
      ),
    [['recurring-charges']],
  )

export const useApiTokens = () =>
  useQuery({
    queryKey: ['api-tokens'],
    queryFn: () => unwrap(api.GET('/v1/api-tokens/')),
  })

export const useCreateApiToken = () =>
  useSettingsMutation(
    (label: string) => unwrap(api.POST('/v1/api-tokens/', { body: { label } })),
    [['api-tokens']],
  )

export const useRevokeApiToken = () =>
  useSettingsMutation(
    (tokenId: string) =>
      unwrap(
        api.DELETE('/v1/api-tokens/{token_id}', {
          params: { path: { token_id: tokenId } },
        }),
      ),
    [['api-tokens']],
  )
