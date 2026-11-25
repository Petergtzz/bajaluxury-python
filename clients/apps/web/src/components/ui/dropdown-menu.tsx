'use client'

import * as MenuPrimitive from '@radix-ui/react-dropdown-menu'
import type { ComponentProps } from 'react'

import { cn } from '@/lib/utils'

export const DropdownMenu = MenuPrimitive.Root
export const DropdownMenuTrigger = MenuPrimitive.Trigger

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...props
}: ComponentProps<typeof MenuPrimitive.Content>) {
  return (
    <MenuPrimitive.Portal>
      <MenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 min-w-[12rem] rounded-2xl border border-border bg-popover p-1.5 text-popover-foreground shadow-lg data-[state=open]:animate-in data-[state=open]:fade-in-0',
          className,
        )}
        {...props}
      />
    </MenuPrimitive.Portal>
  )
}

export function DropdownMenuItem({
  className,
  ...props
}: ComponentProps<typeof MenuPrimitive.Item>) {
  return (
    <MenuPrimitive.Item
      className={cn(
        'flex cursor-default items-center gap-2.5 rounded-xl px-3 py-2.5 text-[15px] outline-none select-none focus:bg-accent [&_svg]:size-4 [&_svg]:text-muted-foreground',
        className,
      )}
      {...props}
    />
  )
}

export function DropdownMenuSeparator({ className }: { className?: string }) {
  return (
    <MenuPrimitive.Separator className={cn('-mx-1.5 my-1.5 h-px bg-border', className)} />
  )
}
