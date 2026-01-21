'use client'

import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { fetchAudits } from '@/lib/api'

export function AuditList() {
  const pathname = usePathname()
  const { data: audits, isLoading } = useQuery({
    queryKey: ['audits'],
    queryFn: fetchAudits,
  })

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800"
          />
        ))}
      </div>
    )
  }

  if (!audits || audits.length === 0) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          No audits yet
        </p>
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      complete: {
        bg: 'bg-green-100 dark:bg-green-900/30',
        text: 'text-green-700 dark:text-green-400',
        border: 'border-green-500',
      },
      processing: {
        bg: 'bg-blue-100 dark:bg-blue-900/30',
        text: 'text-blue-700 dark:text-blue-400',
        border: 'border-blue-500',
      },
      error: {
        bg: 'bg-red-100 dark:bg-red-900/30',
        text: 'text-red-700 dark:text-red-400',
        border: 'border-red-500',
      },
      draft: {
        bg: 'bg-slate-100 dark:bg-slate-800',
        text: 'text-slate-600 dark:text-slate-400',
        border: 'border-slate-300',
      },
    }
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.draft
    return (
      <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${config.bg} ${config.text} ${config.border}`}>
        {status}
      </span>
    )
  }

  return (
    <div className="space-y-2">
      {audits.map((audit) => {
        const isActive = pathname === `/audit/${audit.id}`
        return (
          <Link
            key={audit.id}
            href={`/audit/${audit.id}`}
            className={`block rounded-lg border-l-4 px-4 py-3 transition-all duration-200 ${
              isActive
                ? 'border-blue-500 bg-blue-50 shadow-sm dark:bg-blue-900/20'
                : 'border-transparent bg-white hover:border-slate-300 hover:bg-slate-50 hover:shadow-sm dark:bg-slate-900 dark:hover:bg-slate-800'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate font-medium text-slate-900 dark:text-white">
                {audit.name}
              </span>
              {getStatusBadge(audit.status)}
            </div>
          </Link>
        )
      })}
    </div>
  )
}
