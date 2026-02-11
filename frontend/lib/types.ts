export type AgentResult = {
  id: string
  agent: string

  // Success fields (optional)
  severity?: 'critical' | 'warning' | 'pass'
  title?: string
  description?: string
  reasoning?: string

  // Error fields (optional)
  error?: string

  // Common fields
  raw_data: Record<string, unknown>
}

export type AgentStatus = {
  agent: string
  status: 'idle' | 'running' | 'processing' | 'complete' | 'error'
}

export type Document = {
  id: string
  job_id: string
  filename: string
  content_type: string
  gcs_path: string
  extracted_text?: string
  created_at: string
}

export type AgentId = 'numeric_validation' | 'logic_consistency' | 'disclosure_compliance' | 'external_signal'

export const ALL_AGENT_IDS: AgentId[] = [
  'numeric_validation',
  'logic_consistency',
  'disclosure_compliance',
  'external_signal',
]

export const AGENT_LABELS: Record<AgentId, string> = {
  numeric_validation: 'Numeric Validation',
  logic_consistency: 'Logic Consistency',
  disclosure_compliance: 'Disclosure Compliance',
  external_signal: 'External Signals',
}

export type Audit = {
  id: string
  name: string
  status: string
  enabled_agents: AgentId[]
  created_at: string
  updated_at?: string
  documents: Document[]
}
