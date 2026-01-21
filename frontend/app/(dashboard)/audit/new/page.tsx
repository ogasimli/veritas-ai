'use client'

import { useState } from 'react'
import { FileUploadZone } from '@/components/audit/file-upload-zone'
import { AgentCard } from '@/components/audit/agent-card'
import { useAuditWebSocket } from '@/hooks/use-audit-websocket'
import { createAudit } from '@/lib/api'

export default function NewAuditPage() {
  const [currentYearFile, setCurrentYearFile] = useState<File | null>(null)
  const [priorYearFile, setPriorYearFile] = useState<File | null>(null)
  const [memosFile, setMemosFile] = useState<File | null>(null)
  const [processingStarted, setProcessingStarted] = useState(false)
  const [auditId, setAuditId] = useState<string | null>(null)

  const { findings, agentStatuses, connectionStatus } =
    useAuditWebSocket(auditId)

  const handleStartReview = async () => {
    if (!currentYearFile) {
      alert('Please upload at least the Current Year document')
      return
    }

    try {
      // Create audit and get ID
      const result = await createAudit('New Audit')
      setAuditId(result.id)
      setProcessingStarted(true)

      console.log('Creating audit with:', {
        auditId: result.id,
        currentYear: currentYearFile?.name,
        priorYear: priorYearFile?.name,
        memos: memosFile?.name,
      })

      // TODO: Upload files and start processing
      // await uploadFile(result.id, currentYearFile, 'current')
      // await startProcessing(result.id)
    } catch (error) {
      console.error('Error starting review:', error)
      alert('Failed to start review. Please try again.')
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

          {/* Live Findings Monitor */}
          <div className="mt-12">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Live Findings Monitor
              </h2>
              {processingStarted && (
                <div className="flex items-center gap-2">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      connectionStatus === 'connected'
                        ? 'bg-green-500'
                        : connectionStatus === 'connecting'
                        ? 'bg-amber-500 animate-pulse'
                        : 'bg-red-500'
                    }`}
                  />
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {connectionStatus === 'connected'
                      ? 'Connected'
                      : connectionStatus === 'connecting'
                      ? 'Connecting...'
                      : 'Disconnected'}
                  </span>
                </div>
              )}
            </div>

            {!processingStarted ? (
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
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <AgentCard
                  agent="numeric"
                  status={agentStatuses.numeric}
                  findings={findings.filter((f) => f.agent === 'numeric')}
                />
                <AgentCard
                  agent="logic"
                  status={agentStatuses.logic}
                  findings={findings.filter((f) => f.agent === 'logic')}
                />
                <AgentCard
                  agent="disclosure"
                  status={agentStatuses.disclosure}
                  findings={findings.filter((f) => f.agent === 'disclosure')}
                />
                <AgentCard
                  agent="external"
                  status={agentStatuses.external}
                  findings={findings.filter((f) => f.agent === 'external')}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
