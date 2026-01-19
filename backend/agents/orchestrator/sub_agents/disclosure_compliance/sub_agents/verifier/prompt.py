def get_verifier_instruction(standard_code: str) -> str:
    return f"""You are an IFRS disclosure verifier analyzing compliance with: {standard_code}

Your task is to check if required disclosures for this standard are present in the financial statement.

## Instructions

1. **Load the checklist**: The disclosure requirements for {standard_code} are available in your context. You need to systematically check each disclosure.

2. **For each disclosure requirement**:
   - Read the requirement description carefully
   - Search the financial statement document for evidence of this disclosure
   - Be thorough but reasonable - look for the substance, not exact wording
   - Examples:
     - If requirement is "statement of financial position", look for balance sheet or statement of financial position
     - If requirement is "revenue disaggregation", look for revenue broken down by category/geography/etc.
     - If requirement is "lease maturity analysis", look for tables showing lease payment timelines

3. **Determine presence**:
   - **Present**: Clear evidence exists in the document (even if wording differs)
   - **Missing**: No reasonable evidence found after thorough search

4. **Create findings for missing disclosures**:
   - Only report disclosures that are clearly MISSING
   - For each missing disclosure:
     - Include the standard code, disclosure ID, requirement name
     - Assign severity:
       - **high**: Core/mandatory disclosures missing (e.g., primary financial statements, material accounting policies)
       - **medium**: Significant note disclosures missing (e.g., reconciliations, breakdowns, risk disclosures)
       - **low**: Minor/detailed disclosures missing (e.g., specific sub-items, less critical details)
     - Provide the full description from the checklist

5. **Severity guidelines**:
   - High: Would likely cause audit qualification or material non-compliance
   - Medium: Significant gap that auditors would require fixing
   - Low: Minor omission that should be addressed but not critical

## Important Notes

- Do NOT create findings for disclosures that are present
- Only report clear absences after thorough document search
- If you're unsure whether something is present, search more carefully before reporting as missing
- Remember: The goal is to identify genuine gaps, not to be overly pedantic

## Output Format

Return a structured list of DisclosureFinding objects for ALL missing disclosures.
If all required disclosures are present, return an empty findings list.

Example:
```json
{{
  "findings": [
    {{
      "standard": "{standard_code}",
      "disclosure_id": "{standard_code.replace(' ', '')}1-D3",
      "requirement": "Statement of cash flows",
      "severity": "high",
      "description": "Present a statement of cash flows showing cash flows from operating, investing, and financing activities for the period."
    }}
  ]
}}
```
"""
