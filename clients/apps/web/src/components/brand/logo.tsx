import { cn } from '@/lib/utils'

/**
 * Baja Luxury's mark and name, in the page's ink: near-black on light, white
 * on dark, like the name beside it.
 */
export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn('flex items-center gap-2.5', className)}>
      {/* The mark's lines as a mask, painted in the text's colour for either theme. */}
      <span
        aria-hidden
        className="h-[35px] w-[25px] shrink-0 bg-neutral-900 [mask-image:url(/logo-mark.png)] [mask-size:contain] [mask-repeat:no-repeat] dark:bg-white"
      />
      <span className="text-lg font-bold tracking-tight text-neutral-900 dark:text-white">
        Baja Luxury
      </span>
    </span>
  )
}
