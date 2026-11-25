import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type schemas, unwrap } from '@/lib/api/client'
import type { Checklist } from '@/lib/api/types'

export const checklistKeys = {
  all: ['checklists'] as const,
  list: ['checklists', 'list'] as const,
  one: (checklistId: string) => ['checklists', 'one', checklistId] as const,
  templates: ['checklists', 'templates'] as const,
  properties: ['checklists', 'properties'] as const,
}

/** Every walk the caller can see, newest first. */
export const useChecklists = () =>
  useQuery({
    queryKey: checklistKeys.list,
    queryFn: () => unwrap(api.GET('/v1/checklists/')),
  })

export const useChecklist = (checklistId: string) =>
  useQuery({
    queryKey: checklistKeys.one(checklistId),
    queryFn: () =>
      unwrap(
        api.GET('/v1/checklists/{checklist_id}', {
          params: { path: { checklist_id: checklistId } },
        }),
      ),
  })

/** Every type's items: a type with none can't be walked. */
export const useChecklistTemplates = (enabled = true) =>
  useQuery({
    enabled,
    queryKey: checklistKeys.templates,
    queryFn: () => unwrap(api.GET('/v1/checklist-templates/')),
  })

export const useStartChecklist = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: schemas['ChecklistCreate']) =>
      unwrap(api.POST('/v1/checklists/', { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: checklistKeys.all }),
  })
}

/** A walk's answer, written straight into the cache so the row settles at once. */
const useSettle = (checklistId: string) => {
  const queryClient = useQueryClient()
  return (checklist: Checklist) => {
    queryClient.setQueryData(checklistKeys.one(checklistId), checklist)
    void queryClient.invalidateQueries({ queryKey: checklistKeys.list })
  }
}

/**
 * Ticks an item, or keeps a note against it.
 *
 * Somebody is standing in a doorway with one hand on the phone; the row has to
 * settle the moment they tap it, not when the round trip finishes.
 */
export const useSetChecklistItem = (checklistId: string) => {
  const settle = useSettle(checklistId)
  return useMutation({
    mutationFn: ({
      itemId,
      body,
    }: {
      itemId: string
      body: schemas['ChecklistItemUpdate']
    }) =>
      unwrap(
        api.PATCH('/v1/checklists/{checklist_id}/items/{item_id}', {
          params: { path: { checklist_id: checklistId, item_id: itemId } },
          body,
        }),
      ),
    onSuccess: settle,
  })
}

/** Freezes the walk and emails its report to its property's recipients. */
export const useCompleteChecklist = (checklistId: string) => {
  const settle = useSettle(checklistId)
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.POST('/v1/checklists/{checklist_id}/complete', {
          params: { path: { checklist_id: checklistId } },
        }),
      ),
    onSuccess: settle,
  })
}

export const useDeleteChecklist = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (checklistId: string) =>
      unwrap(
        api.DELETE('/v1/checklists/{checklist_id}', {
          params: { path: { checklist_id: checklistId } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: checklistKeys.all }),
  })
}

/** Every property, with who hears about the checklists finished there. */
export const useChecklistProperties = (enabled = true) =>
  useQuery({
    enabled,
    queryKey: checklistKeys.properties,
    queryFn: () => unwrap(api.GET('/v1/checklists/properties')),
  })

export const useSaveChecklistRecipients = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      propertyId,
      recipients,
    }: {
      propertyId: string
      recipients: schemas['RecipientUpdate'][]
    }) =>
      unwrap(
        api.PUT('/v1/checklists/properties/{property_id}', {
          params: { path: { property_id: propertyId } },
          body: { recipients },
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: checklistKeys.properties }),
  })
}
