'use client'

import { FileText, Plus } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark, StatusMeta } from '@/components/list-row'
import { PageAction, PageHeader } from '@/components/page-header'
import { useCompany, useCurrency, usePermissions } from '@/components/session-context'
import { SettingsListState } from '@/components/settings/settings-list-state'
import { useInvoices } from '@/hooks/invoices'
import { useProperties } from '@/hooks/ledger'
import type { Invoice } from '@/lib/api/types'
import { formatMomentDay, formatMoney, groupConsecutive } from '@/lib/format'
import { monthName } from '@/lib/reports'

import { InvoiceDialog } from './invoice-dialog'

/** What guests were billed, newest first, a month to a heading. */
export function Invoices() {
  const router = useRouter()
  const { manages } = usePermissions()
  const currency = useCurrency()
  const timezone = useCompany().data?.timezone ?? 'America/Mazatlan'
  const invoices = useInvoices(manages)
  const properties = useProperties()
  const [open, setOpen] = useState<Invoice | null>(null)
  const names = new Map((properties.data ?? []).map((one) => [one.id, one.name]))
  const items = invoices.data ?? []
  const months = groupConsecutive(items, (one) => one.issued_on.slice(0, 7))

  return (
    <>
      <PageHeader
        title="Invoices"
        description="What guests were billed for, emailed to them as a PDF."
        actions={
          manages ? (
            <PageAction
              label="New invoice"
              icon={<Plus className="size-4" />}
              onClick={() => router.push('/invoices/new')}
            />
          ) : undefined
        }
      />

      {!manages ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          Only owners and managers can see and send invoices.
        </p>
      ) : items.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          <SettingsListState
            query={invoices}
            empty="No invoices yet. Bill a guest for what was bought for their stay."
          />
        </p>
      ) : (
        <div className="flex flex-col gap-8">
          {months.map((month) => (
            <section key={month.key} aria-label={monthName(`${month.key}-01`)}>
              <ListHeading>{monthName(`${month.key}-01`)}</ListHeading>
              <ul className="flex flex-col">
                {month.items.map((invoice) => (
                  <ListRow
                    key={invoice.id}
                    onSelect={() => setOpen(invoice)}
                    label={`Invoice ${invoice.number}, ${invoice.recipient_name}`}
                    mark={
                      <RowMark className="bg-amber-100 dark:bg-amber-500/20">
                        <FileText
                          className="size-5 text-amber-900 dark:text-amber-100"
                          aria-hidden
                        />
                      </RowMark>
                    }
                    title={invoice.recipient_name}
                    meta={
                      <StatusMeta tone={invoice.sent_at ? 'on' : 'busy'}>
                        {invoice.number}
                        {/* On a phone the number is all that fits, and all that identifies it. */}
                        <span className="max-sm:hidden">
                          {[
                            '',
                            names.get(invoice.property_id),
                            invoice.sent_at
                              ? `Sent ${formatMomentDay(invoice.sent_at, timezone)}`
                              : 'Sending',
                          ]
                            .filter((part) => part !== undefined)
                            .join(' · ')}
                        </span>
                      </StatusMeta>
                    }
                    trailing={
                      <span className="shrink-0 text-base font-semibold whitespace-nowrap tabular-nums">
                        {formatMoney(invoice.total, currency)}
                      </span>
                    }
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {open && (
        <InvoiceDialog
          key={open.id}
          invoice={open}
          propertyName={names.get(open.property_id)}
          open
          onOpenChange={(next) => !next && setOpen(null)}
        />
      )}
    </>
  )
}
