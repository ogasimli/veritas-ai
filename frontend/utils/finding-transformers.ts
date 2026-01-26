/**
 * Finding transformation utilities for converting backend agent findings to frontend Finding type
 */

import type { Finding } from '@/lib/types'
import { mapAgentId, mapSeverity } from './agent-mapping'

// TODO: Consolidate backend agent schemas to return a uniform data type for findings.
// This will allow us to remove 'any' and use a strict union or base type.
/* eslint-disable @typescript-eslint/no-explicit-any */

/**
 * Transforms numeric validation agent findings
 */
function transformNumericFinding(f: any, agentKey: string, index: number): Finding {
    return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: mapSeverity(f.severity || 'medium'),
        title: f.summary || `${f.fsli_name}: Numeric discrepancy`,
        description: `Expected: ${f.expected_value}, Actual: ${f.actual_value}, Discrepancy: ${f.discrepancy}`,
        reasoning: f.reasoning
    }
}

/**
 * Transforms logic consistency agent findings
 */
function transformLogicFinding(f: any, agentKey: string, index: number): Finding {
    return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: mapSeverity(f.severity || 'medium'),
        title: f.contradiction || 'Logic inconsistency',
        description: `Claim: ${f.claim || ''}. ${f.reasoning || ''}`,
        reasoning: f.reasoning
    }
}

/**
 * Transforms disclosure compliance agent findings
 */
function transformDisclosureFinding(f: any, agentKey: string, index: number): Finding {
    return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: mapSeverity(f.severity || 'medium'),
        title: `${f.standard || ''} - ${f.requirement || 'Missing disclosure'}`,
        description: f.description || '',
        reasoning: f.reasoning
    }
}

/**
 * Transforms external signal agent findings (handles both Internet-to-Report and Report-to-Internet)
 */
function transformExternalFinding(f: any, agentKey: string, index: number): Finding {
    // Report-to-Internet verification
    if (f.claim && f.status) {
        return {
            id: `${agentKey}-${index}-${Date.now()}`,
            agent: agentKey,
            severity: f.status === 'CONTRADICTED' ? 'critical' : f.status === 'VERIFIED' ? 'pass' : 'warning',
            title: `${f.status}: ${f.claim}`,
            description: `${f.evidence_summary || ''}${f.discrepancy ? ' | Discrepancy: ' + f.discrepancy : ''}`,
            reasoning: f.reasoning
        }
    }

    // Internet-to-Report finding
    return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: f.signal_type === 'financial_distress' || f.signal_type === 'litigation' ? 'critical' : 'warning',
        title: `${f.signal_type || 'External signal'}: ${f.summary || ''}`,
        description: `${f.potential_contradiction || ''}${f.publication_date ? ' (Published: ' + f.publication_date + ')' : ''}`,
        reasoning: f.reasoning
    }
}

/**
 * Fallback transformer for unknown agent types
 */
function transformGenericFinding(f: any, agentKey: string, index: number): Finding {
    return {
        id: `${agentKey}-${index}-${Date.now()}`,
        agent: agentKey,
        severity: 'warning' as const,
        title: f.title || f.summary || f.requirement || f.claim || 'Finding',
        description: f.description || f.reasoning || f.evidence_summary || '',
        reasoning: f.reasoning
    }
}

/**
 * Main transformer that routes to appropriate agent-specific transformer
 */
export function transformFinding(f: any, agentId: string, index: number): Finding {
    const agentKey = mapAgentId(agentId)

    switch (agentKey) {
        case 'numeric':
            return transformNumericFinding(f, agentKey, index)
        case 'logic':
            return transformLogicFinding(f, agentKey, index)
        case 'disclosure':
            return transformDisclosureFinding(f, agentKey, index)
        case 'external':
            return transformExternalFinding(f, agentKey, index)
        default:
            return transformGenericFinding(f, agentKey, index)
    }
}

/* eslint-enable @typescript-eslint/no-explicit-any */
