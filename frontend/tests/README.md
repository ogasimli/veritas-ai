# E2E Tests for Findings Accuracy

## Setup

1. Install Playwright:
```bash
npm install
npx playwright install chromium
```

2. Create test fixtures directory and add test document:
```bash
mkdir -p tests/fixtures
# Place a test financial report (DOCX) in tests/fixtures/test-report.docx
```

## Running Tests

```bash
# Run all tests
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run in debug mode
npm run test:e2e:debug

# Run specific test file
npx playwright test findings-accuracy.spec.ts

# Run specific test
npx playwright test -g "findings display matches database"
```

## Test Coverage

### 1. Findings Display Matches Database
- Uploads document and waits for completion
- Extracts findings from UI
- Fetches findings from database via API
- Compares counts and content
- Ensures no findings are missing

### 2. No Undefined Values
- Checks numeric findings for "undefined" strings
- Verifies all fields are populated correctly
- Ensures transformation is working properly

### 3. No Duplicates
- Extracts all finding IDs from UI
- Checks for duplicate IDs
- Ensures deduplication logic is working

## Test Fixtures

You'll need to provide test documents in the `tests/fixtures/` directory:

- `test-report.docx` - A sample financial report for testing

The test document should contain:
- Numeric data (for numeric validation agent)
- Narrative text (for logic consistency agent)
- Disclosure statements (for disclosure compliance agent)
- Company/financial data (for external signal agent)

## CI/CD Integration

To run tests in CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: npm ci
  working-directory: ./frontend

- name: Install Playwright browsers
  run: npx playwright install --with-deps chromium
  working-directory: ./frontend

- name: Run E2E tests
  run: npm run test:e2e
  working-directory: ./frontend
  env:
    NEXT_PUBLIC_API_URL: http://localhost:8000

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: frontend/playwright-report/
```

## Debugging Tests

If tests fail:

1. **Check test output:**
   ```bash
   npx playwright test --reporter=list
   ```

2. **View HTML report:**
   ```bash
   npx playwright show-report
   ```

3. **Run in headed mode:**
   ```bash
   npx playwright test --headed
   ```

4. **Use trace viewer:**
   ```bash
   npx playwright show-trace trace.zip
   ```

## Test Data Requirements

For the tests to work, ensure:

1. Backend is running on `http://localhost:8000`
2. Frontend is running on `http://localhost:3000`
3. Database is accessible and migrations are run
4. Test fixtures are in place
5. Agent pipeline is configured correctly

## Known Limitations

- Tests require actual document processing (takes 3-5 minutes)
- Tests depend on agent pipeline completing successfully
- Network timeouts may occur if backend is slow
- Tests assume specific UI structure (data-testid attributes)

## Future Improvements

- [ ] Add more test fixtures with different content types
- [ ] Mock backend responses for faster tests
- [ ] Add visual regression tests
- [ ] Test error scenarios (failed agents, network errors)
- [ ] Add performance benchmarks
