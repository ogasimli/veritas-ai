'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { Finding, AgentStatus, AgentError } from '@/lib/types'
import { fetchAuditFindings } from '@/lib/api'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

// Map backend agent_id to frontend agent keys
function mapAgentId(agentId: string): string {
  const mapping: Record<string, string> = {
    numeric_validation: 'numeric',
    logic_consistency: 'logic',
    disclosure_compliance: 'disclosure',
    external_signal: 'external',
  }
  return mapping[agentId] || agentId
}

// Map backend severity to frontend severity
function mapSeverity(backendSeverity: string): 'critical' | 'warning' | 'pass' {
  if (backendSeverity === 'high') return 'critical'
  if (backendSeverity === 'medium' || backendSeverity === 'low') return 'warning'
  return 'warning'
}

// TODO: Consolidate backend agent schemas to return a uniform data type for findings.
// This will allow us to remove 'any' and use a strict union or base type.
/* eslint-disable @typescript-eslint/no-explicit-any */
function transformFinding(f: any, agentId: string, index: number): Finding {
  const agentKey = mapAgentId(agentId)

  // Transform based on agent type and actual schema
  if (agentKey === 'numeric') {
    // Schema: fsli_name, summary, severity, expected_value, actual_value, discrepancy, source_refs
    return {
      id: `${agentKey}-${index}-${Date.now()}`, // Ensure unique ID
      agent: agentKey,
      severity: mapSeverity(f.severity || 'medium'),
      title: f.summary || `${f.fsli_name}: Numeric discrepancy`,
      description: `Expected: ${f.expected_value}, Actual: ${f.actual_value}, Discrepancy: ${f.discrepancy}`,
      reasoning: f.reasoning // Pass through reasoning if available
    }
  } else if (agentKey === 'logic') {
    // Schema: fsli_name, claim, contradiction, severity, reasoning, source_refs
    return {
      id: `${agentKey}-${index}-${Date.now()}`,
      agent: agentKey,
      severity: mapSeverity(f.severity || 'medium'),
      title: f.contradiction || 'Logic inconsistency',
      description: `Claim: ${f.claim || ''}. ${f.reasoning || ''}`,
      reasoning: f.reasoning
    }
  } else if (agentKey === 'disclosure') {
    // Schema: standard, disclosure_id, requirement, severity, description
    return {
      id: `${agentKey}-${index}-${Date.now()}`,
      agent: agentKey,
      severity: mapSeverity(f.severity || 'medium'),
      title: `${f.standard || ''} - ${f.requirement || 'Missing disclosure'}`,
      description: f.description || '',
      reasoning: f.reasoning
    }
  } else if (agentKey === 'external') {
    // Two schemas:
    // 1) Internet-to-Report: signal_type, summary, source_url, publication_date, potential_contradiction
    // 2) Report-to-Internet: claim, status, evidence_summary, source_urls, discrepancy
    if (f.claim && f.status) {
      // Report-to-Internet verification
      return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: f.status === 'CONTRADICTED' ? 'critical' : f.status === 'VERIFIED' ? 'pass' : 'warning',
        title: `${f.status}: ${f.claim}`,
        description: `${f.evidence_summary || ''}${f.discrepancy ? ' | Discrepancy: ' + f.discrepancy : ''}`,
        reasoning: f.reasoning
      }
    } else {
      // Internet-to-Report finding
      return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: f.signal_type === 'financial_distress' || f.signal_type === 'litigation' ? 'critical' : 'warning',
        title: `${f.signal_type || 'External signal'}: ${f.summary || ''}`,
        description: `${f.potential_contradiction || ''}${f.publication_date ? ' (Published: ' + f.publication_date + ')' : ''}`,
        reasoning: f.reasoning
      }
    }
  }

  // Fallback for unknown structure
  return {
    id: `${agentKey}-${index}-${Date.now()}`,
    agent: agentKey,
    severity: 'warning' as const,
    title: f.title || f.summary || f.requirement || f.claim || 'Finding',
    description: f.description || f.reasoning || f.evidence_summary || '',
    reasoning: f.reasoning
  }
}
/* eslint-enable @typescript-eslint/no-explicit-any */

type WebSocketMessage =
  | {
    type: 'agent_started'
    agent_id: string
    timestamp: string
  }
  | {
    type: 'agent_completed'
    agent_id: string
    findings: Finding[]
    timestamp: string
  }
  | {
    type: 'audit_complete'
    timestamp: string
  }
  | {
    type: 'agent_error'
    agent_id: string
    error: AgentError | string
    timestamp: string
  }

export function useAuditWebSocket(auditId: string | null) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempted = useRef(false)
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>('disconnected')
  const [findings, setFindings] = useState<Finding[]>([])
  const [agentStatuses, setAgentStatuses] = useState<
    Record<string, AgentStatus['status']>
  >({
    numeric: 'idle',
    logic: 'idle',
    disclosure: 'idle',
    external: 'idle',
  })
  const [agentErrors, setAgentErrors] = useState<Record<string, AgentError | null>>({})

  const connect = useCallback(function connectFn() {
    if (!auditId) return

    setConnectionStatus('connecting')

    try {
      const websocket = new WebSocket(
        `ws://localhost:8000/ws/audit/${auditId}`
      )

      websocket.onopen = () => {
        console.log('WebSocket connected')
        setConnectionStatus('connected')
      }

      websocket.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)

          switch (data.type) {
            case 'agent_started':
              // Map agent_id to frontend agent key format
              const startedAgentKey = mapAgentId(data.agent_id)
              setAgentStatuses((prev) => ({
                ...prev,
                [startedAgentKey]: 'running',
              }))
              console.log(`Agent ${data.agent_id} started`)
              break

            case 'agent_completed':
              // Map agent_id and add all findings from this agent
              const completedAgentKey = mapAgentId(data.agent_id)
              setAgentStatuses((prev) => ({
                ...prev,
                [completedAgentKey]: 'complete',
              }))


              // Transform backend findings to match frontend Finding type
              /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
              const transformedFindings = data.findings.map((f: any, index: number) =>
                transformFinding(f, data.agent_id, index)
              )


              setFindings((prev) => [...prev, ...transformedFindings])
              console.log(
                `Agent ${data.agent_id} completed with ${data.findings.length} findings`
              )
              break

            case 'audit_complete':
              console.log('Audit processing complete')
              break

            case 'agent_error':
              console.error(`Agent ${data.agent_id} error:`, data.error)
              const errorAgentKey = mapAgentId(data.agent_id)
              setAgentStatuses((prev) => ({
                ...prev,
                [errorAgentKey]: 'error',
              }))

              // Normalize error to AgentError type
              let errorData: AgentError
              if (typeof data.error === 'string') {
                errorData = {
                  agent_name: data.agent_id,
                  error_type: 'Error',
                  error_message: data.error,
                }
              } else {
                errorData = data.error
              }

              setAgentErrors((prev) => ({
                ...prev,
                [errorAgentKey]: errorData,
              }))
              break

            default:
              console.log('Unknown message type:', data)
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus('disconnected')
      }

      websocket.onclose = () => {
        console.log('WebSocket disconnected')
        setConnectionStatus('disconnected')

        // Auto-reconnect once after 2s delay if not already attempted
        if (!reconnectAttempted.current) {
          reconnectAttempted.current = true
          console.log('Attempting auto-reconnect in 2s...')
          setTimeout(() => {
            if (auditId) connectFn()
          }, 2000)
        }
      }

      ws.current = websocket
    } catch (error) {
      console.error('Error connecting to WebSocket:', error)
      setConnectionStatus('disconnected')
    }
  }, [auditId])

  const reconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close()
    }
    reconnectAttempted.current = false
    connect()
  }, [connect])

  useEffect(() => {
    if (auditId) {
      connect()
    }

    return () => {
      if (ws.current) {
        ws.current.close()
        ws.current = null
      }
    }
  }, [auditId, connect])

  // Load initial findings
  useEffect(() => {
    if (!auditId) return

    const loadFindings = async () => {
      try {
        const initialFindings = await fetchAuditFindings(auditId)
        /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
        const properlyTransformed = initialFindings.map((f: any, i: number) =>
          transformFinding(f, f.agent_id || 'unknown', i)
        )

        setFindings(properlyTransformed)
      } catch (error) {
        console.error('Failed to load initial findings:', error)
      }
    }

    loadFindings()
  }, [auditId])


  return {
    findings,
    agentStatuses,
    agentErrors,
    connectionStatus,
    reconnect,
  }
}
