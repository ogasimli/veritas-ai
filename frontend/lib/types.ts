export type Finding = {
  id: string
  agent: string
  severity: 'critical' | 'warning' | 'pass'
  title: string
  description: string
  reasoning?: string // Added for detailed output details (Expected/Actual)
}

export type AgentStatus = {
  agent: string
  status: 'idle' | 'running' | 'processing' | 'complete' | 'error'
}

export type Audit = {
  id: string
  name: string
  status: string
  created_at: string
  updated_at?: string
}

export type AgentError = {
  agent_name: string
  error_type: string
  error_message: string
}
