import {
  Banknote,
  Briefcase,
  BrushCleaning,
  Car,
  CircleEllipsis,
  ConciergeBell,
  House,
  Lamp,
  Landmark,
  type LucideIcon,
  Package,
  ReceiptText,
  ShieldCheck,
  ShoppingCart,
  Truck,
  UserRound,
  Utensils,
  Wrench,
  Zap,
} from 'lucide-react'

/**
 * Categories are free text, typed as expenses are recorded, so the known ones
 * get a picture and anything new gets the "other" one until it is added here.
 */
const ICONS: Record<string, LucideIcon> = {
  utilities: Zap,
  'maintenance/projects': Wrench,
  supermarket: ShoppingCart,
  staff: UserRound,
  housekeeping: BrushCleaning,
  services: ConciergeBell,
  cars: Car,
  transport: Truck,
  transportation: Truck,
  government: Landmark,
  taxes: ReceiptText,
  atm: Banknote,
  housing: House,
  'e-commerce': Package,
  decoration: Lamp,
  office: Briefcase,
  insurance: ShieldCheck,
  food: Utensils,
}

export const categoryIcon = (category: string): LucideIcon =>
  ICONS[category.toLowerCase()] ?? CircleEllipsis
