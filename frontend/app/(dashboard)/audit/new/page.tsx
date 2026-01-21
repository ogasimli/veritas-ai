'use client'

import { useState } from 'react'
import { FileUploadZone } from '@/components/audit/file-upload-zone'

export default function NewAuditPage() {
  const [currentYearFile, setCurrentYearFile] = useState<File | null>(null)
  const [priorYearFile, setPriorYearFile] = useState<File | null>(null)
  const [memosFile, setMemosFile] = useState<File | null>(null)

  const handleStartReview = async () => {
    if (!currentYearFile) {
      alert('Please upload at least the Current Year document')
      return
    }

    // TODO: Create audit via API and upload files
    console.log('Creating audit with:', {
      currentYear: currentYearFile?.name,
      priorYear: priorYearFile?.name,
      memos: memosFile?.name,
    })

    // TODO: Navigate to processing view
  }

  const hasAnyFile = currentYearFile || priorYearFile || memosFile

  return (
    <div className="flex h-full flex-col bg-slate-50 dark:bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
              New Audit
            </h1>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Upload financial documents to begin automated validation
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              Draft
            </span>
          </div>
        </div>
      </div>

      {/* Upload Zones */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <FileUploadZone
              label="Current Year (Required)"
              onUpload={(file) => setCurrentYearFile(file)}
            />
            <FileUploadZone
              label="Prior Year (Optional)"
              onUpload={(file) => setPriorYearFile(file)}
            />
            <FileUploadZone
              label="Internal Memos (Optional)"
              onUpload={(file) => setMemosFile(file)}
            />
          </div>

          {/* Start Review Button */}
          {hasAnyFile && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={handleStartReview}
                className="rounded-lg bg-blue-500 px-8 py-3 font-medium text-white transition-colors hover:bg-blue-600 disabled:opacity-50"
                disabled={!currentYearFile}
              >
                Start Review
              </button>
            </div>
          )}

          {/* Live Findings Monitor - Empty State */}
          <div className="mt-12">
            <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-white">
              Live Findings Monitor
            </h2>
            <div className="rounded-lg border-2 border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-600 dark:bg-slate-900">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="mx-auto h-12 w-12 text-slate-400"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6"
                />
              </svg>
              <h3 className="mt-4 text-lg font-medium text-slate-900 dark:text-white">
                Monitoring Inactive
              </h3>
              <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Real-time analysis and findings will appear here automatically
                once the review process is initiated
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
