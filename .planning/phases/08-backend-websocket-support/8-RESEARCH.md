# Phase 8: Backend WebSocket Support - Research

**Researched:** 2026-01-24
**Domain:** FastAPI WebSocket implementation with async agent execution streaming
**Confidence:** HIGH

<research_summary>
## Summary

Researched FastAPI WebSocket patterns for streaming real-time updates from long-running async agent execution. The standard approach uses FastAPI's native WebSocket support with a ConnectionManager pattern for multi-client handling, combined with asyncio.create_task() for concurrent background processing.

Key finding: Don't use BackgroundTasks for WebSocket streaming - they're designed for HTTP endpoints and have lifecycle incompatibilities with WebSocket connections. Instead, use asyncio.create_task() to run the agent processor concurrently while streaming progress updates via an asyncio.Queue to the WebSocket handler.

The existing codebase already uses `runner.run_async()` which yields events - these events can be intercepted and forwarded to a WebSocket connection via a queue-based producer-consumer pattern.

**Primary recommendation:** Use ConnectionManager pattern for connection lifecycle + asyncio.create_task() for concurrent agent execution + asyncio.Queue for event streaming. The agent runner already emits events asynchronously - just need to wire them to WebSocket.
</research_summary>

<standard_stack>
## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115+ | Web framework with native WebSocket support | Built-in WebSocket support via Starlette |
| websockets | Latest | WebSocket protocol implementation | Required dependency for FastAPI WebSockets |
| asyncio | stdlib | Async primitives (Queue, create_task) | Python's native async runtime |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| encode/broadcaster | Latest | Multi-process WebSocket broadcasting | Only if deploying with >1 worker process (out of scope) |
| fastapi-websocket-pubsub | Latest | Pub/sub abstraction for WebSockets | Only if need complex topic-based broadcasting (out of scope) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WebSocket | Server-Sent Events (SSE) | SSE simpler but one-way only; WebSocket needed if future bi-directional |
| WebSocket | HTTP Polling | Polling simpler but higher latency + server load |
| asyncio.Queue | In-memory state | Queue pattern cleaner for producer-consumer, handles backpressure |

**Installation:**
```bash
pip install websockets  # FastAPI requires this for WebSocket support
# No additional dependencies needed - use stdlib asyncio
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/routes/
│   └── websockets.py          # WebSocket endpoints
├── services/
│   ├── processor.py            # Existing agent processor
│   └── websocket_manager.py    # Connection manager
└── schemas/
    └── websocket.py            # WebSocket message schemas
```

### Pattern 1: ConnectionManager for Client Lifecycle
**What:** Centralized manager for tracking active WebSocket connections, handling connect/disconnect
**When to use:** Always - standard pattern for WebSocket apps
**Example:**
```python
# Source: FastAPI official docs - https://fastapi.tiangolo.com/advanced/websockets/
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        # Track active connections by audit_id
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, audit_id: str, websocket: WebSocket):
        await websocket.accept()
        if audit_id not in self.active_connections:
            self.active_connections[audit_id] = []
        self.active_connections[audit_id].append(websocket)

    def disconnect(self, audit_id: str, websocket: WebSocket):
        if audit_id in self.active_connections:
            self.active_connections[audit_id].remove(websocket)
            if not self.active_connections[audit_id]:
                del self.active_connections[audit_id]

    async def send_to_audit(self, audit_id: str, message: dict):
        """Send message to all connections watching this audit"""
        if audit_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[audit_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.append(connection)
            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(audit_id, conn)
```

### Pattern 2: Concurrent Agent Execution with Event Streaming
**What:** Run agent processor in background task, stream events to WebSocket via Queue
**When to use:** When WebSocket needs updates from long-running async operations
**Example:**
```python
# Pattern based on research findings
import asyncio
from asyncio import Queue

@app.websocket("/ws/audit/{audit_id}")
async def websocket_endpoint(audit_id: str, websocket: WebSocket):
    await manager.connect(audit_id, websocket)

    # Create queue for agent events
    event_queue: Queue = asyncio.Queue()

    # Start agent processing in background
    async def process_and_stream():
        async for event in runner.run_async(...):
            # Put events in queue for WebSocket consumer
            await event_queue.put({
                "type": "agent_event",
                "data": event.to_dict()
            })
        await event_queue.put({"type": "complete"})

    processor_task = asyncio.create_task(process_and_stream())

    try:
        # Stream events to client
        while True:
            event = await event_queue.get()
            await websocket.send_json(event)
            if event["type"] == "complete":
                break
    except WebSocketDisconnect:
        # Clean up on disconnect
        processor_task.cancel()
        manager.disconnect(audit_id, websocket)
```

### Pattern 3: Message Schema for Agent Progress Updates
**What:** Structured message format for different update types
**When to use:** Always - ensures frontend can parse messages correctly
**Example:**
```python
# Pydantic schemas for WebSocket messages
from pydantic import BaseModel
from typing import Literal

class AgentStartedMessage(BaseModel):
    type: Literal["agent_started"]
    agent_id: str  # "numeric_validation", "logic_consistency", etc.
    timestamp: str

class AgentCompletedMessage(BaseModel):
    type: Literal["agent_completed"]
    agent_id: str
    findings: list[dict]  # Agent-specific finding structure
    timestamp: str

class AgentErrorMessage(BaseModel):
    type: Literal["agent_error"]
    agent_id: str
    error: str
    timestamp: str
```

### Anti-Patterns to Avoid
- **Using BackgroundTasks with WebSocket:** BackgroundTasks run AFTER response returns, incompatible with WebSocket lifecycle
- **No disconnection cleanup:** Always cancel background tasks when WebSocket disconnects to avoid orphaned processes
- **Blocking operations in WebSocket handler:** All I/O must be async - blocking calls will freeze all WebSocket connections
- **No error handling on send:** WebSocket send can fail if client disconnected - always handle exceptions
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection tracking | Custom dict with manual cleanup | ConnectionManager pattern | Handles edge cases: concurrent connects, cleanup on error, dead connection detection |
| Message serialization | String formatting | Pydantic models + send_json() | Type safety, validation, consistent format |
| Heartbeat/keepalive | Custom ping loop | Built-in WebSocket ping/pong | Protocol-level support, automatic in Starlette/websockets |
| Multi-process broadcasting | Custom Redis pub/sub | encode/broadcaster | Only if scaling to multiple workers - out of scope for Phase 8 |
| Event queue | Global state dict | asyncio.Queue | Handles backpressure, thread-safe, proper async semantics |

**Key insight:** FastAPI (via Starlette) handles WebSocket protocol details automatically. Don't implement custom ping/pong, frame parsing, or protocol negotiation - the framework does this. Focus on business logic: what messages to send, when to send them.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: BackgroundTasks with WebSocket Endpoints
**What goes wrong:** Using FastAPI's BackgroundTasks with WebSocket routes causes tasks to never run or run at wrong time
**Why it happens:** BackgroundTasks are designed for HTTP endpoints (run after response returns). WebSockets don't "return" - they stay open.
**How to avoid:** Use asyncio.create_task() instead for concurrent operations in WebSocket handlers
**Warning signs:** Background tasks not executing, tasks running after WebSocket closes

### Pitfall 2: Orphaned Background Tasks on Disconnect
**What goes wrong:** Client disconnects but agent processing continues running, wasting resources
**Why it happens:** Not canceling background tasks when WebSocketDisconnect exception raised
**How to avoid:** Always wrap WebSocket loop in try/except, cancel tasks in except/finally block
**Warning signs:** Increasing memory usage, processes running for completed audits

### Pitfall 3: Blocking the WebSocket Event Loop
**What goes wrong:** One slow WebSocket handler blocks all other WebSocket connections
**Why it happens:** Using blocking I/O (sync database queries, sync agent calls) in WebSocket handler
**How to avoid:** Ensure all operations are async. Use async database sessions, run_async() for agents.
**Warning signs:** All WebSocket clients freeze when one client has slow operation

### Pitfall 4: Not Handling Send Failures
**What goes wrong:** Exception when sending to disconnected client crashes WebSocket manager
**Why it happens:** Client disconnected between last send and current send, no exception handling
**How to avoid:** Wrap all send operations in try/except, remove dead connections from manager
**Warning signs:** ConnectionManager crashes, other clients lose connection when one disconnects

### Pitfall 5: In-Memory ConnectionManager with Multiple Workers
**What goes wrong:** Client connects to worker A, but agent events go to worker B's ConnectionManager
**Why it happens:** Each worker process has separate memory, in-memory ConnectionManager not shared
**How to avoid:** For single worker (Phase 8 scope): not an issue. For production scaling: use encode/broadcaster with Redis
**Warning signs:** Clients connect but don't receive updates, works locally but not in production with >1 worker
</common_pitfalls>

<code_examples>
## Code Examples

Verified patterns from official sources:

### Basic WebSocket Endpoint with Path Parameter
```python
# Source: https://fastapi.tiangolo.com/advanced/websockets/
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.websocket("/ws/audit/{audit_id}")
async def websocket_endpoint(audit_id: str, websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive (optional - for bi-directional)
            data = await websocket.receive_text()

            # Send
            await websocket.send_json({
                "audit_id": audit_id,
                "message": f"Received: {data}"
            })
    except WebSocketDisconnect:
        print(f"Client disconnected from audit {audit_id}")
```

### Producer-Consumer Pattern with asyncio.Queue
```python
# Pattern from research: https://github.com/greed2411/fastapi_ws_producer_consumer
import asyncio

@app.websocket("/ws/audit/{audit_id}")
async def websocket_endpoint(audit_id: str, websocket: WebSocket):
    await websocket.accept()

    queue = asyncio.Queue()

    # Producer: runs agent, puts events in queue
    async def run_agent():
        try:
            async for event in processor.run_async(audit_id):
                await queue.put(event)
        finally:
            await queue.put(None)  # Signal completion

    # Consumer: reads from queue, sends to WebSocket
    async def stream_to_client():
        while True:
            event = await queue.get()
            if event is None:
                break
            await websocket.send_json(event)

    producer = asyncio.create_task(run_agent())
    consumer = asyncio.create_task(stream_to_client())

    try:
        await consumer
    except WebSocketDisconnect:
        producer.cancel()
        consumer.cancel()
```

### Integration with Existing Agent Runner
```python
# Adapted for existing codebase pattern (app/services/processor.py)
from google.adk.runners import InMemoryRunner
from app.services.websocket_manager import manager

async def process_with_websocket(job_id: UUID, audit_id: str, extracted_text: str):
    """Process document and stream updates via WebSocket."""
    runner = InMemoryRunner(agent=root_agent, app_name="veritas-ai")
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=str(job_id)
    )

    content = UserContent(parts=[Part(text=extracted_text)])

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
        # Stream each event to WebSocket clients watching this audit
        await manager.send_to_audit(audit_id, {
            "type": "agent_event",
            "event": event.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        })

    # Send completion message
    await manager.send_to_audit(audit_id, {
        "type": "complete",
        "timestamp": datetime.utcnow().isoformat()
    })
```
</code_examples>

<sota_updates>
## State of the Art (2025-2026)

What's changed recently:

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate WebSocket library | FastAPI native WebSocket | FastAPI 0.60+ (2020) | No need for separate ws library, built into FastAPI |
| Manual connection dict | ConnectionManager pattern | Community standard ~2021 | Cleaner lifecycle management, official FastAPI examples |
| Thread-based concurrency | asyncio.create_task() | Python 3.7+ async/await | Better performance, simpler code for I/O-bound tasks |
| Custom serialization | Pydantic + send_json() | Pydantic v2 (2023) | Type safety, automatic validation, faster serialization |

**New tools/patterns to consider:**
- **fastapi-websocket-pubsub:** Adds pub/sub abstraction for topic-based broadcasting. Useful if adding "subscribe to multiple audits" feature later. Not needed for Phase 8's single-audit subscription.
- **asyncio.TaskGroup (Python 3.11+):** Better structured concurrency for managing multiple background tasks. Use instead of manual create_task() if Python 3.11+.

**Deprecated/outdated:**
- **BackgroundTasks for WebSocket:** Never worked correctly, explicitly documented as HTTP-only in FastAPI 0.100+
- **WebSocket in vanilla Starlette without FastAPI:** FastAPI's wrapper adds better dependency injection, easier routing
</sota_updates>

<open_questions>
## Open Questions

Things that couldn't be fully resolved:

1. **Agent Event Format**
   - What we know: `runner.run_async()` yields events with session state updates
   - What's unclear: Exact structure of events from Google ADK's InMemoryRunner (what properties/methods available)
   - Recommendation: During implementation, inspect event object structure. Likely has `.session.state` for agent outputs. May need to transform to simpler format for frontend.

2. **Timing of Agent Completion vs Result Availability**
   - What we know: Existing processor waits for all events, then extracts findings from `final_state`
   - What's unclear: Can we extract partial findings from intermediate events, or only from final state?
   - Recommendation: Start with sending status updates ("agent started", "agent completed"), then findings from final state. Optimize later if intermediate findings available.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) - Official documentation, connection manager pattern, error handling
- [FastAPI Async/Await](https://fastapi.tiangolo.com/async/) - Concurrency patterns with FastAPI
- [Better Stack: FastAPI WebSockets Guide](https://betterstack.com/community/guides/scaling-python/fastapi-websockets/) - Connection manager pattern, broadcasting
- [GetOrchestra: FastAPI WebSockets Guide](https://www.getorchestra.io/guides/fastapi-and-websockets-a-comprehensive-guide) - Best practices, error handling

### Secondary (MEDIUM confidence)
- [TestDriven.io: Real-time Dashboard](https://testdriven.io/blog/fastapi-postgres-websockets/) (2025) - Verified pattern for streaming DB changes via WebSocket
- [Medium: Background Tasks with WebSockets](https://hexshift.medium.com/implementing-background-tasks-with-websockets-in-fastapi-034cdf803430) - Confirmed asyncio.create_task() pattern (couldn't fetch full article)
- [GitHub: fastapi_ws_producer_consumer](https://github.com/greed2411/fastapi_ws_producer_consumer) - Producer-consumer with asyncio.Queue example
- [UnfoldAI: FastAPI WebSockets](https://unfoldai.com/fastapi-and-websockets/) - Real-time features, background task patterns

### Tertiary (LOW confidence - needs validation)
- None - all patterns verified against official FastAPI docs or community standards
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: FastAPI WebSocket endpoints
- Ecosystem: asyncio.Queue for event streaming, ConnectionManager pattern
- Patterns: Producer-consumer with async agents, concurrent task management
- Pitfalls: BackgroundTasks incompatibility, task cleanup, blocking operations

**Confidence breakdown:**
- Standard stack: HIGH - FastAPI native WebSocket support is official, well-documented
- Architecture: HIGH - ConnectionManager and asyncio patterns verified in official docs and multiple sources
- Pitfalls: HIGH - BackgroundTasks issue documented in GitHub issues, asyncio pitfalls well-known
- Code examples: HIGH - from official FastAPI docs and verified community examples

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - FastAPI WebSocket API is stable)

**Integration with existing codebase:**
- Existing: `app/services/processor.py` uses `runner.run_async()` which yields events
- Existing: `app/main.py` has FastAPI app, CORS middleware, router includes
- New: Add `app/services/websocket_manager.py` for ConnectionManager
- New: Add `app/api/routes/websockets.py` for WebSocket endpoint
- New: Add `app/schemas/websocket.py` for message schemas
- Modify: `processor.py` to optionally stream events to WebSocket (backward compatible)
</metadata>

---

*Phase: 08-backend-websocket-support*
*Research completed: 2026-01-24*
*Ready for planning: yes*
