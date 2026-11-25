import { Download } from 'lucide-react'

const LINK =
  '-my-1 flex shrink-0 items-center gap-1.5 rounded-full px-2 py-1 text-sm font-semibold text-muted-foreground transition-colors outline-none hover:text-neutral-900 focus-visible:ring-[3px] focus-visible:ring-ring/50 dark:hover:text-neutral-100'

/**
 * The report as files, from the API under the same filters. Plain links:
 * the browser downloads them with the session cookie, nothing in between.
 */
export function Downloads({ pdf, excel }: { pdf: string; excel: string }) {
  return (
    <div className="-mr-2 flex items-center gap-1">
      <a href={pdf} download className={LINK} aria-label="Download PDF">
        <Download className="size-4" aria-hidden />
        PDF
      </a>
      <a href={excel} download className={LINK} aria-label="Download Excel">
        <Download className="size-4" aria-hidden />
        Excel
      </a>
    </div>
  )
}
