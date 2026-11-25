'use client'

import { OTPInput, OTPInputContext } from 'input-otp'
import { type ComponentProps, useContext } from 'react'

import { cn } from '@/lib/utils'

export function InputOTP({ className, ...props }: ComponentProps<typeof OTPInput>) {
  return (
    <OTPInput
      containerClassName="flex items-center justify-center gap-2 has-disabled:opacity-50"
      className={cn('disabled:cursor-not-allowed', className)}
      {...props}
    />
  )
}

/** One digit's box. */
export function InputOTPSlot({ index }: { index: number }) {
  const slot = useContext(OTPInputContext).slots[index]
  return (
    <div
      className={cn(
        'relative flex h-14 w-11 items-center justify-center rounded-xl border border-input text-2xl font-semibold transition-shadow',
        slot?.isActive && 'ring-[3px] ring-ring/50',
      )}
    >
      {slot?.char}
      {slot?.hasFakeCaret && (
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <span className="h-6 w-px animate-pulse bg-foreground" />
        </span>
      )}
    </div>
  )
}
