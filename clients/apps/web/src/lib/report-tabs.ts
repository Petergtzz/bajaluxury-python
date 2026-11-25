import { makeTabs } from '@/lib/page-tabs'

/**
 * The Reports page has two halves: what each property is set up to send, and
 * what has actually gone out. They are the same subject from two sides, so they
 * are tabs on one page rather than two pages.
 */
export const reportTabs = makeTabs(['properties', 'history'], {
  properties: 'Properties',
  history: 'History',
})

export type ReportTab = (typeof reportTabs.tabs)[number]
