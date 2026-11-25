import type { schemas } from './client'

export type User = schemas['UserSchema']
export type Company = schemas['CompanySchema']
export type Property = schemas['PropertySchema']
export type Transaction = schemas['TransactionSchema']
export type TransactionSummary = schemas['TransactionSummary']
export type PropertyBalance = schemas['PropertyBalance']
export type PaymentMethod = schemas['PaymentMethod']
export type TransactionType = schemas['TransactionType']
export type Role = schemas['Role']
export type Report = schemas['ReportSchema']
export type SentStatement = schemas['SentStatementSchema']
export type ManagedUser = schemas['ManagedUserSchema']
export type RecipientKind = schemas['RecipientKind']
/** Someone who can log in, as the report screens name them (Doorstep's member). */
export type Member = ManagedUser & { user_id: string }
export type Checklist = schemas['ChecklistSchema']
export type ChecklistItem = schemas['ChecklistItemSchema']
export type ChecklistType = schemas['ChecklistType']
export type Invoice = schemas['InvoiceSchema']
export type GuestExpense = schemas['GuestExpenseSchema']
export type ChecklistProperty = schemas['ChecklistPropertySchema']
