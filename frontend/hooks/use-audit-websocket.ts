'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { Finding, AgentStatus } from '@/lib/types'

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
    error: string
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

  const connect = useCallback(() => {
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
              setFindings((prev) => [...prev, ...data.findings])
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
            connect()
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

  return {
    findings,
    agentStatuses,
    connectionStatus,
    reconnect,
  }
}
