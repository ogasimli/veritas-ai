/**
 * Unit test to verify transformDatabaseResult works correctly
 * Converted to Playwright test format (no Jest/Vitest runner available)
 */

import { test, expect } from '@playwright/test'
import { transformDatabaseResult } from '../utils/finding-transformers'
import type { DatabaseAgentResult } from '../utils/finding-transformers'

test.describe('Database Finding Transformer', () => {
  test('transforms numeric finding correctly', () => {
    const dbResult: DatabaseAgentResult = {
      id: 'a1b2c3d4-5678-90ab-cdef-1234567890ab',
      category: 'numeric',
      severity: 'high',
      description: 'Revenue discrepancy detected',
      reasoning: 'Expected: 1000000, Actual: 950000, Discrepancy: 50000',
      source_refs: [{ page: 10, section: 'Income Statement' }],
      agent_id: 'numeric_validation',
      error: null,
      raw_data: {},
      created_at: '2026-01-26T10:00:00Z'
    }

    const result = transformDatabaseResult(dbResult)

    expect(result.id).toBe('a1b2c3d4-5678-90ab-cdef-1234567890ab')
    expect(result.agent).toBe('numeric')
    expect(result.severity).toBe('critical') // 'high' maps to 'critical'
    expect(result.title).toBe('Revenue discrepancy detected')
    expect(result.description).toBe('Expected: 1000000, Actual: 950000, Discrepancy: 50000')
    expect(result.reasoning).toBe('Expected: 1000000, Actual: 950000, Discrepancy: 50000')
  })

  test('transforms logic finding correctly', () => {
    const dbResult: DatabaseAgentResult = {
      id: 'b2c3d4e5-6789-01bc-def0-234567890abc',
      category: 'logic',
      severity: 'medium',
      description: 'Inconsistent profit margin claims',
      reasoning: 'Claim: Profit margin increased by 5%\n\nReasoning: Financial data shows decrease',
      source_refs: [],
      agent_id: 'logic_consistency',
      error: null,
      raw_data: {},
      created_at: '2026-01-26T10:01:00Z'
    }

    const result = transformDatabaseResult(dbResult)

    expect(result.id).toBe('b2c3d4e5-6789-01bc-def0-234567890abc')
    expect(result.agent).toBe('logic')
    expect(result.severity).toBe('warning') // 'medium' maps to 'warning'
    expect(result.title).toBe('Inconsistent profit margin claims')
    expect(result.description).toContain('Claim:')
  })

  test('transforms disclosure finding correctly', () => {
    const dbResult: DatabaseAgentResult = {
      id: 'c3d4e5f6-7890-12cd-ef01-34567890abcd',
      category: 'disclosure',
      severity: 'high',
      description: 'Missing statement of cash flows',
      reasoning: 'Standard: IAS 1\nID: IAS1-D6\n\nRequirement Detail: A statement of cash flows for the period is missing.',
      source_refs: [],
      agent_id: 'disclosure_compliance',
      error: null,
      raw_data: {},
      created_at: '2026-01-26T10:02:00Z'
    }

    const result = transformDatabaseResult(dbResult)

    expect(result.id).toBe('c3d4e5f6-7890-12cd-ef01-34567890abcd')
    expect(result.agent).toBe('disclosure')
    expect(result.title).toBe('Missing statement of cash flows')
    expect(result.description).toContain('Standard: IAS 1')
  })

  test('handles empty reasoning gracefully', () => {
    const dbResult: DatabaseAgentResult = {
      id: 'd4e5f6g7-8901-23de-f012-4567890abcde',
      category: 'external',
      severity: 'low',
      description: 'External signal detected',
      reasoning: null,
      source_refs: [],
      agent_id: 'external_signal',
      error: null,
      raw_data: {},
      created_at: '2026-01-26T10:03:00Z'
    }

    const result = transformDatabaseResult(dbResult)

    expect(result.description).toBeUndefined() // null reasoning becomes undefined
    expect(result.reasoning).toBeUndefined()
  })

  test('does not produce "undefined" strings', () => {
    const dbResult: DatabaseAgentResult = {
      id: 'e5f6g7h8-9012-34ef-0123-567890abcdef',
      category: 'numeric',
      severity: 'high',
      description: '',
      reasoning: 'Expected: None, Actual: None, Discrepancy: None',
      source_refs: [],
      agent_id: 'numeric_validation',
      error: null,
      raw_data: {},
      created_at: '2026-01-26T10:04:00Z'
    }

    const result = transformDatabaseResult(dbResult)

    // Should NOT contain the string "undefined"
    expect(result.title || '').not.toContain('undefined')
    expect(result.description || '').not.toContain('undefined')
    expect(JSON.stringify(result)).not.toContain('"undefined"')
  })
})
