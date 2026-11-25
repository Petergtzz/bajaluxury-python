'use client'

import { Check, ChevronDown, SlidersHorizontal } from 'lucide-react'
import { type ReactNode, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { formatRange } from '@/lib/format'
import { PERIOD_NAMES, type Period, PERIODS, type Range } from '@/lib/period'
import { cn } from '@/lib/utils'

/** A filter people change all the time, as a chip that says what it is set to. */
export const CHIP =
  'h-11 w-auto shrink-0 gap-1.5 rounded-full border-0 bg-neutral-100 px-4 text-[15px] font-semibold text-neutral-900 shadow-none hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-100 dark:hover:bg-neutral-700 [&_svg]:text-neutral-500'

const ALL = '__all'

/**
 * A select over a list, with an "everything" choice meaning no filter when it
 * has `allLabel`; without one, something is always chosen.
 */
export function FilterSelect({
  label,
  value,
  onChange,
  allLabel,
  className,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  allLabel?: string
  className?: string
  children: ReactNode
}) {
  return (
    <Select
      value={value || (allLabel ? ALL : undefined)}
      // Radix announces an empty value while it resets; nothing is unchosen here.
      onValueChange={(next) => next && onChange(next === ALL ? '' : next)}
    >
      <SelectTrigger aria-label={label} className={className}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="start">
        {allLabel && <SelectItem value={ALL}>{allLabel}</SelectItem>}
        {children}
      </SelectContent>
    </Select>
  )
}

/** Which span of time: a month, the year, everything, or days of one's own. */
export function PeriodChip({
  period,
  custom,
  onChange,
  allowed = PERIODS,
}: {
  period: Period
  custom?: Range
  onChange: (period: Period, custom?: Range) => void
  /** The periods the page offers, custom days among them if it does. */
  allowed?: readonly Period[]
}) {
  const [open, setOpen] = useState(false)
  const [from, setFrom] = useState(custom?.from ?? '')
  const [to, setTo] = useState(custom?.to ?? '')
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="secondary" className={CHIP}>
          {period === 'custom' && custom
            ? formatRange(custom.from, custom.to)
            : PERIOD_NAMES[period]}
          <ChevronDown className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-1.5">
        {allowed
          .filter((one) => one !== 'custom')
          .map((one) => (
            <button
              key={one}
              type="button"
              onClick={() => {
                onChange(one)
                setOpen(false)
              }}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-[15px] hover:bg-accent"
            >
              {PERIOD_NAMES[one]}
              {period === one && <Check className="size-4" />}
            </button>
          ))}
        <form
          className="mt-1.5 flex flex-col gap-2 border-t border-border p-2 pt-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (from && to && from <= to) {
              onChange('custom', { from, to })
              setOpen(false)
            }
          }}
        >
          <span className="text-sm font-medium text-muted-foreground">Between</span>
          <div className="flex items-center gap-2">
            <Input
              type="date"
              aria-label="From"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="h-10 px-3 text-sm"
            />
            <Input
              type="date"
              aria-label="To"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="h-10 px-3 text-sm"
            />
          </div>
          <Button type="submit" size="sm" disabled={!from || !to || from > to}>
            Show these days
          </Button>
        </form>
      </PopoverContent>
    </Popover>
  )
}

/** The rarer filters, behind one chip whose badge counts those in use. */
export function FiltersChip({
  active,
  onReset,
  children,
}: {
  active: number
  onReset: () => void
  children: ReactNode
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="secondary"
          className={cn(CHIP, active === 0 && 'max-sm:w-11 max-sm:px-0')}
          aria-label={active > 0 ? `Filters, ${active} in use` : 'Filters'}
        >
          <SlidersHorizontal className="size-4" />
          <span className="max-sm:hidden">Filters</span>
          {active > 0 && (
            <span className="flex size-6 items-center justify-center rounded-full bg-brand text-xs font-semibold text-brand-foreground tabular-nums">
              {active}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-5">
        <div className="flex flex-col gap-4">
          {children}
          <div className="flex items-center justify-between border-t border-border pt-3">
            <span className="text-sm text-muted-foreground">Changes apply as you go</span>
            <Button
              variant="ghost"
              size="sm"
              className="-mr-2 font-semibold"
              disabled={active === 0}
              onClick={onReset}
            >
              Reset
            </Button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

/** A filter inside the panel: what it is, over its control. */
export function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-muted-foreground">{label}</span>
      {children}
    </div>
  )
}
