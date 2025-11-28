"""
WebSocket Connection Manager for Lullaby Generation Notifications
Reuses pattern from story_websocket_manager.py
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass

@dataclass
class WebSocketConnection:
    websocket: WebSocket
    user_id: str
    lullaby_ids: List[str]
    connected_at: datetime
    last_ping: Optional[datetime] = None
    
class LullabyWebSocketManager:
    """Manages WebSocket connections for lullaby generation notifications"""
    
    def __init__(self):
        # Map lullaby_id -> list of connections interested in that lullaby
        self.lullaby_connections: Dict[str, List[WebSocketConnection]] = {}
        # Map user_id -> list of connections for that user
        self.user_connections: Dict[str, List[WebSocketConnection]] = {}
        # All active connections
        self.active_connections: List[WebSocketConnection] = []
        
    async def connect(self, websocket: WebSocket, user_id: str) -> WebSocketConnection:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            lullaby_ids=[],
            connected_at=datetime.utcnow()
        )
        
        self.active_connections.append(connection)
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection)
        
        print(f"📡 WebSocket connected for user {user_id} (lullaby channel)")
        
        # Send connection confirmation
        await self._send_to_connection(connection, {
            "event": "connected",
            "user_id": user_id,
            "message": "WebSocket connection established for lullaby notifications",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return connection
    
    async def disconnect(self, connection: WebSocketConnection):
        """Handle WebSocket disconnection"""
        try:
            print(f"🔌 WebSocket disconnecting for user {connection.user_id} (lullaby channel)")
            
            # Remove from active connections
            if connection in self.active_connections:
                self.active_connections.remove(connection)
            
            # Remove from user connections
            user_connections = self.user_connections.get(connection.user_id, [])
            if connection in user_connections:
                user_connections.remove(connection)
                if not user_connections:
                    del self.user_connections[connection.user_id]
            
            # Remove from lullaby subscriptions
            subscribed_lullabies = list(connection.lullaby_ids)
            for lullaby_id in subscribed_lullabies:
                lullaby_connections = self.lullaby_connections.get(lullaby_id, [])
                if connection in lullaby_connections:
                    lullaby_connections.remove(connection)
                    if not lullaby_connections:
                        del self.lullaby_connections[lullaby_id]
            
            print(f"📡 WebSocket disconnected for user {connection.user_id} (was subscribed to {len(subscribed_lullabies)} lullabies)")
            
        except Exception as e:
            print(f"❌ Error during disconnect: {e}")
    
    async def subscribe_to_lullaby(self, connection: WebSocketConnection, lullaby_id: str):
        """Subscribe a connection to lullaby updates"""
        if lullaby_id not in connection.lullaby_ids:
            connection.lullaby_ids.append(lullaby_id)
        
        if lullaby_id not in self.lullaby_connections:
            self.lullaby_connections[lullaby_id] = []
        
        if connection not in self.lullaby_connections[lullaby_id]:
            self.lullaby_connections[lullaby_id].append(connection)
        
        print(f"📡 User {connection.user_id} subscribed to lullaby {lullaby_id}")
        
        # Confirm subscription
        await self._send_to_connection(connection, {
            "event": "subscribed",
            "lullaby_id": lullaby_id,
            "message": f"Subscribed to lullaby {lullaby_id} updates",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    async def unsubscribe_from_lullaby(self, connection: WebSocketConnection, lullaby_id: str):
        """Unsubscribe a connection from lullaby updates"""
        if lullaby_id in connection.lullaby_ids:
            connection.lullaby_ids.remove(lullaby_id)
        
        lullaby_connections = self.lullaby_connections.get(lullaby_id, [])
        if connection in lullaby_connections:
            lullaby_connections.remove(connection)
            if not lullaby_connections:
                del self.lullaby_connections[lullaby_id]
        
        print(f"📡 User {connection.user_id} unsubscribed from lullaby {lullaby_id}")
    
    async def broadcast_to_lullaby(self, lullaby_id: str, message: Dict):
        """Send a message to all connections subscribed to a lullaby"""
        connections = self.lullaby_connections.get(lullaby_id, [])
        if not connections:
            print(f"📡 No WebSocket connections for lullaby {lullaby_id}")
            return
        
        print(f"📡 Broadcasting to {len(connections)} connections for lullaby {lullaby_id}")
        
        # Send to all connections for this lullaby
        tasks = []
        for connection in connections.copy():  # Use copy to avoid modification during iteration
            tasks.append(self._send_to_connection_safe(connection, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_user(self, user_id: str, message: Dict):
        """Send a message to all connections for a specific user"""
        connections = self.user_connections.get(user_id, [])
        if not connections:
            print(f"⚠️ No active connections found for user {user_id} to broadcast lullaby message")
            return
        
        event_type = message.get("event", "unknown")
        print(f"📡 Broadcasting '{event_type}' to {len(connections)} connections for user {user_id}")
        
        tasks = []
        for connection in connections.copy():
            tasks.append(self._send_to_connection_safe(connection, message))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            print(f"✅ Successfully sent '{event_type}' to {success_count}/{len(connections)} connections")
    
    async def _send_to_connection(self, connection: WebSocketConnection, message: Dict):
        """Send a message to a specific connection"""
        try:
            event_type = message.get("event", "unknown")
            print(f"📤 Attempting to send '{event_type}' to user {connection.user_id}")
            await connection.websocket.send_text(json.dumps(message))
            print(f"✅ Successfully sent '{event_type}' to user {connection.user_id}")
        except Exception as e:
            print(f"❌ Error sending '{event_type}' to WebSocket {connection.user_id}: {e}")
            await self.disconnect(connection)
            raise e
    
    async def _send_to_connection_safe(self, connection: WebSocketConnection, message: Dict):
        """Send a message to a connection with error handling"""
        try:
            await self._send_to_connection(connection, message)
        except Exception as e:
            print(f"⚠️ Failed to send to connection {connection.user_id}: {e}")
            # Connection will be cleaned up automatically
    
    async def handle_message(self, connection: WebSocketConnection, message: Dict):
        """Handle incoming WebSocket message from client"""
        try:
            action = message.get("action")
            
            if action == "subscribe":
                lullaby_id = message.get("lullaby_id")
                if lullaby_id:
                    await self.subscribe_to_lullaby(connection, lullaby_id)
                else:
                    await self._send_to_connection(connection, {
                        "event": "error",
                        "message": "lullaby_id is required for subscribe action"
                    })
            
            elif action == "unsubscribe":
                lullaby_id = message.get("lullaby_id")
                if lullaby_id:
                    await self.unsubscribe_from_lullaby(connection, lullaby_id)
                else:
                    await self._send_to_connection(connection, {
                        "event": "error",
                        "message": "lullaby_id is required for unsubscribe action"
                    })
            
            elif action == "ping":
                connection.last_ping = datetime.utcnow()
                await self._send_to_connection(connection, {
                    "event": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                await self._send_to_connection(connection, {
                    "event": "error",
                    "message": f"Unknown action: {action}"
                })
        
        except Exception as e:
            print(f"❌ Error handling message: {e}")
            await self._send_to_connection(connection, {
                "event": "error",
                "message": f"Error handling message: {str(e)}"
            })
    
    def get_connection_stats(self) -> Dict:
        """Get statistics about active connections"""
        return {
            "total_connections": len(self.active_connections),
            "users_connected": len(self.user_connections),
            "lullabies_subscribed": len(self.lullaby_connections),
            "connections_per_user": {
                user_id: len(conns) 
                for user_id, conns in self.user_connections.items()
            }
        }

# Singleton instance
lullaby_websocket_manager = LullabyWebSocketManager()
