'use client'

import { ChevronRight } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'

import { Select, SelectContent, SelectTrigger, SelectValue } from '@/components/ui/select'
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

/** Fields as rows on one grey card, a hairline between each. */
export function FieldRows({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col divide-y divide-neutral-200/70 rounded-2xl bg-neutral-50 px-5 dark:divide-neutral-700/60 dark:bg-neutral-800/50">
      {children}
    </div>
  )
}

/** A row: what it is on the left, its value on the right. */
export function FieldRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="flex min-h-12 items-center justify-between gap-4 text-[15px]">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className="flex min-w-0 flex-1 justify-end text-right font-medium">
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
  return <input className={cn(VALUE, className)} {...props} />
}

/** A choice made from a list, its value at the row's end with a chevron. */
export function RowSelect({
  label,
  value,
  onChange,
  placeholder,
  disabled,
  children,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  children: ReactNode
}) {
  return (
    <Select
      value={value}
      // Radix announces an empty value while a form resets; a choice is never
      // unmade from here, so that is ignored.
      onValueChange={(next) => next && onChange(next)}
      disabled={disabled}
    >
      <SelectTrigger
        aria-label={label}
        className="h-auto w-auto max-w-full gap-1.5 border-0 px-0 py-0 font-medium shadow-none focus-visible:ring-0 [&>svg:last-child]:hidden"
      >
        <SelectValue placeholder={placeholder ?? 'Select'} />
        {!disabled && <ChevronRight className="size-4 shrink-0 text-muted-foreground" />}
      </SelectTrigger>
      <SelectContent align="end" className="min-w-48">
        {children}
      </SelectContent>
    </Select>
  )
}
