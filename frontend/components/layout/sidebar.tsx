import Link from 'next/link'
import Image from 'next/image'

export function Sidebar() {
  return (
    <aside className="w-80 flex-shrink-0 border-r border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="flex h-full flex-col">
        {/* Logo Section */}
        <div className="border-b border-slate-200 p-6 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <Image
              src="/logo.png"
              alt="Veritas AI"
              width={32}
              height={32}
              className="rounded"
            />
            <div>
              <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
                Veritas AI
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                INTEGRITY AT SCALE
              </p>
            </div>
          </div>
        </div>

        {/* New Audit Button */}
        <div className="p-4">
          <Link
            href="/audit/new"
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-500 px-4 py-3 font-medium text-white transition-colors hover:bg-blue-600"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="h-5 w-5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
            New Audit
          </Link>
        </div>

        {/* Audit List Section */}
        <div className="flex-1 overflow-y-auto px-4">
          {/* Placeholder for AuditList component - will be added in Task 3 */}
        </div>

        {/* User Placeholder */}
        <div className="border-t border-slate-200 p-4 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500 text-sm font-medium text-white">
              JD
            </div>
            <div>
              <p className="text-sm font-medium text-slate-900 dark:text-white">
                Jane Doe
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Senior Auditor
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
