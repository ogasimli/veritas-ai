"""WebSocket connection manager for tracking and broadcasting to active connections."""

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time audit updates."""

    def __init__(self):
        """Initialize the connection manager with empty connection tracking."""
        # Track active connections by audit_id
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, audit_id: str, websocket: WebSocket):
        """
        Accept and track a new WebSocket connection for an audit.

        Args:
            audit_id: The audit ID to associate with this connection
            websocket: The WebSocket connection to track
        """
        await websocket.accept()
        if audit_id not in self.active_connections:
            self.active_connections[audit_id] = []
        self.active_connections[audit_id].append(websocket)

    def disconnect(self, audit_id: str, websocket: WebSocket):
        """
        Remove a WebSocket connection and clean up empty audit lists.

        Args:
            audit_id: The audit ID associated with this connection
            websocket: The WebSocket connection to remove
        """
        if audit_id in self.active_connections:
            self.active_connections[audit_id].remove(websocket)
            # Clean up empty lists
            if not self.active_connections[audit_id]:
                del self.active_connections[audit_id]

    async def send_to_audit(self, audit_id: str, message: dict):
        """
        Send a JSON message to all connections watching this audit.

        Automatically handles dead connections by removing them.

        Args:
            audit_id: The audit ID to broadcast to
            message: The message dict to send as JSON
        """
        if audit_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[audit_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Connection is dead, mark for removal
                    dead_connections.append(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.disconnect(audit_id, conn)


# Global singleton instance
manager = ConnectionManager()
