import type { AgentResult } from '@/lib/types'
import { mapSeverity } from './agent-mapping'

export interface DatabaseAgentResult {
    id: string
    category: string
    agent_id: string
    // Success fields (nullable)
    severity: string | null
    description: string | null
    reasoning: string | null
    source_refs: Array<Record<string, unknown>> | null
    // Error fields (nullable)
    error: string | null
    // Common
    raw_data: Record<string, unknown>
    created_at: string
}

/**
 * Transform database result to frontend AgentResult type
 */
export function transformDatabaseResult(dbResult: DatabaseAgentResult): AgentResult {
    return {
        id: dbResult.id,
        agent: dbResult.category, // "numeric", "logic", "disclosure", "external"
        severity: dbResult.severity ? mapSeverity(dbResult.severity) : undefined,
        title: dbResult.description || undefined, // Backend stores summary in description
        description: dbResult.reasoning || undefined, // Backend stores details in reasoning
        reasoning: dbResult.reasoning || undefined,
        error: dbResult.error || undefined,
        raw_data: dbResult.raw_data
    }
}

/**
 * Validation helper
 */
export function validateAgentResult(result: AgentResult): boolean {
    const issues: string[] = []

    if (!result.id) issues.push('Missing id')
    if (!result.agent) issues.push('Missing agent')

    // For successful results, we expect title
    if (!result.error && !result.title) issues.push('Missing title for successful result')

    if (result.title?.includes('undefined')) issues.push('Title contains "undefined"')
    if (result.description?.includes('undefined')) issues.push('Description contains "undefined"')

    if (issues.length > 0) {
        console.error('[VALIDATION] AgentResult validation failed:', issues, result)
        return false
    }
    return true
}
