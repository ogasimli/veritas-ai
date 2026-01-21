export type Audit = {
  id: string
  name: string
  status: string
  createdAt: string
}

export async function fetchAudits(): Promise<Audit[]> {
  // Mock data for now - will be replaced with actual API call
  return [
    {
      id: '1',
      name: 'Audit #001',
      status: 'complete',
      createdAt: new Date().toISOString(),
    },
  ]
}

export async function createAudit(name: string): Promise<{ id: string }> {
  // TODO: Replace with actual API call to POST /api/audits
  // For now, return mock ID
  return {
    id: Math.random().toString(36).substring(7),
  }
}

export async function uploadFile(
  auditId: string,
  file: File,
  type: 'current' | 'prior' | 'memos'
): Promise<void> {
  // TODO: Replace with actual API call to POST /api/documents
  const formData = new FormData()
  formData.append('file', file)
  formData.append('auditId', auditId)
  formData.append('type', type)

  // Mock upload for now
  console.log(`Uploading ${type} file:`, file.name)
}

export async function startProcessing(auditId: string): Promise<void> {
  // TODO: Replace with actual API call to POST /api/audits/{id}/process
  console.log(`Starting processing for audit ${auditId}`)

  // Mock: Backend will send WebSocket updates as processing happens
  // For now, just log
}
