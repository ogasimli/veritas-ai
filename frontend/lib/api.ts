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
    const response = await fetch(`${API_URL}/documents/upload`, {
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
