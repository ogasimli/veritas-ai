'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { Finding, AgentStatus, AgentError } from '@/lib/types'
import type { WebSocketMessage, ConnectionStatus } from '@/types/websocket'
import { mapAgentId } from '@/utils/agent-mapping'
import { transformFinding } from '@/utils/finding-transformers'
import { useInitialAuditData } from './use-initial-audit-data'

/**
 * Hook for managing WebSocket connection and real-time audit updates
 */
export function useAuditWebSocket(auditId: string | null) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempted = useRef(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [agentErrors, setAgentErrors] = useState<Record<string, AgentError | null>>({})

  // Load initial audit data
  const {
    findings: initialFindings,
    agentStatuses: initialStatuses
  } = useInitialAuditData(auditId)

  // WebSocket state (merges with initial data)
  const [findings, setFindings] = useState<Finding[]>(initialFindings)
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus['status']>>(initialStatuses)

  // Sync initial data when it loads
  useEffect(() => {
    setFindings(initialFindings)
    setAgentStatuses(initialStatuses)
  }, [initialFindings, initialStatuses])

  /**
   * Handles incoming WebSocket messages
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data)

      switch (data.type) {
        case 'agent_started': {
          const agentKey = mapAgentId(data.agent_id)
          setAgentStatuses((prev) => ({
            ...prev,
            [agentKey]: 'processing',
          }))
          console.log(`Agent ${data.agent_id} started`)
          break
        }

        case 'agent_completed': {
          const agentKey = mapAgentId(data.agent_id)
          setAgentStatuses((prev) => ({
            ...prev,
            [agentKey]: 'complete',
          }))

          // Transform backend findings to frontend format
          /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
          const transformedFindings = data.findings.map((f: any, index: number) =>
            transformFinding(f, data.agent_id, index)
          )

          setFindings((prev) => [...prev, ...transformedFindings])
          console.log(`Agent ${data.agent_id} completed with ${data.findings.length} findings`)
          break
        }

        case 'audit_complete':
          console.log('Audit processing complete')
          break

        case 'agent_error': {
          console.error(`Agent ${data.agent_id} error:`, data.error)
          const agentKey = mapAgentId(data.agent_id)

          setAgentStatuses((prev) => ({
            ...prev,
            [agentKey]: 'error',
          }))

          // Normalize error to AgentError type
          const errorData: AgentError = typeof data.error === 'string'
            ? {
              agent_name: data.agent_id,
              error_type: 'Error',
              error_message: data.error,
            }
            : data.error

          setAgentErrors((prev) => ({
            ...prev,
            [agentKey]: errorData,
          }))
          break
        }

        default:
          console.log('Unknown message type:', data)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }, [])

  /**
   * Establishes WebSocket connection
   */
  const connect = useCallback(function connectFn() {
    if (!auditId) return

    setConnectionStatus('connecting')

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const wsUrl = apiUrl.replace(/^http/, 'ws')
      const websocket = new WebSocket(`${wsUrl}/ws/audit/${auditId}`)

      websocket.onopen = () => {
        console.log('WebSocket connected')
        setConnectionStatus('connected')
      }

      websocket.onmessage = handleMessage

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
  }, [auditId, handleMessage])

  /**
   * Manually reconnect to WebSocket
   */
  const reconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close()
    }
    reconnectAttempted.current = false
    connect()
  }, [connect])

  // Connect on mount and cleanup on unmount
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

  return {
    findings,
    agentStatuses,
    agentErrors,
    connectionStatus,
    reconnect,
  }
}
