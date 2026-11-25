import { makeTabs } from '@/lib/page-tabs'

/**
 * The Checklists page has two halves: who hears about each property's walks,
 * and the walks themselves. Same subject from two sides, so they are tabs on
 * one page rather than two pages.
 */
export const checklistTabs = makeTabs(['properties', 'history'], {
  properties: 'Properties',
  history: 'History',
})

export type ChecklistTab = (typeof checklistTabs.tabs)[number]
