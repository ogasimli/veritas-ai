/**
 * Finding transformation - DATABASE FORMAT ONLY
 * All findings come from database, no raw agent format handling
 */

import type { Finding } from '@/lib/types'
import { mapSeverity } from './agent-mapping'

export interface DatabaseFinding {
    id: string
    category: string
    severity: string
    description: string
    reasoning: string | null
    source_refs: Array<Record<string, unknown>>
    agent_id: string
    created_at: string
}

/**
 * Transform database finding to frontend Finding type
 * Database schema: { id, category, severity, description, reasoning, source_refs, agent_id, created_at }
 */
export function transformDatabaseFinding(dbFinding: DatabaseFinding): Finding {
    return {
        id: dbFinding.id, // Use database UUID directly
        agent: dbFinding.category, // "numeric", "logic", "disclosure", "external"
        severity: mapSeverity(dbFinding.severity), // Map "high"→"critical", etc.
        title: dbFinding.description, // Backend stores summary in description
        description: dbFinding.reasoning || '', // Backend stores details in reasoning
        reasoning: dbFinding.reasoning
    }
}

/**
 * Validation helper
 */
export function validateFinding(finding: Finding): boolean {
    const issues: string[] = []

    if (!finding.id) issues.push('Missing id')
    if (!finding.agent) issues.push('Missing agent')
    if (!finding.title) issues.push('Missing title')
    if (finding.title?.includes('undefined')) issues.push('Title contains "undefined"')
    if (finding.description?.includes('undefined')) issues.push('Description contains "undefined"')

    if (issues.length > 0) {
        console.error('[VALIDATION] Finding validation failed:', issues, finding)
        return false
    }
    return true
}
