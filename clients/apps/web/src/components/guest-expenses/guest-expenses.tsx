'use client'

import { Plus, ReceiptText } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo, useState } from 'react'

import {
  CHIP,
  CHIP_ROW,
  FilterField,
  FilterSelect,
  FiltersChip,
  PeriodChip,
} from '@/components/ledger/filter-chips'
import { ListRow, RowMark } from '@/components/list-row'
import { PageAction, PageHeader } from '@/components/page-header'
import { useCompany, useCurrency, usePermissions } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { Button } from '@/components/ui/button'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useGuestExpenseSummary, useGuestExpenses } from '@/hooks/guest-expenses'
import { useCategories, useProperties } from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { schemas } from '@/lib/api/client'
import {
  counted,
  formatDayHeading,
  formatMoney,
  groupConsecutive,
  sentence,
  todayIn,
} from '@/lib/format'
import {
  type GuestExpenseFilters,
  parseGuestExpenseFilters,
  serializeGuestExpenseFilters,
  toGuestExpenseQuery,
} from '@/lib/guest-expenses/filters'
import { customRange, DEFAULT_PERIOD, getPeriodLabel } from '@/lib/period'
import { cn } from '@/lib/utils'

import { GuestExpenseDialog } from './guest-expense-dialog'

type GuestExpense = schemas['GuestExpenseSchema']

/**
 * What was bought for renting guests, to bill them for. The card leads with
 * what is still to bill, the question this page is opened to answer.
 */
export function GuestExpenses() {
  const { manages } = usePermissions()
  const company = useCompany()
  const currency = useCurrency()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseGuestExpenseFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const query = useMemo(() => toGuestExpenseQuery(filters, today), [filters, today])

  const list = useGuestExpenses(query)
  const summary = useGuestExpenseSummary(query)
  const properties = useProperties()
  const categories = useCategories(manages)
  const names = useMemo(
    () =>
      new Map((properties.data ?? []).map((property) => [property.id, property.name])),
    [properties.data],
  )

  const [dialog, setDialog] = useState<{
    guestExpense: GuestExpense | null
    key: number
  } | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const openDialog = (guestExpense: GuestExpense | null) => {
    setDialog({ guestExpense, key: Date.now() })
    setDialogOpen(true)
  }

  const setFilters = (patch: Partial<GuestExpenseFilters>) => {
    const address = serializeGuestExpenseFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }

  const rows = list.data?.pages.flatMap((page) => page.items) ?? []
  const inPanel = [filters.billed, filters.category].filter(Boolean).length
  const filtered = inPanel > 0 || !!filters.property || filters.period !== DEFAULT_PERIOD
  const visible = (properties.data ?? []).filter(
    (p) => !p.is_archived || p.id === filters.property,
  )
  const data = summary.data

  return (
    <>
      <PageHeader
        title="Guest expenses"
        description="Bought for renting guests, to bill them. Never part of the owner's balance."
        actions={
          manages && (
            <PageAction
              label="Add guest expense"
              icon={<Plus />}
              onClick={() => openDialog(null)}
            />
          )
        }
      />

      <SummaryCard
        label={`Not billed yet · ${getPeriodLabel(filters.period, today, customRange(filters))}`}
        headline={data && formatMoney(data.total - data.billed_total, currency)}
        figures={[
          { label: 'Billed', value: data && formatMoney(data.billed_total, currency) },
          { label: 'Total', value: data && formatMoney(data.total, currency) },
          { label: 'Entries', value: data?.count.toLocaleString('en-US') },
        ]}
      />

      <div className={CHIP_ROW}>
        <PeriodChip
          key={`${filters.from}${filters.to}`}
          period={filters.period}
          custom={customRange(filters)}
          onChange={(period, custom) =>
            setFilters({ period, from: custom?.from ?? '', to: custom?.to ?? '' })
          }
        />
        {visible.length > 1 && (
          <FilterSelect
            label="Property"
            value={filters.property}
            onChange={(property) => setFilters({ property })}
            allLabel="All properties"
            className={CHIP}
          >
            {visible.map((property) => (
              <SelectItem key={property.id} value={property.id}>
                {property.name}
              </SelectItem>
            ))}
          </FilterSelect>
        )}
        <span className="flex-1" />
        <FiltersChip
          active={inPanel}
          onReset={() => setFilters({ billed: '', category: '' })}
        >
          <FilterField label="Billed">
            <FilterSelect
              label="Billed"
              value={filters.billed}
              onChange={(billed) =>
                setFilters({ billed: billed as GuestExpenseFilters['billed'] })
              }
              allLabel="Billed or not"
            >
              <SelectItem value="unbilled">Not billed yet</SelectItem>
              <SelectItem value="billed">Billed</SelectItem>
            </FilterSelect>
          </FilterField>
          {(categories.data?.length ?? 0) > 0 && (
            <FilterField label="Category">
              <FilterSelect
                label="Category"
                value={filters.category}
                onChange={(category) => setFilters({ category })}
                allLabel="All categories"
              >
                {categories.data?.map((category) => (
                  <SelectItem key={category} value={category}>
                    {sentence(category)}
                  </SelectItem>
                ))}
              </FilterSelect>
            </FilterField>
          )}
        </FiltersChip>
      </div>

      {rows.length === 0 ? (
        <div className="p-6 text-center text-sm text-muted-foreground">
          {list.isPending ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Loading guest expenses
            </span>
          ) : list.isError ? (
            getErrorMessage(list.error)
          ) : filtered ? (
            'No guest expenses match these filters.'
          ) : (
            'Nothing bought for guests this month yet.'
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-9">
          {groupConsecutive(rows, (row) => row.date).map((day) => (
            <section key={day.key} aria-label={formatDayHeading(day.key, today)}>
              <h2 className="border-b border-border pb-3 text-sm text-muted-foreground">
                {formatDayHeading(day.key, today)}
              </h2>
              <ul className="flex flex-col">
                {day.items.map((row) => (
                  <ListRow
                    key={row.id}
                    label={`${sentence(row.concept)}, ${formatMoney(row.amount, currency)}`}
                    onSelect={() => openDialog(row)}
                    mark={
                      <RowMark>
                        <ReceiptText className="size-5" strokeWidth={1.8} />
                      </RowMark>
                    }
                    title={sentence(row.concept)}
                    meta={
                      <span className="truncate">
                        {[names.get(row.property_id), sentence(row.category)]
                          .filter(Boolean)
                          .join(' · ')}
                      </span>
                    }
                    trailing={
                      <span className="flex shrink-0 flex-col items-end">
                        <span className="text-base font-semibold whitespace-nowrap tabular-nums">
                          {formatMoney(row.amount, currency)}
                        </span>
                        <span
                          className={cn(
                            'text-xs',
                            row.invoice_id
                              ? 'font-semibold text-emerald-700 dark:text-emerald-500'
                              : 'text-muted-foreground',
                          )}
                        >
                          {row.invoice_id ? 'Billed' : 'Not billed'}
                        </span>
                      </span>
                    }
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {rows.length > 0 && (
        <div className="flex items-center justify-between pt-2 text-sm text-muted-foreground">
          <span>
            {data && rows.length < data.count
              ? `${rows.length} of ${data.count.toLocaleString('en-US')}`
              : counted(rows.length, 'entry', 'entries')}
          </span>
          {list.hasNextPage && (
            <Button
              variant="outline"
              size="sm"
              disabled={list.isFetchingNextPage}
              onClick={() => list.fetchNextPage()}
            >
              {list.isFetchingNextPage && <Spinner />}
              Load more
            </Button>
          )}
        </div>
      )}

      {dialog && (
        <GuestExpenseDialog
          key={dialog.key}
          guestExpense={dialog.guestExpense}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          today={today}
          properties={properties.data ?? []}
          categories={categories.data ?? []}
          currency={currency}
          readOnly={!manages}
        />
      )}
    </>
  )
}
