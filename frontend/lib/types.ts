export type Finding = {
  id: string
  agent: string
  severity: 'critical' | 'warning' | 'pass'
  title: string
  description: string
}

export type AgentStatus = {
  agent: string
  status: 'idle' | 'processing' | 'complete' | 'error'
}

export type Audit = {
  id: string
  name: string
  status: string
  createdAt: string
  updatedAt?: string
}
