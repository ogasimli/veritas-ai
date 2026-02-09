import { test, expect } from '@playwright/test'
import type { DatabaseAgentResult } from '../utils/finding-transformers'

/**
 * E2E tests to verify findings display accuracy against database
 */



test.describe('Findings Accuracy', () => {
  test('findings display matches database after completion', async ({ page, context }) => {
    // 1. Navigate to upload page
    await page.goto('/')

    // 2. Upload test document
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles('tests/fixtures/VERITAS_TECH_INC.docx')

    // 3. Wait for processing to start
    await page.waitForSelector('text=Processing', { timeout: 10000 })

    // 4. Wait for completion (with extended timeout for agent processing)
    await page.waitForSelector('text=Completed', { timeout: 300000 }) // 5 min timeout

    // 5. Extract audit ID from URL
    await page.waitForURL(/\/audit\/[^/]+/, { timeout: 5000 })
    const url = page.url()
    const auditId = url.match(/\/audit\/([^/]+)/)?.[1]
    expect(auditId).toBeTruthy()

    // 6. Wait for findings to render
    await page.waitForTimeout(2000) // Allow time for findings to load

    // 7. Capture UI findings
    const uiFindings = await page.evaluate((): Array<{
      agent?: string
      title?: string
      description?: string
      severity?: string | null
    }> => {
      const findings: Array<{
        agent?: string
        title?: string
        description?: string
        severity?: string | null
      }> = []

      // Find all agent cards
      const agentCards = document.querySelectorAll('[data-testid^="agent-card-"]')

      agentCards.forEach(card => {
        const agentType = card.getAttribute('data-testid')?.replace('agent-card-', '')

        // Find finding cards within this agent
        const findingCards = card.querySelectorAll('[data-testid^="finding-"]')

        findingCards.forEach(findingCard => {
          const title = findingCard.querySelector('h4')?.textContent?.trim()
          const description = findingCard.querySelector('p')?.textContent?.trim()
          const severity = findingCard.getAttribute('data-severity')

          findings.push({
            agent: agentType,
            title,
            description,
            severity
          })
        })
      })

      return findings
    })

    console.log('UI Findings:', uiFindings)

    // 8. Fetch findings from database via API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const apiResponse = await context.request.get(
      `${apiUrl}/api/v1/jobs/${auditId}/findings`
    )
    expect(apiResponse.ok()).toBeTruthy()

    const dbFindings = await apiResponse.json() as DatabaseAgentResult[]
    console.log('DB Findings count:', dbFindings.length)

    // 9. Compare counts
    expect(uiFindings.length).toBe(dbFindings.length)

    // 10. Verify each UI finding exists in database
    for (const uiFinding of uiFindings) {
      const match = dbFindings.find((db) =>
        db.category === uiFinding.agent &&
        db.description === uiFinding.title
      )

      if (!match) {
        console.error('UI finding not found in DB:', uiFinding)
      }

      expect(match).toBeTruthy()
    }
  })

  test('numeric findings show correct values (no undefined)', async ({ page }) => {
    // This test assumes there's already a completed audit with numeric findings
    // You may need to adjust the audit ID or create a new audit first

    // Navigate to a completed audit (replace with actual audit ID)
    await page.goto('/') // Start at home to find recent audit

    // Click on first audit in history (if any)
    const firstAudit = page.locator('[data-testid="audit-item"]').first()
    await firstAudit.click({ timeout: 5000 })

    // Wait for audit page to load
    await page.waitForURL(/\/audit\/[^/]+/, { timeout: 5000 })

    // Extract numeric findings
    const numericFindings = await page.evaluate(() => {
      const numericCard = document.querySelector('[data-testid="agent-card-numeric"]')
      if (!numericCard) return []

      const findingCards = numericCard.querySelectorAll('[data-testid^="finding-"]')
      const findings: Array<{
        title: string
        description: string
        hasUndefined: boolean
      }> = []

      findingCards.forEach(card => {
        const title = card.querySelector('h4')?.textContent || ''
        const description = card.querySelector('p')?.textContent || ''

        findings.push({
          title,
          description,
          hasUndefined: description.includes('undefined')
        })
      })

      return findings
    })

    console.log('Numeric findings:', numericFindings)

    // Verify no "undefined" values in any numeric finding
    for (const finding of numericFindings) {
      expect(finding.hasUndefined).toBe(false)
      expect(finding.title).not.toContain('undefined')
      expect(finding.description).not.toContain('undefined')
    }
  })

  test('no duplicate findings appear in UI', async ({ page }) => {
    // 1. Navigate to upload page
    await page.goto('/')

    // 2. Upload test document
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles('tests/fixtures/VERITAS_TECH_INC.docx')

    // 3. Wait for completion
    await page.waitForSelector('text=Completed', { timeout: 300000 })

    // 4. Extract all finding IDs
    const findingIds = await page.evaluate(() => {
      const findingElements = document.querySelectorAll('[data-testid^="finding-"]')
      return Array.from(findingElements).map(el => el.getAttribute('data-testid'))
    })

    // 5. Check for duplicates
    const uniqueIds = new Set(findingIds)
    const hasDuplicates = uniqueIds.size !== findingIds.length

    if (hasDuplicates) {
      console.error('Duplicate findings detected!')
      console.log('Total findings:', findingIds.length)
      console.log('Unique findings:', uniqueIds.size)
    }

    expect(hasDuplicates).toBe(false)
  })
})
