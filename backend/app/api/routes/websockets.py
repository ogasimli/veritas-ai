"""WebSocket routes for real-time audit updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import manager

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def websocket_endpoint(job_id: str, websocket: WebSocket):
    """
    WebSocket endpoint for real-time audit progress updates.

    Clients connect to this endpoint to receive live updates as validation
    agents complete their work. The connection stays open until the audit
    completes or the client disconnects.

    Args:
        job_id: The job ID to subscribe to
        websocket: The WebSocket connection
    """
    # Accept and track the connection
    await manager.connect(job_id, websocket)

    try:
        # Keep connection alive - client can send heartbeats if needed
        while True:
            # Receive any messages from client (optional, for bi-directional)
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Clean up when client disconnects
        manager.disconnect(job_id, websocket)
