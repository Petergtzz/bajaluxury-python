import {
  ArrowDownLeft,
  ArrowRightLeft,
  Banknote,
  CreditCard,
  FileCheck,
  Landmark,
  type LucideIcon,
  Wallet,
} from 'lucide-react'

import type { PaymentMethod, TransactionType } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const ICONS: Record<PaymentMethod, LucideIcon> = {
  cash: Banknote,
  'credit card': CreditCard,
  'debit card': CreditCard,
  withdrawal: Landmark,
  check: FileCheck,
  wire: ArrowRightLeft,
  paypal: Wallet,
}

/** A row's mark: money in is an arrow on green, money out how it was paid. */
export function MethodMark({
  type,
  method,
}: {
  type: TransactionType
  method: PaymentMethod | null
}) {
  const income = type === 'income'
  const Icon = income ? ArrowDownLeft : method ? ICONS[method] : Wallet
  return (
    <span
      className={cn(
        'flex size-11 shrink-0 items-center justify-center rounded-full',
        income
          ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400'
          : 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
      )}
    >
      <Icon className="size-5" strokeWidth={1.8} aria-hidden />
    </span>
  )
}
