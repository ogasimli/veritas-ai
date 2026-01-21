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
