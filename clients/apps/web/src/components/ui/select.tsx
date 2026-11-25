'use client'

import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown } from 'lucide-react'
import type { ComponentProps } from 'react'

import { cn } from '@/lib/utils'

export const Select = SelectPrimitive.Root
export const SelectValue = SelectPrimitive.Value

export function SelectTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Trigger>) {
  return (
    <SelectPrimitive.Trigger
      className={cn(
        'flex h-11 w-full items-center justify-between gap-2 rounded-xl border border-input bg-transparent px-4 text-[15px] whitespace-nowrap outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-50 data-[placeholder]:text-muted-foreground [&>span]:truncate',
        className,
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDown className="size-4 shrink-0 opacity-60" />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

export function SelectContent({
  className,
  children,
  position = 'popper',
  ...props
}: ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        position={position}
        sideOffset={6}
        className={cn(
          'relative z-50 max-h-(--radix-select-content-available-height) min-w-[10rem] overflow-y-auto rounded-2xl border border-border bg-popover p-1.5 text-popover-foreground shadow-lg data-[state=open]:animate-in data-[state=open]:fade-in-0',
          position === 'popper' && 'w-full min-w-(--radix-select-trigger-width)',
          className,
        )}
        {...props}
      >
        <SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

export function SelectItem({
  className,
  children,
  ...props
}: ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      className={cn(
        'relative flex w-full cursor-default items-center rounded-xl py-2.5 pr-9 pl-3 text-[15px] outline-none select-none focus:bg-accent data-[disabled]:opacity-50',
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
      <span className="absolute right-3 flex size-4 items-center justify-center">
        <SelectPrimitive.ItemIndicator>
          <Check className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
    </SelectPrimitive.Item>
  )
}
