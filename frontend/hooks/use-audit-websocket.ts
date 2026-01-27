'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import type { AgentResult, AgentStatus } from '@/lib/types'
import type { WebSocketMessage, ConnectionStatus } from '@/types/websocket'
import { mapAgentId } from '@/utils/agent-mapping'
import { transformDatabaseResult } from '@/utils/finding-transformers'
import { useInitialAuditData } from './use-initial-audit-data'
import { fetchAgentResults } from '@/lib/api'

/**
 * Hook for managing WebSocket connection and real-time audit updates
 */
export function useAuditWebSocket(auditId: string | null) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectAttempted = useRef(false)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')

  // Load initial audit data
  const {
    results: initialResults,
    agentStatuses: initialStatuses
  } = useInitialAuditData(auditId)

  // WebSocket state (merges with initial data)
  const [results, setResults] = useState<AgentResult[]>(initialResults)
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus['status']>>(initialStatuses)

  // Sync initial data when it loads
  useEffect(() => {
    setResults(initialResults)
    setAgentStatuses(initialStatuses)
  }, [initialResults, initialStatuses])

  /**
   * Fetch results for a specific agent from the database
   */
  const loadAgentResults = useCallback(async (jobId: string, agentId: string) => {
    try {
      const dbResults = await fetchAgentResults(jobId, agentId)

      /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
      const transformedResults = dbResults.map((r: any) => transformDatabaseResult(r))

      setResults((prev) => {
        // Use database IDs to prevent duplicates
        const existingIds = new Set(prev.map(r => r.id))
        const newResults = transformedResults.filter((r: AgentResult) => !existingIds.has(r.id))
        return [...prev, ...newResults]
      })

      return transformedResults
    } catch (error) {
      console.error(`Error fetching results for ${agentId}:`, error)
      return []
    }
  }, [])

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

          // Fetch results from DB to determine status (complete vs error)
          console.log(`Agent ${data.agent_id} completed. Fetching results...`)

          if (auditId) {
            loadAgentResults(auditId, data.agent_id).then((newResults) => {
              const hasError = newResults.some(r => !!r.error)
              setAgentStatuses((prev) => ({
                ...prev,
                [agentKey]: hasError ? 'error' : 'complete',
              }))
              console.log(`Agent ${data.agent_id} status updated to: ${hasError ? 'error' : 'complete'}`)
            })
          }
          break
        }

        case 'audit_complete':
          console.log('Audit processing complete')
          break

        default:
          console.log('Unknown message type:', data)
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error)
    }
  }, [auditId, loadAgentResults])

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
    results, // Renamed from findings
    agentStatuses,
    connectionStatus,
    reconnect,
  }
}
