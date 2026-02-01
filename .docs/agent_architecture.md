# Veritas AI Agent Architecture

This document describes the architecture of the Veritas AI agent system, including the agent hierarchy, data flow, and key naming conventions.

## Overview

The system is orchestrated by a root `AuditOrchestrator` agent which runs four parallel validation pipelines:
1. **Logic Consistency**: Detects semantic contradictions.
2. **Disclosure Compliance**: Validates IFRS/IAS disclosure requirements.
3. **Numeric Validation**: Verifies calculations and cross-checks numbers (includes Legacy and In-Table pipelines).
4. **External Signal**: Verifies claims against external sources (Internet Search).

## pipelines and Agents

### 1. Logic Consistency Pipeline (`LogicConsistency`)

Detects logical inconsistencies within the financial statement text.

- **Detector** (`LogicConsistencyDetector`)
  - **Input**: Extracted text
  - **Output Key**: `logic_consistency_detector_output`
  - **Schema**: `LogicConsistencyDetectorOutput`
  - **Function**: Identifies potential contradictions.

- **Reviewer** (`LogicConsistencyReviewer`)
  - **Input**: `logic_consistency_detector_output`
  - **Output Key**: `logic_consistency_reviewer_output`
  - **Schema**: `LogicConsistencyReviewerOutput`
  - **Function**: Filters false positives and assigns severity.

### 2. Disclosure Compliance Pipeline (`DisclosureCompliance`)

Validates compliance with IFRS standards.

- **Scanner** (`DisclosureScanner`)
  - **Input**: Extracted text
  - **Output Key**: `disclosure_scanner_output`
  - **Schema**: `DisclosureScannerOutput`
  - **Function**: Identifies applicable IFRS/IAS standards.

- **Verifier** (`DisclosureVerifier`)
  - **Input**: `disclosure_scanner_output`
  - **Output Key**: Dynamic `disclosure_findings:{standard}` (aggregated to `disclosure_all_findings`)
  - **Schema**: `DisclosureVerifierOutput`
  - **Function**: Parallel agents verify disclosures for each standard.

- **Reviewer** (`DisclosureReviewer`)
  - **Input**: `disclosure_all_findings`
  - **Output Key**: `disclosure_reviewer_output`
  - **Schema**: `DisclosureReviewerOutput`
  - **Function**: Filters false positives.

### 3. Numeric Validation Pipeline (`NumericValidation`)

Runs two sub-pipelines in parallel.

#### A. Legacy Numeric Validation (`LegacyNumericValidation`)

Checks cross-references and internal consistency using FSLI extraction.

- **Extractor** (`LegacyNumericFsliExtractor`)
  - **Input**: Extracted text
  - **Output Key**: `legacy_numeric_fsli_extractor_output`
  - **Schema**: `LegacyNumericFsliExtractorOutput`
  - **Function**: Extracts Financial Statement Line Items (FSLIs).

- **Verifier** (`LegacyNumericVerifier`)
  - **Input**: `legacy_numeric_fsli_extractor_output`
  - **Output Key**: Dynamic `legacy_numeric_checks:{fsli}` (aggregated to `legacy_numeric_all_checks`)
  - **Schema**: `LegacyNumericVerifierOutput`
  - **Function**: Parallel agents verify calculations for each FSLI.

- **Reviewer** (`LegacyNumericIssueReviewer`)
  - **Input**: `legacy_numeric_all_checks`
  - **Output Key**: `legacy_numeric_issue_reviewer_output`
  - **Schema**: `LegacyNumericReviewerOutput`
  - **Function**: Reviews discrepancies and filters noise.

#### B. In-Table Verification (`InTableVerification`)

Verifies mathematical accuracy of tables.

- **Table Extractor** (`TableExtractor`)
  - **Output Key**: `table_extractor_output`
  - **Schema**: `TableExtractorOutput`
  - **Callback**: `resolve_and_verify_formulas` (sets `table_calc_issues`)
  - **Function**: Extracts tables and performs deterministic formula checks.

- **Aggregator** (`InTableIssueAggregator`)
  - **Input**: `table_calc_issues`
  - **Output Key**: `in_table_issue_aggregator_output`
  - **Schema**: `InTableIssueAggregatorOutput`
  - **Function**: Summarizes and prioritizes calculation issues.

### 4. External Signal Pipeline (`ExternalSignal`)

Verifies information against external sources.

- **Verification** (`ExternalSignalVerification`) - Parallel
  - **Internet To Report** (`ExternalSignalInternetToReport`)
    - **Output Key**: `external_signal_internet_to_report_output`
    - **Schema**: `ExternalSignalInternetToReportOutput`
    - **Function**: Searches for external risks (news, litigation).
  - **Report To Internet** (`ExternalSignalReportToInternet`)
    - **Output Key**: `external_signal_report_to_internet_output`
    - **Schema**: `ExternalSignalReportToInternetOutput`
    - **Function**: Verifies specific claims from the report.

- **Aggregator** (`ExternalSignalFindingsAggregator`)
  - **Input**: Both external outputs
  - **Output Key**: `external_signal_findings_aggregator_output`
  - **Schema**: `ExternalSignalFindingsAggregatorOutput`
  - **Function**: Dedupes and unifies findings.

## Data Flow & State Structure

The session state is a shared dictionary. To prevent conflicts, strict naming conventions are enforced:

- **Pipeline Prefix**: All keys are prefixed with the pipeline name (e.g., `logic_consistency_...`).
- **Dynamic Namespacing**: Parallel workers use dynamic keys (e.g., `:{standard}`) which are aggregated before the next stage.

### Final Output Keys (Consumed by Backend)

- `logic_consistency_reviewer_output`
- `disclosure_reviewer_output`
- `legacy_numeric_issue_reviewer_output`
- `in_table_issue_aggregator_output`
- `external_signal_findings_aggregator_output`