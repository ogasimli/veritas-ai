/**
 * Hook for loading initial audit data and syncing agent statuses
 */

import { useEffect, useState } from 'react'
import type { AgentResult, AgentStatus } from '@/lib/types'
import { fetchAuditResults, fetchAudit } from '@/lib/api'
import { transformDatabaseResult } from '@/utils/finding-transformers'

interface UseInitialAuditDataReturn {
    results: AgentResult[]
    agentStatuses: Record<string, AgentStatus['status']>
    isLoading: boolean
}

export function useInitialAuditData(auditId: string | null): UseInitialAuditDataReturn {
    const [results, setResults] = useState<AgentResult[]>([])
    const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus['status']>>({
        numeric: 'idle',
        logic: 'idle',
        disclosure: 'idle',
        external: 'idle',
    })
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        if (!auditId) {
            setIsLoading(false)
            return
        }

        const loadInitialData = async () => {
            setIsLoading(true)
            try {
                // Parallel fetch for results and audit status
                const [initialResults, audit] = await Promise.all([
                    fetchAuditResults(auditId),
                    fetchAudit(auditId).catch(() => null)
                ])

                /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
                const transformedResults = initialResults.map((r: any) =>
                    transformDatabaseResult(r)
                )

                setResults(transformedResults)

                // Initialize statuses based on results and audit status
                const newStatuses: Record<string, AgentStatus['status']> = {
                    numeric: 'idle',
                    logic: 'idle',
                    disclosure: 'idle',
                    external: 'idle',
                }

                // 1. Any agent with results is "complete" (or error if error present)
                // Group results by agent
                const agentResults = new Map<string, AgentResult[]>()
                transformedResults.forEach(r => {
                    if (!agentResults.has(r.agent)) agentResults.set(r.agent, [])
                    agentResults.get(r.agent)?.push(r)
                })

                agentResults.forEach((results, agentKey) => {
                    const hasError = results.some(r => r.error)
                    if (newStatuses[agentKey]) {
                        newStatuses[agentKey] = hasError ? 'error' : 'complete'
                    }
                })

                // 2. If the whole audit is "completed", remaining idle agents are also "complete" (no findings)
                if (audit?.status === 'completed') {
                    Object.keys(newStatuses).forEach(key => {
                        if (newStatuses[key as string] === 'idle') {
                            newStatuses[key as string] = 'complete'
                        }
                    })
                } else if (audit?.status === 'processing') {
                    // If still processing, non-completed agents should be "processing"
                    Object.keys(newStatuses).forEach(key => {
                        if (newStatuses[key as string] === 'idle') {
                            newStatuses[key as string] = 'processing'
                        }
                    })
                }

                setAgentStatuses(newStatuses)
            } catch (error) {
                console.error('Failed to load initial audit data:', error)
            } finally {
                setIsLoading(false)
            }
        }

        loadInitialData()
    }, [auditId])

    return {
        results,
        agentStatuses,
        isLoading
    }
}
