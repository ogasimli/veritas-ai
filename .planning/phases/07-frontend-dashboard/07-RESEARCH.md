# Phase 7: Frontend Dashboard - Research

**Researched:** 2026-01-20
**Domain:** Next.js 14 App Router real-time dashboard with WebSocket integration
**Confidence:** HIGH

<research_summary>
## Summary

Researched the Next.js 14 App Router ecosystem for building a real-time dashboard with WebSocket integration, file upload with validation, and dark mode. The standard approach uses Next.js 14 App Router with server/client component separation, native WebSocket API for FastAPI backend connection, Shadcn UI components with react-dropzone for file upload, and next-themes for dark mode.

Key finding: **Don't build a custom WebSocket server in Next.js** - the App Router doesn't support WebSocket servers in Route Handlers, and serverless platforms like Vercel don't support WebSocket servers at all. Instead, use Next.js purely as a client that connects to your existing FastAPI WebSocket server.

The 2026 architecture trend combines React Server Components for initial data loading with Client Components for real-time features, using TanStack Query for server state caching and WebSocket for live updates.

**Primary recommendation:** Use Next.js 14 App Router with server components for layout/data fetching, client components for WebSocket/file upload/dark mode, native WebSocket API to connect to FastAPI backend, Shadcn UI + react-dropzone for file uploads, next-themes for dark mode, and TanStack Query for REST API state management.

</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for Next.js real-time dashboards:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 14.x | Full-stack React framework | App Router is production-ready, RSC + Client Components |
| React | 18.x | UI library | Required by Next.js, hooks for WebSocket integration |
| Shadcn UI | Latest | UI component library | Accessible, copy-paste, built on Radix UI primitives |
| TailwindCSS | 3.x | Utility-first CSS | Already in stack, integrates with Shadcn UI |

### Real-Time & State
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Native WebSocket | Browser API | WebSocket client | Connecting to FastAPI WebSocket server |
| TanStack Query | 5.x | Server state management | REST API calls, caching, optimistic updates |
| Zustand | 4.x | Client state management | Optional - for shared UI state (WebSocket connection status) |

### File Upload
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-dropzone | 14.x | Drag & drop file upload | Industry standard, handles validation, accessibility |
| zod | 3.x | Schema validation | Validate file types, sizes before upload |

### Dark Mode
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| next-themes | 0.3.x | Theme management | Official recommendation from Shadcn UI docs |

### Utilities
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json2csv | 6.x | CSV export | Simple JSON to CSV conversion |
| clsx / class-variance-authority | Latest | Conditional classNames | Managing Tailwind classes in components |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native WebSocket | Socket.IO | Socket.IO adds auto-reconnect but requires Socket.IO server (FastAPI doesn't use it) |
| Native WebSocket | next-ws | next-ws only works for Next.js-hosted WebSocket servers (not for external FastAPI) |
| TanStack Query | SWR | SWR is simpler but TanStack Query has more features (already in stack) |
| Zustand | Redux | Redux too complex for simple WebSocket state, Zustand is lightweight |

**Installation:**
```bash
# Core (already installed)
npm install next react react-dom

# UI & Styling (already installed)
npm install tailwindcss @shadcn/ui

# State & Data Fetching (already installed)
npm install @tanstack/react-query

# File Upload
npm install react-dropzone zod

# Dark Mode
npm install next-themes

# Export
npm install json2csv

# Optional: Client State
npm install zustand
```

</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
app/
├── (dashboard)/
│   ├── layout.tsx              # Server Component - sidebar, theme provider
│   ├── page.tsx                # Server Component - home/landing
│   └── audit/
│       ├── [id]/
│       │   └── page.tsx        # Server Component - fetch audit data
│       └── new/
│           └── page.tsx        # Server Component - wrapper for upload
components/
├── providers/
│   └── theme-provider.tsx      # Client Component - next-themes wrapper
├── ui/                         # Shadcn UI components (mix of server/client)
│   ├── button.tsx
│   ├── card.tsx
│   └── ...
├── audit/
│   ├── file-upload.tsx         # Client Component - drag & drop
│   ├── agent-card.tsx          # Client Component - WebSocket updates
│   ├── findings-list.tsx       # Client Component - real-time list
│   └── audit-list.tsx          # Client Component - clickable audit list
└── layout/
    ├── sidebar.tsx             # Server Component - static structure
    └── theme-toggle.tsx        # Client Component - theme switcher
hooks/
├── use-websocket.ts            # Custom hook for WebSocket connection
└── use-audit-state.ts          # Custom hook for audit state
lib/
├── api.ts                      # FastAPI REST client functions
└── utils.ts                    # Shared utilities
```

### Pattern 1: Server Component for Layout + Client for Interactivity
**What:** Use Server Components for static layout/structure, Client Components for real-time features
**When to use:** Always in App Router - default to server, opt into client only when needed
**Example:**
```typescript
// app/(dashboard)/layout.tsx - Server Component
import { Sidebar } from '@/components/layout/sidebar'
import { ThemeProvider } from '@/components/providers/theme-provider'

export default function DashboardLayout({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <div className="flex h-screen">
        <Sidebar /> {/* Server Component */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </ThemeProvider>
  )
}
```

### Pattern 2: WebSocket Client Connection in useEffect
**What:** Connect to FastAPI WebSocket server from Client Component using native WebSocket API
**When to use:** All real-time features (agent progress, live findings)
**Example:**
```typescript
// hooks/use-websocket.ts
'use client'

import { useEffect, useRef, useState } from 'react'

export function useWebSocket(auditId: string) {
  const ws = useRef<WebSocket | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting')

  useEffect(() => {
    // Connect to FastAPI WebSocket endpoint
    const websocket = new WebSocket(`ws://localhost:8000/ws/audit/${auditId}`)

    websocket.onopen = () => {
      setConnectionStatus('connected')
      console.log('WebSocket connected')
    }

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data)

      // Handle different message types from FastAPI
      if (data.type === 'finding') {
        setFindings(prev => [...prev, data.finding])
      } else if (data.type === 'agent_status') {
        // Update agent status
      }
    }

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error)
      setConnectionStatus('disconnected')
    }

    websocket.onclose = () => {
      setConnectionStatus('disconnected')
      console.log('WebSocket closed')
    }

    ws.current = websocket

    // Cleanup on unmount
    return () => {
      websocket.close()
    }
  }, [auditId])

  return { findings, connectionStatus, ws: ws.current }
}
```

### Pattern 3: File Upload with react-dropzone + Validation
**What:** Use react-dropzone for drag & drop, validate with zod before upload
**When to use:** All file upload features
**Example:**
```typescript
// components/audit/file-upload.tsx
'use client'

import { useDropzone } from 'react-dropzone'
import { z } from 'zod'

const fileSchema = z.object({
  name: z.string().endsWith('.docx', 'Only .docx files allowed'),
  size: z.number().max(10 * 1024 * 1024, 'File must be less than 10MB')
})

export function FileUpload() {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    onDrop: (acceptedFiles, rejectedFiles) => {
      // Validate with zod
      acceptedFiles.forEach(file => {
        try {
          fileSchema.parse(file)
          // Upload file
          handleUpload(file)
        } catch (error) {
          console.error('Validation error:', error)
        }
      })

      // Show errors for rejected files
      if (rejectedFiles.length > 0) {
        // Display error message
      }
    }
  })

  return (
    <div {...getRootProps()} className="border-2 border-dashed rounded-lg p-8">
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Drop the .docx file here...</p>
      ) : (
        <p>Drag & drop .docx file here, or click to select</p>
      )}
    </div>
  )
}
```

### Pattern 4: Dark Mode with next-themes
**What:** Wrap app in ThemeProvider, use useTheme hook in client components
**When to use:** Dark mode toggle, theme-aware components
**Example:**
```typescript
// components/providers/theme-provider.tsx
'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'

export function ThemeProvider({ children, ...props }) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}

// components/layout/theme-toggle.tsx
'use client'

import { useTheme } from 'next-themes'

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      {theme === 'dark' ? '☀️' : '🌙'}
    </button>
  )
}

// app/layout.tsx
import { ThemeProvider } from '@/components/providers/theme-provider'

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
```

### Pattern 5: Optimistic UI with TanStack Query
**What:** Update UI immediately, rollback on error
**When to use:** Creating new audits, updating audit state
**Example:**
```typescript
// Using TanStack Query for optimistic updates
import { useMutation, useQueryClient } from '@tanstack/react-query'

function useCreateAudit() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (newAudit) => fetch('/api/audits', { method: 'POST', body: JSON.stringify(newAudit) }),
    onMutate: async (newAudit) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['audits'] })

      // Snapshot previous value
      const previousAudits = queryClient.getQueryData(['audits'])

      // Optimistically update
      queryClient.setQueryData(['audits'], (old) => [...old, newAudit])

      // Return context with snapshot
      return { previousAudits }
    },
    onError: (err, newAudit, context) => {
      // Rollback on error
      queryClient.setQueryData(['audits'], context.previousAudits)
    },
    onSettled: () => {
      // Refetch after error or success
      queryClient.invalidateQueries({ queryKey: ['audits'] })
    }
  })
}
```

### Anti-Patterns to Avoid
- **Using 'use client' at the root layout**: Only mark components that need interactivity as client components
- **Accessing window/localStorage in Server Components**: Causes hydration errors, use useEffect in client components
- **Not cleaning up WebSocket connections**: Always close WebSocket in useEffect cleanup
- **Building WebSocket server in Next.js Route Handlers**: Route Handlers don't support WebSocket upgrades in production
- **Using Math.random() or Date.now() in Server Components**: Causes hydration mismatches, use in client components only

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File drag & drop UI | Custom drag event handlers | react-dropzone | Handles accessibility, keyboard navigation, file validation, edge cases |
| Dark mode system | Manual theme toggling + localStorage | next-themes | Prevents hydration mismatches, system preference detection, SSR-safe |
| CSV export | Manual CSV string building | json2csv | Handles escaping, quotes, special characters, nested objects |
| WebSocket reconnection | Custom retry logic | Native WebSocket + manual reconnect OR simple retry | FastAPI expects standard WebSocket, Socket.IO adds unnecessary complexity |
| Form validation | Manual regex checks | zod | Type-safe, composable schemas, better error messages |
| Optimistic updates | Manual state rollback | TanStack Query useMutation | Handles cancellation, rollback, refetch automatically |

**Key insight:** Next.js App Router is server-first by design. Don't fight the framework - use Server Components for static content, Client Components only for interactivity. The native WebSocket API is sufficient for simple real-time updates; don't add Socket.IO unless you need its specific features (which you don't when connecting to FastAPI).

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Hydration Mismatch from Browser APIs
**What goes wrong:** Accessing `window`, `localStorage`, or using `Date.now()` in Server Components causes "Text content does not match server-rendered HTML" errors
**Why it happens:** Server doesn't have browser APIs, generates different output than client
**How to avoid:** Use `useEffect` hook or `'use client'` directive, check `typeof window !== 'undefined'` before accessing browser APIs
**Warning signs:** Console errors about hydration mismatch, content flashing on page load

### Pitfall 2: WebSocket Connection Not Cleaned Up
**What goes wrong:** WebSocket connections remain open when component unmounts, causing memory leaks and multiple connections
**Why it happens:** Missing cleanup function in useEffect
**How to avoid:** Always return cleanup function from useEffect that calls `websocket.close()`
**Warning signs:** Multiple WebSocket connections in DevTools Network tab, increasing memory usage

### Pitfall 3: Trying to Use WebSocket Servers in Next.js App Router
**What goes wrong:** Attempting to create WebSocket server in Route Handlers fails in production
**Why it happens:** Route Handlers only support Request/Response, not protocol upgrade
**How to avoid:** Keep FastAPI as WebSocket server, use Next.js as client only
**Warning signs:** Works in development but fails on Vercel/serverless deployment

### Pitfall 4: File Upload Without Proper Validation
**What goes wrong:** Users upload wrong file types, oversized files, crashes backend
**Why it happens:** Client-side validation skipped or incomplete
**How to avoid:** Use react-dropzone `accept` prop + zod schema validation, show clear error messages
**Warning signs:** Backend errors from invalid files, poor UX with unclear rejection reasons

### Pitfall 5: Dark Mode Flash (FOUT - Flash of Unstyled Theme)
**What goes wrong:** Page loads in light mode then flashes to dark mode
**Why it happens:** Theme applied after initial render, not reading system preference correctly
**How to avoid:** Use next-themes with `suppressHydrationWarning` on html tag, set `defaultTheme="system"`
**Warning signs:** Visible theme flash on page load, especially on refresh

### Pitfall 6: Not Handling WebSocket Disconnection
**What goes wrong:** Connection drops, UI shows stale "connected" state, no new findings
**Why it happens:** Only handling `onmessage`, not `onerror` or `onclose`
**How to avoid:** Handle all WebSocket events, show connection status to user, optionally implement reconnection
**Warning signs:** UI stops updating but no error shown, silent failures

### Pitfall 7: Invalid HTML Nesting Causing Hydration Errors
**What goes wrong:** Hydration errors from `<p>` wrapping `<div>`, `<ul>` outside `<li>`, etc.
**Why it happens:** Invalid HTML structure that browser auto-corrects differently than React expects
**How to avoid:** Validate HTML structure, use correct semantic nesting
**Warning signs:** Hydration errors in console, unexpected DOM structure in DevTools

</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources:

### Complete WebSocket Integration with FastAPI Backend
```typescript
// Source: Native WebSocket API + FastAPI patterns
// hooks/use-audit-websocket.ts
'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface Finding {
  id: string
  agent: 'numeric' | 'logic' | 'disclosure' | 'external'
  severity: 'critical' | 'warning' | 'pass'
  title: string
  description: string
}

interface AgentStatus {
  agent: string
  status: 'idle' | 'processing' | 'complete' | 'error'
}

export function useAuditWebSocket(auditId: string | null) {
  const ws = useRef<WebSocket | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [agentStatuses, setAgentStatuses] = useState<Record<string, AgentStatus>>({})
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')

  const connect = useCallback(() => {
    if (!auditId) return

    // Close existing connection
    if (ws.current) {
      ws.current.close()
    }

    setConnectionStatus('connecting')

    // Connect to FastAPI WebSocket
    const websocket = new WebSocket(`ws://localhost:8000/ws/audit/${auditId}`)

    websocket.onopen = () => {
      setConnectionStatus('connected')
      console.log('[WebSocket] Connected to audit', auditId)
    }

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // Handle different message types from FastAPI
        switch (data.type) {
          case 'finding':
            setFindings(prev => [...prev, data.payload])
            break

          case 'agent_status':
            setAgentStatuses(prev => ({
              ...prev,
              [data.payload.agent]: data.payload
            }))
            break

          case 'complete':
            console.log('[WebSocket] Analysis complete')
            break

          default:
            console.warn('[WebSocket] Unknown message type:', data.type)
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error)
      }
    }

    websocket.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
      setConnectionStatus('disconnected')
    }

    websocket.onclose = (event) => {
      console.log('[WebSocket] Closed:', event.code, event.reason)
      setConnectionStatus('disconnected')
    }

    ws.current = websocket
  }, [auditId])

  useEffect(() => {
    if (auditId) {
      connect()
    }

    // Cleanup on unmount or auditId change
    return () => {
      if (ws.current) {
        ws.current.close()
      }
    }
  }, [auditId, connect])

  return {
    findings,
    agentStatuses,
    connectionStatus,
    reconnect: connect
  }
}
```

### File Upload Component with Validation
```typescript
// Source: react-dropzone + zod validation pattern
// components/audit/file-upload-zone.tsx
'use client'

import { useDropzone } from 'react-dropzone'
import { z } from 'zod'
import { useState } from 'react'

const fileSchema = z.object({
  name: z.string().endsWith('.docx', 'Only .docx files are allowed'),
  size: z.number().max(10 * 1024 * 1024, 'File must be less than 10MB')
})

interface FileUploadZoneProps {
  label: string
  onUpload: (file: File) => Promise<void>
}

export function FileUploadZone({ label, onUpload }: FileUploadZoneProps) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    multiple: false,
    onDrop: async (acceptedFiles, rejectedFiles) => {
      setError(null)

      // Handle rejected files
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0]
        if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Only .docx files are allowed')
        } else if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File must be less than 10MB')
        } else {
          setError('File upload failed')
        }
        return
      }

      // Validate accepted file
      const uploadedFile = acceptedFiles[0]
      try {
        fileSchema.parse(uploadedFile)
        setFile(uploadedFile)

        // Upload file
        setUploading(true)
        await onUpload(uploadedFile)
        setUploading(false)
      } catch (err) {
        if (err instanceof z.ZodError) {
          setError(err.errors[0].message)
        } else {
          setError('Upload failed')
        }
        setUploading(false)
      }
    }
  })

  return (
    <div
      {...getRootProps()}
      className={`
        border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
        transition-colors
        ${isDragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-950' : 'border-slate-300 dark:border-slate-700'}
        ${error ? 'border-red-500' : ''}
        ${file ? 'border-green-500' : ''}
      `}
    >
      <input {...getInputProps()} />

      {uploading ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">Uploading...</p>
      ) : file ? (
        <div className="flex items-center justify-center gap-2">
          <span className="text-green-600">✓</span>
          <p className="text-sm font-medium">{file.name}</p>
        </div>
      ) : (
        <>
          <p className="text-sm font-semibold mb-1">{label}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {isDragActive ? 'Drop here...' : 'Drop .docx file here or click'}
          </p>
        </>
      )}

      {error && (
        <p className="text-xs text-red-600 mt-2">{error}</p>
      )}
    </div>
  )
}
```

### Agent Card with Real-Time Updates
```typescript
// Source: WebSocket + React state patterns
// components/audit/agent-card.tsx
'use client'

import { useMemo } from 'react'

interface AgentCardProps {
  agent: 'numeric' | 'logic' | 'disclosure' | 'external'
  status: 'idle' | 'processing' | 'complete' | 'error'
  findings: Finding[]
}

const AGENT_CONFIG = {
  numeric: { label: 'Numeric Validation', icon: 'calculate', color: 'blue' },
  logic: { label: 'Logic Consistency', icon: 'account_tree', color: 'purple' },
  disclosure: { label: 'Disclosure Compliance', icon: 'policy', color: 'orange' },
  external: { label: 'External Signals', icon: 'public', color: 'teal' }
}

export function AgentCard({ agent, status, findings }: AgentCardProps) {
  const config = AGENT_CONFIG[agent]

  const criticalCount = useMemo(
    () => findings.filter(f => f.severity === 'critical').length,
    [findings]
  )

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className={`material-icons-outlined text-${config.color}-500`}>
            {config.icon}
          </span>
          <span className="font-medium text-slate-700 dark:text-slate-200">
            {config.label}
          </span>
        </div>

        {status === 'complete' && criticalCount > 0 && (
          <span className="bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 text-xs px-2 py-0.5 rounded-full font-bold">
            {criticalCount} CRITICAL
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-4">
        {status === 'processing' && (
          <div className="flex flex-col items-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-slate-300 border-t-blue-600"></div>
            <p className="text-xs text-slate-400 mt-2 animate-pulse">
              Analyzing...
            </p>
          </div>
        )}

        {status === 'complete' && findings.length === 0 && (
          <div className="flex items-center gap-2 text-green-600">
            <span className="material-icons-outlined">check_circle</span>
            <p className="text-sm font-medium">No issues found</p>
          </div>
        )}

        {status === 'complete' && findings.length > 0 && (
          <div className="space-y-3">
            {findings.map((finding) => (
              <div
                key={finding.id}
                className={`
                  border-l-4 rounded-r p-3
                  ${finding.severity === 'critical' ? 'border-red-500 bg-red-50 dark:bg-red-950/20' : ''}
                  ${finding.severity === 'warning' ? 'border-amber-500 bg-amber-50 dark:bg-amber-950/20' : ''}
                  ${finding.severity === 'pass' ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : ''}
                `}
              >
                <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {finding.title}
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  {finding.description}
                </p>
              </div>
            ))}
          </div>
        )}

        {status === 'error' && (
          <p className="text-sm text-red-600">Processing failed</p>
        )}
      </div>
    </div>
  )
}
```

### CSV Export Function
```typescript
// Source: json2csv + browser download pattern
// lib/export.ts
import { parse } from 'json2csv'

export function exportFindingsToCSV(findings: Finding[], filename: string = 'audit-findings.csv') {
  try {
    // Convert findings to CSV
    const csv = parse(findings, {
      fields: ['agent', 'severity', 'title', 'description']
    })

    // Create blob
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })

    // Create download link
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    // Clean up
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export CSV:', error)
    throw new Error('Export failed')
  }
}

export function exportFindingsToJSON(findings: Finding[], filename: string = 'audit-findings.json') {
  try {
    const json = JSON.stringify(findings, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)

    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export JSON:', error)
    throw new Error('Export failed')
  }
}
```

</code_examples>

<sota_updates>
## State of the Art (2025-2026)

What's changed recently:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pages Router + getServerSideProps | App Router + Server Components | Next.js 13+ (2023) | Better streaming, parallel data fetching, automatic request deduplication |
| Client-side data fetching only | RSC for initial load + Client for interactive | 2024-2025 | Faster initial page loads, reduced client bundle |
| Custom WebSocket hooks without cleanup | WebSocket hooks with proper cleanup + reconnection | 2025 | Prevents memory leaks, better UX |
| Manual dark mode implementation | next-themes | 2023+ | No hydration flash, system preference detection |
| Custom file upload UI | react-dropzone | Established | Accessibility, validation, better DX |
| Socket.IO for all WebSocket | Native WebSocket for simple cases | 2025-2026 | Less complexity when not needed |

**New tools/patterns to consider:**
- **React useOptimistic hook**: Built-in optimistic updates (React 19+), simpler than custom state rollback
- **TanStack Query streamedQuery API**: Experimental feature for streaming data from Server Actions/SSE
- **Partial Prerendering (PPR)**: Next.js 15 experimental feature - static shell + dynamic content streaming
- **Zustand for WebSocket state**: Lightweight alternative to Context for sharing WebSocket connection across components

**Deprecated/outdated:**
- **Pages Router for new projects**: App Router is production-ready and recommended for all new projects
- **next-ws for external WebSocket servers**: Only useful for Next.js-hosted WebSocket servers, not for connecting to FastAPI
- **Class-based Error Boundaries**: Use functional components with error.tsx in App Router
- **getServerSideProps/getStaticProps**: Replaced by Server Components and async components

</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **WebSocket Reconnection Strategy**
   - What we know: Native WebSocket doesn't auto-reconnect, Socket.IO does but adds complexity
   - What's unclear: Best reconnection pattern for FastAPI WebSocket (exponential backoff? max retries?)
   - Recommendation: Start with simple manual reconnect button, add automatic reconnection in future iteration if needed

2. **Real-time Optimistic Updates vs Server Truth**
   - What we know: TanStack Query handles optimistic REST updates well
   - What's unclear: How to handle conflicts when WebSocket sends update that contradicts optimistic update
   - Recommendation: For v1, WebSocket is source of truth - no optimistic updates for findings, only for audit CRUD

3. **File Upload Progress Tracking**
   - What we know: FastAPI can stream upload progress, react-dropzone can show progress
   - What's unclear: Whether backend supports chunked upload progress events
   - Recommendation: Start without progress bar (files are small .docx), add progress in future if needed

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [Next.js Official Docs - Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- [Shadcn UI Dark Mode - Next.js](https://ui.shadcn.com/docs/dark-mode/next)
- [next-themes GitHub](https://github.com/pacocoursey/next-themes) - Official dark mode solution
- [FastAPI WebSockets Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [react-dropzone Documentation](https://react-dropzone.js.org/)

### Secondary (MEDIUM confidence - verified with official sources)
- [Next.js WebSocket Discussion #58698](https://github.com/vercel/next.js/discussions/58698) - Route Handlers don't support WebSocket upgrade
- [TanStack Query and WebSockets - LogRocket](https://blog.logrocket.com/tanstack-query-websockets-real-time-react-data-fetching/)
- [Using WebSockets with React Query - TkDodo's Blog](https://tkdodo.eu/blog/using-web-sockets-with-react-query)
- [Next.js Hydration Error Documentation](https://nextjs.org/docs/messages/react-hydration-error)
- [Socket.IO vs ws comparison](https://socket.io/how-to/use-with-nextjs) - Official Socket.IO docs

### Tertiary (LOW confidence - needs validation)
- None - all critical findings verified against official documentation

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Next.js 14 App Router, React 18
- Ecosystem: WebSocket clients, file upload, dark mode, state management
- Patterns: Server/Client component separation, real-time updates, optimistic UI
- Pitfalls: Hydration errors, WebSocket cleanup, deployment constraints

**Confidence breakdown:**
- Standard stack: HIGH - verified with official docs and community consensus
- Architecture: HIGH - from Next.js official docs and established patterns
- Pitfalls: HIGH - documented in official docs and recent tutorials
- Code examples: HIGH - adapted from official documentation and verified sources

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - Next.js ecosystem stable, monthly patch releases)

</metadata>

---

*Phase: 07-frontend-dashboard*
*Research completed: 2026-01-20*
*Ready for planning: yes*
