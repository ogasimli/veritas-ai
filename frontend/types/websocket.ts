/**
 * WebSocket message types for audit real-time updates
 */

import type { AgentError } from '@/lib/types'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export type WebSocketMessage =
    | {
        type: 'agent_started'
        agent_id: string
        timestamp: string
    }
    | {
        type: 'agent_completed'
        agent_id: string
        findings_count: number
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
