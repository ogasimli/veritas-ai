/**
 * WebSocket message types for audit real-time updates
 */

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
        timestamp: string
    }
    | {
        type: 'audit_complete'
        timestamp: string
    }
