'use client'

import { Plus } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useMemo, useState } from 'react'

import { PageAction, PageHeader } from '@/components/page-header'
import { useCompany, useCurrency, usePermissions } from '@/components/session-context'
import { Button } from '@/components/ui/button'
import { SelectItem } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import {
  useCategories,
  useProperties,
  useTransactionSummary,
  useTransactions,
} from '@/hooks/ledger'
import { getErrorMessage } from '@/lib/api/errors'
import type { Transaction } from '@/lib/api/types'
import { counted, sentence, todayIn } from '@/lib/format'
import {
  type LedgerFilters,
  METHODS,
  parseFilters,
  serializeFilters,
  toTransactionQuery,
} from '@/lib/ledger/filters'
import { customRange, DEFAULT_PERIOD, getPeriodLabel } from '@/lib/period'

import { CHIP, FilterField, FilterSelect, FiltersChip, PeriodChip } from './filter-chips'
import { LedgerSummary } from './ledger-summary'
import { TransactionDialog } from './transaction-dialog'
import { TransactionsList } from './transactions-list'

const NO_PANEL_FILTERS = { type: '', method: '', category: '' } as const

export function Ledger() {
  const { manages } = usePermissions()
  const company = useCompany()
  const currency = useCurrency()
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = useMemo(() => parseFilters(searchParams), [searchParams])
  const today = todayIn(company.data?.timezone ?? 'America/Mazatlan')
  const query = useMemo(() => toTransactionQuery(filters, today), [filters, today])

  const transactions = useTransactions(query)
  const summary = useTransactionSummary(query)
  const properties = useProperties()
  const categories = useCategories(manages)
  const byId = useMemo(
    () => new Map((properties.data ?? []).map((property) => [property.id, property])),
    [properties.data],
  )

  // Held, not looked up, so the dialog keeps its data while it animates shut;
  // the key gives every opening a fresh form.
  const [dialog, setDialog] = useState<{
    transaction: Transaction | null
    key: number
  } | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const openDialog = (transaction: Transaction | null) => {
    setDialog({ transaction, key: Date.now() })
    setDialogOpen(true)
  }

  const setFilters = (patch: Partial<LedgerFilters>) => {
    const address = serializeFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }

  const rows = transactions.data?.pages.flatMap((page) => page.items) ?? []
  const inPanel = [filters.type, filters.method, filters.category].filter(Boolean).length
  const filtered = inPanel > 0 || !!filters.property || filters.period !== DEFAULT_PERIOD
  const visible = (properties.data ?? []).filter(
    (p) => !p.is_archived || p.id === filters.property,
  )

  const empty = transactions.isPending ? (
    <span className="inline-flex items-center gap-2">
      <Spinner /> Loading transactions
    </span>
  ) : transactions.isError ? (
    <span className="inline-flex items-center gap-3">
      {getErrorMessage(transactions.error)}
      <Button variant="outline" size="sm" onClick={() => transactions.refetch()}>
        Try again
      </Button>
    </span>
  ) : filtered ? (
    'No transactions match these filters.'
  ) : (
    'Nothing recorded this month yet.'
  )

  return (
    <>
      <PageHeader
        title="Transactions"
        actions={
          manages && (
            <PageAction
              label="Add transaction"
              icon={<Plus />}
              onClick={() => openDialog(null)}
            />
          )
        }
      />

      <LedgerSummary
        summary={summary.data}
        currency={currency}
        period={getPeriodLabel(filters.period, today, customRange(filters))}
      />

      <div className="no-scrollbar flex items-center gap-2 max-sm:-mx-4 max-sm:px-4">
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
        <FiltersChip active={inPanel} onReset={() => setFilters(NO_PANEL_FILTERS)}>
          <FilterField label="In or out">
            <FilterSelect
              label="Money in or out"
              value={filters.type}
              onChange={(type) => setFilters({ type: type as LedgerFilters['type'] })}
              allLabel="Both"
            >
              <SelectItem value="expense">Money out</SelectItem>
              <SelectItem value="income">Money in</SelectItem>
            </FilterSelect>
          </FilterField>
          <FilterField label="Paid with">
            <FilterSelect
              label="Payment method"
              value={filters.method}
              onChange={(method) =>
                setFilters({ method: method as LedgerFilters['method'] })
              }
              allLabel="Any method"
            >
              {METHODS.map((method) => (
                <SelectItem key={method} value={method}>
                  {sentence(method)}
                </SelectItem>
              ))}
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

      <TransactionsList
        transactions={rows}
        properties={byId}
        today={today}
        currency={currency}
        empty={empty}
        onSelect={openDialog}
      />

      {rows.length > 0 && (
        <div className="flex items-center justify-between pt-2 text-sm text-muted-foreground">
          <span>
            {summary.data && rows.length < summary.data.count
              ? `${rows.length} of ${summary.data.count.toLocaleString('en-US')}`
              : counted(rows.length, 'entry', 'entries')}
          </span>
          {transactions.hasNextPage && (
            <Button
              variant="outline"
              size="sm"
              disabled={transactions.isFetchingNextPage}
              onClick={() => transactions.fetchNextPage()}
            >
              {transactions.isFetchingNextPage && <Spinner />}
              Load more
            </Button>
          )}
        </div>
      )}

      {dialog && (
        <TransactionDialog
          key={dialog.key}
          transaction={dialog.transaction}
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
