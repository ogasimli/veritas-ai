---
phase: 08-backend-websocket-support
plan: 01
type: execute
---

<objective>
Implement FastAPI WebSocket endpoint for real-time audit progress streaming.

Purpose: Enable frontend to receive live updates as validation agents complete their work, keeping users engaged during lengthy analysis (can take minutes). This is fundamentally about UX during wait time - showing progressive results as each agent finishes instead of waiting for all agents to complete.

Output: Working WebSocket endpoint at /ws/audit/{audit_id} that streams agent lifecycle events and results to connected clients using the established ConnectionManager pattern.
</objective>

<execution_context>
~/.claude/get-shit-done/workflows/execute-phase.md
~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/08-backend-websocket-support/8-CONTEXT.md
@.planning/phases/08-backend-websocket-support/8-RESEARCH.md
@backend/app/main.py
@backend/app/services/processor.py
@backend/app/api/routes/__init__.py

**Tech stack available:**
- FastAPI with native WebSocket support
- asyncio stdlib (Queue, create_task)
- Pydantic for message schemas
- Existing Google ADK InMemoryRunner that yields events via run_async()

**Established patterns:**
- FastAPI route structure in app/api/routes/
- Pydantic schemas in app/schemas/
- Service layer in app/services/
- Agent execution via InMemoryRunner.run_async() in processor.py

**Key insight from research:**
- DON'T use FastAPI BackgroundTasks with WebSocket (incompatible lifecycle)
- DO use asyncio.create_task() for concurrent agent execution
- DO use asyncio.Queue for producer-consumer pattern (agent events → WebSocket)
- Existing processor.py already uses runner.run_async() which yields events - we tap into this stream

**User vision (from CONTEXT.md):**
- Progressive agent-by-agent display: Results appear as each agent completes, not all at once
- Keep users engaged during long waits (analysis can take minutes)
- Clear data contract for agent → backend → frontend
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create WebSocket connection manager</name>
  <files>backend/app/services/websocket_manager.py</files>
  <action>
  Create ConnectionManager class following the pattern from RESEARCH.md:
  - Track active connections by audit_id in dict[str, list[WebSocket]]
  - async connect(audit_id: str, websocket: WebSocket): accept connection, add to tracking
  - disconnect(audit_id: str, websocket: WebSocket): remove from tracking, clean up empty lists
  - async send_to_audit(audit_id: str, message: dict): send JSON to all connections for that audit, handle dead connections (try/except, remove on failure)

  Use FastAPI's WebSocket import. Don't overcomplicate - single-process in-memory manager is sufficient (out of scope: multi-worker broadcasting with Redis).
  </action>
  <verify>File exists, imports valid (from fastapi import WebSocket), class has all three methods with correct signatures</verify>
  <done>ConnectionManager class ready to use, follows exact pattern from research</done>
</task>

<task type="auto">
  <name>Task 2: Create message schemas for WebSocket communication</name>
  <files>backend/app/schemas/websocket.py</files>
  <action>
  Create Pydantic models for WebSocket messages to ensure type safety and consistent format:

  1. AgentStartedMessage(BaseModel):
     - type: Literal["agent_started"]
     - agent_id: str (e.g. "numeric_validation", "logic_consistency")
     - timestamp: str (ISO format)

  2. AgentCompletedMessage(BaseModel):
     - type: Literal["agent_completed"]
     - agent_id: str
     - findings: list[dict] (agent-specific finding structure)
     - timestamp: str

  3. AgentErrorMessage(BaseModel):
     - type: Literal["agent_error"]
     - agent_id: str
     - error: str
     - timestamp: str

  4. AuditCompleteMessage(BaseModel):
     - type: Literal["audit_complete"]
     - timestamp: str

  Use Pydantic v2 syntax. Import from pydantic not pydantic.v1. These schemas define the data contract mentioned in CONTEXT.md.
  </action>
  <verify>File exists, all four schemas import successfully, each has correct type literal</verify>
  <done>Message schemas ready for use in WebSocket endpoint and processor integration</done>
</task>

<task type="auto">
  <name>Task 3: Create WebSocket endpoint and integrate with processor</name>
  <files>backend/app/api/routes/websockets.py, backend/app/services/processor.py</files>
  <action>
  Part A - Create websockets.py:
  1. Import: FastAPI, WebSocket, WebSocketDisconnect, router = APIRouter()
  2. Import ConnectionManager singleton: manager = ConnectionManager()
  3. Create endpoint @router.websocket("/ws/audit/{audit_id}"):
     - Path parameter: audit_id: str
     - Accept connection: await manager.connect(audit_id, websocket)
     - Keep connection alive with try/except WebSocketDisconnect
     - In try block: await websocket.receive_text() in loop (keeps connection open, client can send heartbeats)
     - In except: manager.disconnect(audit_id, websocket)

  Part B - Modify processor.py:
  1. Import: asyncio, datetime, websocket_manager.manager, websocket schemas
  2. In DocumentProcessor.process_document(), wrap the runner.run_async() loop:
     - Keep existing logic that collects final_state
     - ADD: For each event in the async loop, determine agent completion and send WebSocket messages:
       * When an agent's state appears in event.session.state for the first time: send AgentStartedMessage
       * When an agent's output (e.g. reviewer_output) is present: send AgentCompletedMessage with findings
       * On any exception: send AgentErrorMessage
     - After loop completes: send AuditCompleteMessage

  Use asyncio.create_task() if needed for concurrent operations. DO NOT use BackgroundTasks (incompatible with WebSocket per research). Follow the producer pattern from RESEARCH.md - agent execution produces events, we forward them to WebSocket.

  The existing processor already extracts findings from final_state at the end - we're adding real-time streaming of those same findings as they become available.
  </action>
  <verify>
  1. WebSocket endpoint exists, can be imported
  2. python -m py_compile backend/app/api/routes/websockets.py (no syntax errors)
  3. Processor imports manager and schemas without errors
  4. WebSocket messages sent during agent execution (check code flow)
  </verify>
  <done>
  - WebSocket endpoint created at /ws/audit/{audit_id}
  - Processor modified to stream agent events via WebSocket
  - Messages follow schema contract (typed with Pydantic)
  - Integration follows asyncio.create_task() pattern from research, NOT BackgroundTasks
  </done>
</task>

<task type="auto">
  <name>Task 4: Register WebSocket router in main.py</name>
  <files>backend/app/main.py, backend/app/api/routes/__init__.py</files>
  <action>
  1. In backend/app/api/routes/__init__.py:
     - Add import: from app.api.routes.websockets import router as websockets_router
     - Add to __all__: "websockets_router"

  2. In backend/app/main.py:
     - Import websockets_router from app.api.routes
     - Add after existing routers: app.include_router(websockets_router)
     - No prefix needed (WebSocket route already has /ws/audit/ in definition)

  Keep existing CORS middleware - WebSocket works with it. Don't add WebSocket-specific middleware.
  </action>
  <verify>
  1. python -m py_compile backend/app/main.py (no errors)
  2. grep -r "websockets_router" backend/app/ shows both import and include
  3. Router registered in app
  </verify>
  <done>WebSocket router integrated into FastAPI app, endpoint accessible at /ws/audit/{audit_id}</done>
</task>

</tasks>

<verification>
Before declaring phase complete:
- [ ] All Python files compile without syntax errors
- [ ] WebSocket endpoint registered in FastAPI app
- [ ] ConnectionManager follows pattern from research (no BackgroundTasks)
- [ ] Message schemas are typed with Pydantic
- [ ] Processor integration preserves existing functionality (still saves findings to DB)
</verification>

<success_criteria>

- All tasks completed
- All verification checks pass
- WebSocket endpoint exists at /ws/audit/{audit_id}
- ConnectionManager handles multi-client connections for same audit
- Processor streams events to WebSocket during agent execution
- Message schemas provide type safety
- No BackgroundTasks used (asyncio patterns only)
- Existing processor functionality unchanged (backward compatible)
</success_criteria>

<output>
After completion, create `.planning/phases/08-backend-websocket-support/8-01-SUMMARY.md`:

# Phase 8 Plan 1: Backend WebSocket Support Summary

**[Substantive one-liner - what shipped]**

## Accomplishments

- WebSocket endpoint implemented at /ws/audit/{audit_id}
- ConnectionManager pattern for multi-client support
- Real-time agent event streaming integrated with processor
- Typed message schemas for data contract

## Files Created/Modified

- `backend/app/services/websocket_manager.py` - ConnectionManager class
- `backend/app/schemas/websocket.py` - Message schemas
- `backend/app/api/routes/websockets.py` - WebSocket endpoint
- `backend/app/services/processor.py` - Added event streaming
- `backend/app/api/routes/__init__.py` - Router exports
- `backend/app/main.py` - Router registration

## Decisions Made

- Used asyncio.create_task() pattern instead of BackgroundTasks (per research)
- In-memory ConnectionManager sufficient for demo (4-5 concurrent users)
- Message schemas define clear data contract as requested in context

## Issues Encountered

[Problems and resolutions, or "None"]

## Next Phase Readiness

Phase 8 complete. All 8 phases finished. Backend WebSocket support enables frontend real-time updates.
</output>
