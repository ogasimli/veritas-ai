# Phase 7: Frontend Dashboard - Context

**Gathered:** 2026-01-20
**Status:** Ready for planning

<vision>
## How This Should Work

A single-page, real-time dashboard experience where auditors upload financial documents and watch the analysis happen live. Everything happens on one page with smooth inline transformations - no jarring page navigations.

**The flow:**
1. **Empty state**: Clean landing with "Create Report" button
2. **Upload**: Three labeled upload zones (Current Year, Prior Year, Internal Memos) - drag & drop .docx files
3. **Start processing**: Click "Start Review" → page transforms in place:
   - Upload cards shrink into compact "Data Sources" chips at the top
   - Start button disappears
   - Four agent cards appear with animated spinners
4. **Live updates**: As each agent (Numeric, Logic, Disclosure, External) analyzes the document, findings appear in real-time within their respective cards
5. **Completion**: Spinners are replaced with actual findings - no navigation, just seamless transformation

**The sidebar:**
- "New Audit" button at top
- Flat list of all audits (current + past) - click any audit to view its results
- Dark mode toggle (bottom right floating button)
- Static user placeholder (no auth)

**The feel:**
Professional audit tool that feels calm and organized. Real-time updates should feel informative, not overwhelming. Dark mode support is essential - this matches how the mockup looks and feels.

</vision>

<essential>
## What Must Be Nailed

- **Real-time WebSocket experience** - Findings must appear live as agents produce them. The transformation from "processing" to "showing results" happens gradually, not all at once
- **Inline transformation workflow** - Upload → Processing → Results all happen on the same page. No page navigation. The UI morphs in place
- **Full audit CRUD** - Users can create new audits, see all past audits in sidebar, and click to view any previous audit's results
- **Strict file validation** - Only accept .docx files. Show immediate error feedback if user tries to upload wrong file type
- **Dark mode** - Full implementation with toggle, not just system preference

</essential>

<boundaries>
## What's Out of Scope

**Explicitly NOT in Phase 7:**
- Multi-user features / authentication / permissions (single-user app)
- Advanced filtering (severity filters, saved views, custom sorting)
- Editing findings (no dismiss, annotate, or modify - findings are read-only)
- PDF/Excel export with formatting (basic JSON/CSV export only)
- Audit Score Analysis card (the "78 score" card with Overall Risk - removed from scope)
- Drill-down modal/expansion when clicking findings
- Smart error handling / retry logic (keep errors simple - just show "Processing failed")
- Settings / Logout buttons (no auth, so no need)
- "Import Data" button on home page (only "Create Report")
- Subsection headers in sidebar ("Current Session" / "History" - just one flat list)

**File support:**
- .docx only (no PDF, Excel, CSV uploads as documents)

**Progress tracking:**
- Indefinite progress indicators (spinners/animated bars, not percentages) - we don't have reliable progress calculation

</boundaries>

<specifics>
## Specific Ideas

**Architecture:**
- Next.js 14 App Router (already in tech stack)
- Server components for layout, sidebar, initial data fetching
- Client components ('use client') for file upload, WebSocket, real-time agent cards
- FastAPI backend provides REST endpoints (audit CRUD) + WebSocket for live updates

**4 Key Screens:**
1. **Home** - Landing page with "Create Report" button
2. **Upload/Processing/Results** - Single page that transforms through 3 states
3. **Past Audit View** - Click audit from sidebar to view its completed results
4. _(No separate processing/results pages - it's all one page)_

**Real-time behavior:**
- Use WebSocket connection to backend
- Four agent cards: Numeric Validation, Logic Consistency, Disclosure Compliance, External Signals
- Each agent card starts with indeterminate spinner
- As agent produces findings, they appear in the card immediately
- When agent completes, spinner disappears, only findings remain
- If agent fails, show simple error message in that card

**File upload:**
- Strict validation: only .docx files accepted
- Show error immediately if wrong file type dropped
- Visual feedback: green checkmark when valid file uploaded
- Three slots: Current Year (required), Prior Year (optional), Internal Memos (optional)

**Export:**
- "Export Full Report" button on results
- Simple JSON or CSV download of all findings
- No fancy PDF formatting

**Visual design:**
- Use complete HTML/React mockup provided: `/Users/orkhan/Downloads/code.html`
- Custom logo: `/Users/orkhan/Desktop/logos/favicon.png` (sidebar top left)
- Favicon: `/Users/orkhan/Desktop/logos/favicon-16x16.png`
- Dark mode toggle: floating button bottom right
- Color scheme from mockup: primary #1b4f6f, Tailwind + Material Icons
- Static user placeholder in sidebar: hardcoded "JD" / "Jane Doe" (no auth)

**Findings presentation:**
- Organized by agent category (4 cards: Numeric, Logic, Disclosure, External)
- Each finding shows: severity badge, title, description
- Severity levels: Critical (red), Warning (amber), Compliant/Pass (green)
- No drill-down interaction - findings are read-only text

**Audit list:**
- Sidebar shows all audits in one flat list
- Current audit highlighted
- Click any audit to view its results
- "New Audit" button creates new audit and navigates to upload page

</specifics>

<notes>
## Additional Context

**Design Reference:**
Complete React mockup provided at `/Users/orkhan/Downloads/code.html` shows all screens and interactions. This mockup uses React Router for navigation, but we'll adapt to Next.js App Router while keeping the same visual design and UX.

**Key simplifications from original mockup:**
- Removed "Import Data" button (only "Create Report")
- Removed Settings/Logout buttons
- Removed "Current Session" / "History" sidebar subsections (flat list)
- Removed Audit Score Analysis card with overall risk score
- Changed from percentage-based progress bars to indefinite spinners

**WebSocket integration:**
- Backend sends real-time updates as agents produce findings
- Frontend adds findings to UI immediately as they arrive
- Keep error handling simple for v1 - if WebSocket fails, show basic error

**Tech constraints:**
- Must work with existing FastAPI backend
- Must integrate with 4 existing agents (already built in Phases 3-6)
- Must use existing database schema for audits/findings

</notes>

---

*Phase: 07-frontend-dashboard*
*Context gathered: 2026-01-20*
