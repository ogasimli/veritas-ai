# UAT Issues: Phase 8 Plan 1

**Tested:** 2026-01-24
**Source:** .planning/phases/08-backend-websocket-support/8-01-SUMMARY.md
**Tester:** User via /gsd:verify-work

## Open Issues

[None - all issues resolved]

## Resolved Issues

### UAT-001: Frontend API integration not implemented

**Discovered:** 2026-01-24
**Phase/Plan:** 08-01
**Severity:** Blocker
**Feature:** Complete audit processing flow with WebSocket updates
**Description:** Frontend API functions (`createAudit`, `uploadFile`, `startProcessing`) are mock implementations that only log to console. No actual HTTP requests are made to backend, preventing end-to-end testing of WebSocket functionality. When "Start Review" is clicked, the UI shows WebSocket connection and agent cards, but no actual processing occurs because the backend never receives the audit creation request, file upload, or processing trigger.
**Expected:**
1. Frontend makes POST request to backend to create audit record in database
2. Frontend uploads .docx file to backend via multipart/form-data
3. Frontend triggers processing via API call to backend
4. Backend processes document with agents and streams updates via WebSocket
5. Agent cards update in real-time from "Waiting to start..." → "Running..." → "Complete" with findings

**Actual:**
1. Frontend only logs mock messages to browser console
2. No HTTP requests sent to backend (verified via network inspection)
3. Backend WebSocket connected but idle - no messages sent
4. All 4 agent cards permanently stuck on "Waiting to start..."
5. No agent execution occurs

**Repro:**
1. Start backend and frontend (`make dev`)
2. Navigate to http://localhost:3000/audit/new
3. Upload a .docx file
4. Click "Start Review" button
5. Open browser DevTools Network tab
6. Observe: no HTTP requests to `localhost:8000` (only WebSocket connection)
7. Observe: agents stuck on "Waiting to start..." indefinitely

**Code locations:**
- `frontend/lib/api.ts:20-26` - `createAudit()` returns random ID, no API call
- `frontend/lib/api.ts:28-41` - `uploadFile()` only logs to console
- `frontend/lib/api.ts:43-49` - `startProcessing()` only logs to console
- `frontend/app/(dashboard)/audit/new/page.tsx:42-45` - TODO comment indicating file upload not implemented

**Technical context:**
The Phase 8 WebSocket backend implementation is technically correct (endpoint registered, ConnectionManager works, message schemas defined, processor integration exists). The issue is that Phase 7 (Frontend Dashboard) was built with placeholder API functions that were never replaced with real implementations, creating a gap between frontend and backend.

**Resolved:** 2026-01-24 - Fixed in 8-01-FIX.md
**Commits:** 4cbe0b6, 1e94652, f00989c
**Summary:** Implemented real API integration with fetch() POST to /documents/upload, removed mock createAudit/startProcessing functions, added NEXT_PUBLIC_API_URL environment variable. Frontend now makes real HTTP calls to backend, receives job.id, and connects WebSocket for real-time updates.

---

*Phase: 08-backend-websocket-support*
*Plan: 01*
*Tested: 2026-01-24*
