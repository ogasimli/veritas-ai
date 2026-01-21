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

  return (
    <div className="space-y-1">
      {audits.map((audit) => {
        const isActive = pathname === `/audit/${audit.id}`
        return (
          <Link
            key={audit.id}
            href={`/audit/${audit.id}`}
            className={`block rounded-lg border px-4 py-3 transition-colors ${
              isActive
                ? 'border-blue-500 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20'
                : 'border-transparent hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-slate-900 dark:text-white">
                {audit.name}
              </span>
              <span
                className={`text-xs font-medium ${
                  audit.status === 'complete'
                    ? 'text-green-600 dark:text-green-400'
                    : audit.status === 'processing'
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                {audit.status}
              </span>
            </div>
          </Link>
        )
      })}
    </div>
  )
}
