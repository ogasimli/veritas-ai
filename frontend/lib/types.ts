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

export type Audit = {
  id: string
  name: string
  status: string
  created_at: string
  updated_at?: string
  documents: Document[]
}
