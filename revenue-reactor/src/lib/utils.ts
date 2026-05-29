import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function timeAgo(date: Date | string | null): string {
  if (!date) return '—'
  const d = new Date(date)
  const s = Math.floor((Date.now() - d.getTime()) / 1000)
  if (s < 60) return 'just now'
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const dy = Math.floor(h / 24)
  if (dy < 30) return `${dy}d ago`
  return `${Math.floor(dy / 30)}mo ago`
}

export function formatDate(date: Date | string | null): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function opportunityLabel(score: number): { label: string; emoji: string; cls: string } {
  if (score >= 81) return { label: 'URGENT', emoji: '🔥', cls: 'bg-red-100 text-red-800 border-red-200' }
  if (score >= 61) return { label: 'LIKELY', emoji: '⚡', cls: 'bg-orange-100 text-orange-800 border-orange-200' }
  return { label: 'POSSIBLE', emoji: '👀', cls: 'bg-yellow-100 text-yellow-800 border-yellow-200' }
}

export function churnLabel(score: number, level: string): { label: string; emoji: string; cls: string; border: string } {
  if (level === 'high' || score >= 71) return { label: 'HIGH RISK', emoji: '🚨', cls: 'bg-red-100 text-red-800', border: 'border-l-red-500' }
  if (level === 'medium' || score >= 41) return { label: 'WATCH', emoji: '⚠️', cls: 'bg-yellow-100 text-yellow-800', border: 'border-l-yellow-500' }
  return { label: 'SAFE', emoji: '✅', cls: 'bg-green-100 text-green-800', border: 'border-l-green-500' }
}
