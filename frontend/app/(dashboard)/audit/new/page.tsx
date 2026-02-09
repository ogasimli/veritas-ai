'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { FileUploadZone } from '@/components/audit/file-upload-zone'
import { uploadFile } from '@/lib/api'

export default function NewAuditPage() {
  const router = useRouter()
  const queryClient = useQueryClient()
  const [currentYearFile, setCurrentYearFile] = useState<File | null>(null)
  const [priorYearFile, setPriorYearFile] = useState<File | null>(null)
  const [memosFile, setMemosFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleStartReview = async () => {
    if (!currentYearFile) {
      alert('Please upload at least the Current Year document')
      return
    }

    setIsUploading(true)

    try {
      // Upload file to backend - this creates the job and starts processing automatically
      const jobId = await uploadFile(currentYearFile)

      console.log('File uploaded, job created:', {
        jobId,
        fileName: currentYearFile.name,
      })

      // Invalidate audits query to refresh the sidebar with the new audit
      await queryClient.invalidateQueries({ queryKey: ['audits'] })

      // Navigate to the new audit details page
      router.push(`/audit/${jobId}`)

      // Backend automatically starts processing in background task
      // WebSocket will receive agent_started, agent_completed, audit_complete messages
    } catch (error) {
      console.error('Error starting review:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to start review: ${errorMessage}. Please try again.`)
      setIsUploading(false)
    }
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

        </div>
      </div>

      {/* Upload Zones */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            <FileUploadZone
              label="Current Year (Required)"
              onFileChange={(file) => setCurrentYearFile(file)}
            />
            <div className="relative overflow-hidden rounded-lg">
              {/* Overlay */}
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/40 backdrop-blur-[2px] transition-all duration-300 dark:bg-slate-950/40">
                <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/90 px-4 py-2 shadow-sm backdrop-blur-md dark:border-slate-700 dark:bg-slate-800/90">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="h-4 w-4 text-slate-500 dark:text-slate-400"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
                    />
                  </svg>
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                    Coming Soon
                  </span>
                </div>
              </div>
              <div className="pointer-events-none grayscale filter">
                <FileUploadZone
                  label="Prior Year (Optional)"
                  onFileChange={(file) => setPriorYearFile(file)}
                />
              </div>
            </div>
            <div className="relative overflow-hidden rounded-lg">
              {/* Overlay */}
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/40 backdrop-blur-[2px] transition-all duration-300 dark:bg-slate-950/40">
                <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white/90 px-4 py-2 shadow-sm backdrop-blur-md dark:border-slate-700 dark:bg-slate-800/90">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={1.5}
                    stroke="currentColor"
                    className="h-4 w-4 text-slate-500 dark:text-slate-400"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
                    />
                  </svg>
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                    Coming Soon
                  </span>
                </div>
              </div>
              <div className="pointer-events-none grayscale filter">
                <FileUploadZone
                  label="Internal Memos (Optional)"
                  onFileChange={(file) => setMemosFile(file)}
                />
              </div>
            </div>
          </div>

          {/* Start Review Button */}
          {hasAnyFile && (
            <div className="mt-8 flex justify-center">
              <button
                onClick={handleStartReview}
                className="w-full rounded-lg bg-blue-500 px-8 py-3 font-medium text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
                disabled={!currentYearFile || isUploading}
              >
                {isUploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg
                      className="h-4 w-4 animate-spin"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Uploading...
                  </span>
                ) : (
                  'Start Review'
                )}
              </button>
            </div>
          )}

          {/* Findings Feed - Placeholder */}
          <div className="mt-12">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Findings Feed
              </h2>
            </div>

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
