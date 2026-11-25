'use client'

import { ChevronRight } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

/**
 * The big figure at the top of a money dialog: what it is for, typed in
 * place. Commas are allowed as people write them, and dropped when read.
 */
export function AmountField({
  currency,
  invalid,
  className,
  ...props
}: { currency: string; invalid?: boolean } & ComponentProps<'input'>) {
  return (
    <div className="flex flex-col items-center gap-1 pt-4 pb-2">
      <div className="flex items-baseline justify-center text-5xl font-bold tracking-tight tabular-nums">
        <span
          className={cn(
            'text-neutral-300 dark:text-neutral-600',
            props.value && 'text-foreground',
          )}
        >
          $
        </span>
        <input
          inputMode="decimal"
          autoComplete="off"
          placeholder="0.00"
          aria-label="Amount"
          aria-invalid={invalid}
          className={cn(
            'field-sizing-content min-w-[3ch] max-w-full bg-transparent text-center outline-none placeholder:text-neutral-300 dark:placeholder:text-neutral-600',
            invalid && 'text-destructive',
            className,
          )}
          {...props}
        />
      </div>
      <span className="text-sm font-medium text-muted-foreground">{currency}</span>
    </div>
  )
}

/** The tint the dialog's panels share with the page's summary card. */
export const TINT = 'bg-neutral-50 dark:bg-neutral-800/50'

/** The tinted card a group of fields sits in. */
export function Panel({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn(TINT, 'rounded-xl px-5 py-2', className)}>{children}</div>
}

/** Fields as rows on one tinted card, a hairline between each. */
export function FieldRows({ children }: { children: ReactNode }) {
  return (
    <Panel className="divide-y divide-neutral-200/80 py-0 dark:divide-neutral-800">
      {children}
    </Panel>
  )
}

/** A row: what it is on the left, its value on the right. */
export function FieldRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex min-h-12 items-center justify-between gap-4 py-2.5">
      <span className="shrink-0 text-[15px] leading-6 text-muted-foreground">
        {label}
      </span>
      <span className="flex min-w-0 flex-1 items-center justify-end text-right text-[15px]">
        {children}
      </span>
    </label>
  )
}

const VALUE =
  'w-full min-w-0 bg-transparent text-right outline-none placeholder:font-normal placeholder:text-muted-foreground disabled:opacity-100'

/** A day picked in its row, sitting at the row's end like every other value. */
export function RowDateInput({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      type="date"
      className={cn(
        VALUE,
        'w-auto [&::-webkit-calendar-picker-indicator]:ml-1.5 [&::-webkit-calendar-picker-indicator]:opacity-45 [&::-webkit-datetime-edit]:p-0',
        className,
      )}
      {...props}
    />
  )
}

/** Text typed straight into its row. */
export function RowInput({ className, ...props }: ComponentProps<'input'>) {
  return (
    <input
      // Chrome keeps room for a suggestion arrow on an input with a list, even
      // hidden, which pulled its value off the edge every other row ends on.
      className={cn(
        VALUE,
        '[&::-webkit-calendar-picker-indicator]:m-0 [&::-webkit-calendar-picker-indicator]:w-0 [&::-webkit-calendar-picker-indicator]:p-0 [&::-webkit-calendar-picker-indicator]:opacity-0',
        className,
      )}
      {...props}
    />
  )
}

/** A choice made from a list, its value at the row's end with a chevron. */
export function RowSelect({
  label,
  value,
  onValueChange,
  placeholder,
  disabled,
  children,
}: {
  label: string
  value: string
  onValueChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <Select
      value={value}
      // Radix announces an empty value while a form resets; a choice is never
      // unmade from here, so that is ignored.
      onValueChange={(next) => next && onValueChange(next)}
      disabled={disabled}
    >
      <SelectTrigger
        aria-label={label}
        // The trigger's own size variant (data-[size=default]:h-9) outranks
        // `h-auto`, which would make select rows taller than the input rows.
        className="h-auto w-auto min-w-0 justify-end gap-2 border-0 bg-transparent p-0 text-[15px] shadow-none focus-visible:ring-0 data-[placeholder]:text-muted-foreground data-[size=default]:h-auto dark:bg-transparent [&>svg:last-child]:hidden"
      >
        <SelectValue placeholder={placeholder ?? 'Select'} />
        <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden />
      </SelectTrigger>
      <SelectContent align="end" className="max-h-72">
        {children}
      </SelectContent>
    </Select>
  )
}

export { SelectItem }
