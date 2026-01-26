/**
 * Utilities for mapping between backend and frontend agent identifiers and severity levels
 */

/**
 * Maps backend agent_id to frontend agent keys
 */
export function mapAgentId(agentId: string): string {
    const mapping: Record<string, string> = {
        numeric_validation: 'numeric',
        logic_consistency: 'logic',
        disclosure_compliance: 'disclosure',
        external_signal: 'external',
    }
    return mapping[agentId] || agentId
}

/**
 * Maps backend severity levels to frontend severity levels
 */
export function mapSeverity(backendSeverity: string): 'critical' | 'warning' | 'pass' {
    if (backendSeverity === 'high') return 'critical'
    if (backendSeverity === 'medium' || backendSeverity === 'low') return 'warning'
    return 'warning'
}
