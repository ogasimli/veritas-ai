'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { Finding, AgentStatus } from '@/lib/types'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

type WebSocketMessage =
  | { type: 'finding'; finding: Finding }
  | { type: 'agent_status'; agent: string; status: AgentStatus['status'] }
  | { type: 'complete' }

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
            case 'finding':
              setFindings((prev) => [...prev, data.finding])
              break

            case 'agent_status':
              setAgentStatuses((prev) => ({
                ...prev,
                [data.agent]: data.status,
              }))
              break

            case 'complete':
              console.log('Audit processing complete')
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
