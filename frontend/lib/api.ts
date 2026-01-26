import type { Audit, Finding } from './types'


const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchAudits(): Promise<Audit[]> {
  const response = await fetch(`${API_URL}/api/v1/jobs/`)
  if (!response.ok) {
    throw new Error('Failed to fetch audits')
  }
  return response.json()
}

export async function deleteAudit(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${id}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error('Failed to delete audit')
  }
}

export async function updateAudit(id: string, updates: Partial<Audit>): Promise<Audit> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  })
  if (!response.ok) {
    throw new Error('Failed to update audit')
  }
  return response.json()
}

/**
 * Upload a document file to the backend for processing
 * @param file The .docx file to upload
 * @returns The job ID (UUID as string) for tracking processing status
 */
export async function uploadFile(file: File): Promise<string> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const formData = new FormData()
  formData.append('file', file)

  try {
    const response = await fetch(`${API_URL}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Upload failed: ${response.status} ${errorText}`)
    }

    const data = await response.json()

    // Backend returns JobRead schema with id (UUID)
    if (!data.id) {
      throw new Error('Invalid response from server: missing job ID')
    }

    // Return job ID as string
    return data.id.toString()
  } catch (error) {
    console.error('File upload error:', error)
    throw error
  }
}

export async function fetchAuditFindings(jobId: string): Promise<Finding[]> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/findings`)
  if (!response.ok) {
    throw new Error('Failed to fetch findings')
  }
  return response.json()
}

export async function fetchAudit(id: string): Promise<Audit> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${id}`)
  if (!response.ok) {
    throw new Error('Failed to fetch audit')
  }
  return response.json()
}
