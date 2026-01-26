'use client'

import { useState, use } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AgentCard } from '@/components/audit/agent-card'
import { ExportButton } from '@/components/audit/export-button'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'
import { useAuditWebSocket } from '@/hooks/use-audit-websocket'
import { fetchAudit, deleteAudit } from '@/lib/api'
import { type Audit } from '@/lib/types'
import { Trash2 } from 'lucide-react'

// NOTE: In Next.js App Router, params is a Promise which needs to be unwrapped.
// However, the exact behavior depends on the version. We'll use React.use() if available or await it.
// Actually, since this is a Client Component ('use client'), we receive params as a prop.
// Check if params is a Promise in Next.js 15, but for 14 it's usually just params.
// Let's assume params is passed directly or awaited in parent.
// Wait, for client components in Next.js 13+, params might be passed as props.
// BUT, to be safe with newer Next.js versions where params might be a promise even in client components
// (or passed from server component page wrapper), let's inspect usage.
// Standard pattern: keep Page as server component and import a client component.
// But we want to use 'use client' for hooks.

// Let's stick to the simple pattern:
// export default function AuditDetailsPage({ params }: { params: { id: string } }) { ... }

export default function AuditDetailsPage({ params }: { params: Promise<{ id: string }> }) {
    const { id: auditId } = use(params)
    const router = useRouter()
    const queryClient = useQueryClient()
    const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)

    const { findings, agentStatuses, connectionStatus } = useAuditWebSocket(auditId)

    // Fetch audit details for header info
    const { data: audit, isLoading: isLoadingAudit } = useQuery({
        queryKey: ['audit', auditId],
        queryFn: () => fetchAudit(auditId),
    })

    const handleDelete = (e: React.MouseEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDeleteDialogOpen(true)
    }

    const confirmDelete = async () => {
        try {
            await deleteAudit(auditId)
            // Invalidate query to refresh the list
            await queryClient.invalidateQueries({ queryKey: ['audits'] })

            // Get current audits from cache to decide navigation
            const audits = queryClient.getQueryData<Audit[]>(['audits'])
            const remainingAudits = audits?.filter(a => a.id !== auditId) || []

            if (remainingAudits.length > 0) {
                router.push(`/audit/${remainingAudits[0].id}`)
            } else {
                router.push('/audit/new')
            }
        } catch (error) {
            console.error('Failed to delete audit:', error)
            alert('Failed to delete audit')
        }
    }

    if (isLoadingAudit) {
        return (
            <div className="flex h-full items-center justify-center bg-slate-50 dark:bg-slate-950">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-500 dark:border-slate-700 dark:border-t-blue-400" />
            </div>
        )
    }

    if (!audit) {
        return (
            <div className="flex h-full flex-col items-center justify-center bg-slate-50 dark:bg-slate-950">
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Audit not found</h2>
                <button onClick={() => router.push('/audit/new')} className="mt-4 text-blue-500 hover:underline">
                    Go back to New Audit
                </button>
            </div>
        )
    }

    return (
        <div className="flex h-full flex-col bg-slate-50 dark:bg-slate-950">
            {/* Header */}
            <div className="border-b border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">
                            {audit.name || `Audit ${auditId.substring(0, 8)}`}
                        </h1>
                        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                            Created on {new Date(audit.created_at).toLocaleDateString()}
                        </p>
                    </div>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={handleDelete}
                            className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                            title="Delete Audit"
                        >
                            <Trash2 className="h-5 w-5" />
                        </button>
                        <div className="flex items-center gap-2">
                            <div
                                className={`h-2 w-2 rounded-full ${connectionStatus === 'connected'
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
                        <ExportButton findings={findings} disabled={findings.length === 0} />
                    </div>
                </div>
            </div>

            {/* Findings Monitor */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="mx-auto max-w-7xl">
                    <div className="mt-6">
                        <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2">
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
                    </div>
                </div>
            </div>

            <ConfirmationDialog
                isOpen={isDeleteDialogOpen}
                onClose={() => setIsDeleteDialogOpen(false)}
                onConfirm={confirmDelete}
                title="Delete Audit"
                description="Are you sure you want to delete this audit? This action cannot be undone and all findings will be permanently removed."
                confirmText="Delete"
                variant="danger"
            />
        </div >
    )
}
