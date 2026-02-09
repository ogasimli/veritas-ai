"""WebSocket connection manager for tracking and broadcasting to active connections."""

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time audit updates."""

    def __init__(self):
        """Initialize the connection manager with empty connection tracking."""
        # Track active connections by job_id
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """
        Accept and track a new WebSocket connection for a job.

        Args:
            job_id: The job ID to associate with this connection
            websocket: The WebSocket connection to track
        """
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        """
        Remove a WebSocket connection and clean up empty job lists.

        Args:
            job_id: The job ID associated with this connection
            websocket: The WebSocket connection to remove
        """
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            # Clean up empty lists
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def send_to_job(self, job_id: str, message: dict):
        """
        Send a JSON message to all connections watching this job.

        Automatically handles dead connections by removing them.

        Args:
            job_id: The job ID to broadcast to
            message: The message dict to send as JSON
        """
        if job_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Connection is dead, mark for removal
                    dead_connections.append(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(job_id, conn)


# Global singleton instance
manager = ConnectionManager()
