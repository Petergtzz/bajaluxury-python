'use client'

import { Plus, Repeat } from 'lucide-react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/confirm-dialog'
import { TextAction } from '@/components/dialog-actions'
import {
  AmountField,
  FieldRow,
  FieldRows,
  RowInput,
  RowSelect,
  SelectItem,
} from '@/components/dialog-fields'
import { FormDialog } from '@/components/form-dialog'
import { CHIP, CHIP_ROW, FilterSelect } from '@/components/ledger/filter-chips'
import { ListHeading } from '@/components/list-heading'
import { ListRow, RowMark } from '@/components/list-row'
import { PageAction } from '@/components/page-header'
import { useCurrency, useMoney } from '@/components/session-context'
import { SummaryCard } from '@/components/summary-card'
import { useCategories, useProperties } from '@/hooks/ledger'
import {
  useRecurringCharges,
  useSaveRecurringCharge,
  useStopRecurringCharge,
} from '@/hooks/settings'
import { getErrorMessage } from '@/lib/api/errors'
import type { PaymentMethod, RecurringCharge } from '@/lib/api/types'
import { sentence } from '@/lib/format'
import { METHODS } from '@/lib/ledger/filters'
import {
  type ChargeDraft,
  DAYS,
  dayName,
  describeCharge,
  draftFromCharge,
  toChargeChanges,
  toChargeCreate,
} from '@/lib/settings/charges'
import {
  applyChargeFilters,
  type ChargeFilters,
  chargeKinds,
  parseChargeFilters,
  serializeChargeFilters,
  summarizeCharges,
} from '@/lib/settings/charge-filters'

import { SettingsPage } from './settings-layout'
import { SettingsListState } from './settings-list-state'

/**
 * What each house is charged every month without anyone recording it: the
 * gardener, the pool, the management fee. The scheduler charges each on its
 * day, once a month, never for days before it was set up.
 *
 * Sixty of them read as a wall, so the card says what the ones shown come to
 * each month, and chips narrow them to one kind - all the landscaping - or one
 * house.
 */
export function Charges() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filters = parseChargeFilters(searchParams)
  const setFilters = (patch: Partial<ChargeFilters>) => {
    const address = serializeChargeFilters({ ...filters, ...patch })
    router.replace(address ? `${pathname}?${address}` : pathname, { scroll: false })
  }
  const charges = useRecurringCharges()
  const properties = useProperties().data ?? []
  const money = useMoney()
  const [dialog, setDialog] = useState<{
    charge: RecurringCharge | null
    key: number
  } | null>(null)
  const [open, setOpen] = useState(false)
  const openDialog = (charge: RecurringCharge | null) => {
    setDialog({ charge, key: Date.now() })
    setOpen(true)
  }
  const name = (id: string) => properties.find((one) => one.id === id)?.name ?? ''
  const all = charges.data ?? []
  const shown = applyChargeFilters(all, filters)
  const summary = summarizeCharges(shown)
  // A house is offered once it pays something; one picked stays offered.
  const houses = properties
    .filter((one) => all.some((charge) => charge.property_id === one.id))
    .sort((a, b) => a.name.localeCompare(b.name))
  const sorted = [...shown].sort((a, b) => a.day_of_month - b.day_of_month)
  // One heading per house, in name order. Grouped before sorting, so a house
  // is one group even before the names have loaded.
  const byHouse = [...Map.groupBy(sorted, (charge) => charge.property_id)]
    .map(([key, items]) => ({ key, items }))
    .sort((a, b) => name(a.key).localeCompare(name(b.key)))

  return (
    <SettingsPage
      title="Charges"
      description="Charged to a house every month on their day, without anyone recording them."
      actions={
        <PageAction
          label="Add charge"
          icon={<Plus className="size-4" />}
          onClick={() => openDialog(null)}
        />
      }
    >
      {all.length > 0 && (
        <>
          <SummaryCard
            label={
              filters.what
                ? `${sentence(filters.what)} · each month`
                : 'Charged each month'
            }
            headline={money(summary.monthly)}
            figures={[
              { label: 'Charges', value: summary.count.toLocaleString('en-US') },
              { label: 'Houses', value: summary.houses.toLocaleString('en-US') },
            ]}
          />
          <div className={CHIP_ROW}>
            <FilterSelect
              label="What it is for"
              value={filters.what}
              onChange={(what) => setFilters({ what })}
              allLabel="All charges"
              className={CHIP}
            >
              {chargeKinds(all).map(({ kind, count }) => (
                <SelectItem key={kind} value={kind}>
                  {sentence(kind)} ({count})
                </SelectItem>
              ))}
            </FilterSelect>
            {houses.length > 1 && (
              <FilterSelect
                label="Property"
                value={filters.property}
                onChange={(property) => setFilters({ property })}
                allLabel="All properties"
                className={CHIP}
              >
                {houses.map((house) => (
                  <SelectItem key={house.id} value={house.id}>
                    {house.name}
                  </SelectItem>
                ))}
              </FilterSelect>
            )}
          </div>
        </>
      )}

      {sorted.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">
          {all.length > 0 ? (
            'No charges match these filters.'
          ) : (
            <SettingsListState
              query={charges}
              empty="Nothing is charged by itself yet. Add what a house pays every month."
            />
          )}
        </p>
      ) : (
        <div className="flex flex-col gap-8">
          {byHouse.map((house) => (
            <section key={house.key} aria-label={name(house.key)}>
              <ListHeading>{name(house.key)}</ListHeading>
              <ul className="flex flex-col">
                {house.items.map((charge) => (
                  <ListRow
                    key={charge.id}
                    onSelect={() => openDialog(charge)}
                    label={`${sentence(charge.concept)}, ${money(charge.amount)}`}
                    mark={
                      <RowMark className="bg-emerald-100 dark:bg-emerald-500/20">
                        <Repeat
                          className="size-5 text-emerald-900 dark:text-emerald-100"
                          aria-hidden
                        />
                      </RowMark>
                    }
                    title={sentence(charge.concept)}
                    meta={<span className="truncate">{describeCharge(charge)}</span>}
                    trailing={
                      <span className="shrink-0 text-base font-semibold whitespace-nowrap tabular-nums">
                        {money(charge.amount)}
                      </span>
                    }
                  />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {dialog && (
        <ChargeDialog
          key={dialog.key}
          charge={dialog.charge}
          open={open}
          onOpenChange={setOpen}
        />
      )}
    </SettingsPage>
  )
}

function ChargeDialog({
  charge,
  open,
  onOpenChange,
}: {
  /** Null to set a new one up. */
  charge: RecurringCharge | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const currency = useCurrency()
  const properties = useProperties().data ?? []
  const categories = useCategories(true).data ?? []
  const save = useSaveRecurringCharge()
  const stop = useStopRecurringCharge()
  const [draft, setDraft] = useState<ChargeDraft>(() => draftFromCharge(charge))
  const [error, setError] = useState<string>()
  const [confirming, setConfirming] = useState(false)
  const [stopError, setStopError] = useState<string>()
  const busy = save.isPending || stop.isPending
  const house = properties.find((one) => one.id === draft.propertyId)

  const set = <K extends keyof ChargeDraft>(field: K, value: ChargeDraft[K]) => {
    setDraft((current) => ({ ...current, [field]: value }))
    setError(undefined)
  }

  const submit = async () => {
    try {
      if (charge === null) {
        const result = toChargeCreate(draft)
        if ('error' in result) return setError(result.error)
        await save.mutateAsync({ chargeId: null, body: result.body })
      } else {
        const result = toChargeChanges(draft, charge)
        if ('error' in result) return setError(result.error)
        if (Object.keys(result.body).length > 0) {
          await save.mutateAsync({ chargeId: charge.id, body: result.body })
        }
      }
    } catch (failure) {
      setError(getErrorMessage(failure))
      return
    }
    onOpenChange(false)
    toast.success(
      charge ? 'Charge saved' : `${house?.name ?? 'The house'} is charged monthly`,
    )
  }

  const confirmStop = async () => {
    if (!charge) return
    try {
      await stop.mutateAsync(charge.id)
    } catch (failure) {
      setStopError(getErrorMessage(failure))
      return
    }
    setConfirming(false)
    onOpenChange(false)
    toast.success('Charge stopped')
  }

  return (
    <>
      <FormDialog
        title={charge ? 'Recurring charge' : 'Add recurring charge'}
        open={open && !confirming}
        onOpenChange={onOpenChange}
        onSubmit={() => void submit()}
        submitLabel={charge ? 'Save changes' : 'Add charge'}
        pending={busy}
        error={error}
        className="max-h-[calc(100svh-2rem)] overflow-y-auto"
        contentProps={{ onOpenAutoFocus: (event) => charge && event.preventDefault() }}
        actions={
          charge && (
            <TextAction
              destructive
              onClick={() => {
                setStopError(undefined)
                setConfirming(true)
              }}
              disabled={busy}
            >
              Stop charging
            </TextAction>
          )
        }
      >
        <AmountField
          currency={currency}
          value={draft.amount}
          onChange={(event) => set('amount', event.target.value)}
          disabled={busy}
        />
        <FieldRows>
          <FieldRow label="Property">
            {charge ? (
              // A charge stays with its house; another house's is a new one.
              <span className="truncate">{house?.name}</span>
            ) : (
              <RowSelect
                label="Property"
                value={draft.propertyId}
                onValueChange={(value) => set('propertyId', value)}
                placeholder="Select"
                disabled={busy}
              >
                {properties
                  .filter((one) => !one.is_archived)
                  .map((one) => (
                    <SelectItem key={one.id} value={one.id}>
                      {one.name}
                    </SelectItem>
                  ))}
              </RowSelect>
            )}
          </FieldRow>
          <FieldRow label="Category">
            <RowInput
              list="charge-categories"
              placeholder="services"
              value={draft.category}
              onChange={(event) => set('category', event.target.value)}
              disabled={busy}
            />
            <datalist id="charge-categories">
              {categories.map((category) => (
                <option key={category} value={category} />
              ))}
            </datalist>
          </FieldRow>
          <FieldRow label="Concept">
            <RowInput
              placeholder="gardener"
              value={draft.concept}
              onChange={(event) => set('concept', event.target.value)}
              disabled={busy}
            />
          </FieldRow>
          <FieldRow label="Paid with">
            <RowSelect
              label="Paid with"
              value={draft.paymentMethod}
              onValueChange={(value) => set('paymentMethod', value as PaymentMethod)}
              disabled={busy}
            >
              {METHODS.map((method) => (
                <SelectItem key={method} value={method}>
                  {sentence(method)}
                </SelectItem>
              ))}
            </RowSelect>
          </FieldRow>
          <FieldRow label="Charged on">
            <RowSelect
              label="Day of the month"
              value={String(draft.day)}
              onValueChange={(value) => set('day', Number(value))}
              disabled={busy}
            >
              {DAYS.map((day) => (
                <SelectItem key={day} value={String(day)}>
                  {dayName(day)}
                </SelectItem>
              ))}
            </RowSelect>
          </FieldRow>
          <FieldRow label="Note">
            <RowInput
              placeholder="Add a note"
              value={draft.description}
              onChange={(event) => set('description', event.target.value)}
              disabled={busy}
            />
          </FieldRow>
        </FieldRows>
        <p className="-mt-2 px-1 text-xs text-muted-foreground">
          {charge
            ? 'A change applies from the next charge: months already charged stay as they were.'
            : 'Charged from its next day on, never for days before today.'}
        </p>
      </FormDialog>

      {charge && (
        <ConfirmDialog
          title="Stop charging"
          action="Stop charging"
          open={confirming}
          onOpenChange={setConfirming}
          onConfirm={() => void confirmStop()}
          pending={stop.isPending}
          error={stopError}
        >
          {sentence(charge.concept)} won’t be charged to {house?.name} again. What it
          already charged stays in the ledger.
        </ConfirmDialog>
      )}
    </>
  )
}
