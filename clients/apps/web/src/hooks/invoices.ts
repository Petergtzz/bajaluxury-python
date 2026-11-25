import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api, type schemas, unwrap } from '@/lib/api/client'

export const invoiceKeys = {
  all: ['invoices'] as const,
  list: ['invoices', 'list'] as const,
  unbilled: (propertyId: string) => ['invoices', 'unbilled', propertyId] as const,
}

/** Every invoice, newest number first. */
export const useInvoices = (enabled = true) =>
  useQuery({
    enabled,
    queryKey: invoiceKeys.list,
    queryFn: () => unwrap(api.GET('/v1/invoices/')),
  })

/** A property's guest expenses that no invoice bills yet, to bill them. */
export const useUnbilledGuestExpenses = (propertyId: string) =>
  useQuery({
    enabled: propertyId !== '',
    queryKey: invoiceKeys.unbilled(propertyId),
    queryFn: () =>
      unwrap(
        api.GET('/v1/guest-expenses/', {
          // shortcut: the newest 100 only; page through if a stay ever runs longer.
          params: { query: { property_id: propertyId, invoiced: false, limit: 100 } },
        }),
      ),
    select: (page) => page.items,
  })

/** Numbers, keeps and emails an invoice; its guest expenses count as billed. */
export const useCreateInvoice = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: schemas['InvoiceCreate']) =>
      unwrap(api.POST('/v1/invoices/', { body })),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['guest-expenses'] })
    },
  })
}

/** Its number stays used, and its guest expenses can be billed again. */
export const useDeleteInvoice = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (invoiceId: string) =>
      unwrap(
        api.DELETE('/v1/invoices/{invoice_id}', {
          params: { path: { invoice_id: invoiceId } },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invoiceKeys.all })
      void queryClient.invalidateQueries({ queryKey: ['guest-expenses'] })
    },
  })
}

/** The invoice as it was emailed, a plain same-origin link. */
export const invoicePDF = (invoiceId: string) => `/v1/invoices/${invoiceId}.pdf`
