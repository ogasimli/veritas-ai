# Phase 8: Backend WebSocket Support - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<vision>
## How This Should Work

WebSocket enables real-time streaming of audit progress from backend to frontend. As the four validation agents (numeric, logic, disclosure, external) run in parallel, the WebSocket streams updates to keep users engaged during what can be lengthy analysis.

The UI has sections for each agent type. As each agent completes its work, that section fills with results progressively - users don't wait for all agents to finish before seeing anything. This progressive reveal keeps users engaged and shows the system is actively working.

The main reason for WebSocket isn't just status updates ("agent started", "agent completed") - it's to show each agent's results immediately when that agent finishes, not waiting for the entire audit to complete.

</vision>

<essential>
## What Must Be Nailed

- **User engagement during long waits** - The analysis can take minutes. Updates must give users confidence the system is working and show meaningful progress. This is fundamentally about UX during wait time, not just technical plumbing.
- **Clean integration with existing agent flow** - WebSocket shouldn't require major refactoring of the agent execution code. It should plug into the existing orchestrator cleanly.
- **Clear data contract** - Define the message format for agent → backend → frontend communication. What does an agent result look like when it comes through the WebSocket? What status updates are sent? The contract must be useful and clean.

</essential>

<boundaries>
## What's Out of Scope

- **Performance optimization for high concurrency** - This is a demo project expecting 4-5 concurrent users maximum. Don't optimize for hundreds of concurrent connections, message throttling, or scaling concerns.
- **Advanced WebSocket features** - Keep it simple: basic 1:1 connection per audit. No authentication/authorization on WebSocket connections, no message queuing/persistence, no multi-client broadcasting (for now).

</boundaries>

<specifics>
## Specific Ideas

- **Progressive agent-by-agent display**: Numeric agent section fills when numeric completes, then logic section fills when logic completes, etc. Results appear as each agent finishes, not all at once.
- **Simple status changes**: Basic lifecycle events (started, completed, error) plus the actual agent results. Keep status messages minimal and clean.
- **Data contract definition**: Part of this phase is defining what agent output looks like over WebSocket. Start from existing agent output format but refine it to present only useful, well-structured information.
- **Frontend already has client code**: Phase 7 implemented the WebSocket client in the frontend. This phase is backend-only - implement the `/ws/audit/{audit_id}` endpoint the frontend expects.

</specifics>

<notes>
## Additional Context

User is open to being challenged on technical approach. If WebSocket isn't the right solution for progressive result display, suggest alternatives.

Current issue: Frontend built in Phase 7 tries to connect to `/ws/audit/${auditId}` but gets 403 Forbidden because backend has no WebSocket handler defined at that route.

The four agents run in parallel via the root orchestrator (Phase 3.1). WebSocket needs to tap into that execution flow to emit events as agents start/complete and stream their results.

</notes>

---

*Phase: 08-backend-websocket-support*
*Context gathered: 2026-01-24*
