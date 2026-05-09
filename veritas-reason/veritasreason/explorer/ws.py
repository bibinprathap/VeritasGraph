"""
VeritasReason Explorer : WebSocket Connection Manager

Manages WebSocket connections for real-time graph updates,
import progress events, and mutation broadcasts.
"""

import asyncio
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    """
    Thread-safe WebSocket connection manager.

    Maintains a set of active WebSocket connections and provides
    methods to broadcast events to all connected clients.
    """

    def __init__(self):
        self._active_connections: Set[WebSocket] = set()
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and add it to the active set."""
        await websocket.accept()
        with self._lock:
            self._active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the active set."""
        with self._lock:
            self._active_connections.discard(websocket)

    @property
    def active_count(self) -> int:
        """Number of active connections."""
        with self._lock:
            return len(self._active_connections)

    async def broadcast(self, event_type: str, data: Any = None) -> None:
        """
        Broadcast a JSON message to all connected clients.

        Args:
            event_type: Event type string (e.g., "node_added", "import_progress").
            data: Arbitrary JSON-serialisable payload.
        """
        message = json.dumps(
            {
                "event": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            default=str,
        )

        with self._lock:
            connections = set(self._active_connections)

    
        disconnected: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)

        if disconnected:
            with self._lock:
                for ws in disconnected:
                    self._active_connections.discard(ws)

    async def send_personal(
        self, websocket: WebSocket, event_type: str, data: Any = None
    ) -> None:
        """Send a message to a single client."""
        message = json.dumps(
            {
                "event": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            default=str,
        )
        await websocket.send_text(message)
