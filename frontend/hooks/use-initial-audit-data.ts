/**
 * Hook for loading initial audit data and syncing agent statuses
 */

import { useEffect, useState } from 'react'
import type { Finding, AgentStatus } from '@/lib/types'
import { fetchAuditFindings, fetchAudit } from '@/lib/api'
import { transformFinding } from '@/utils/finding-transformers'

interface UseInitialAuditDataReturn {
    findings: Finding[]
    agentStatuses: Record<string, AgentStatus['status']>
    isLoading: boolean
}

export function useInitialAuditData(auditId: string | null): UseInitialAuditDataReturn {
    const [findings, setFindings] = useState<Finding[]>([])
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
                // Parallel fetch for findings and audit status
                const [initialFindings, audit] = await Promise.all([
                    fetchAuditFindings(auditId),
                    fetchAudit(auditId).catch(() => null)
                ])

                /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
                const transformedFindings = initialFindings.map((f: any, i: number) =>
                    transformFinding(f, f.agent_id || 'unknown', i)
                )

                setFindings(transformedFindings)

                // Initialize statuses based on findings and audit status
                const newStatuses: Record<string, AgentStatus['status']> = {
                    numeric: 'idle',
                    logic: 'idle',
                    disclosure: 'idle',
                    external: 'idle',
                }

                // 1. Any agent with findings is "complete"
                const completedAgents = new Set(transformedFindings.map((f: Finding) => f.agent))
                completedAgents.forEach(agentKey => {
                    if (newStatuses[agentKey as string]) {
                        newStatuses[agentKey as string] = 'complete'
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
        findings,
        agentStatuses,
        isLoading
    }
}
