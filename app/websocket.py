from fastapi import WebSocket, Depends
from typing import Dict
import json
from .auth import get_current_user
from .database import get_db
from .queue import broker

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_personal_message(self, message: str, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket, token: str = Depends(get_current_user)):
    user = await get_current_user(token, next(get_db()))
    await manager.connect(websocket, user.id)
    channel = broker.channel()
    
    try:
        consumer = channel.consume(f"user:{user.id}")
        while True:
            message = next(consumer)
            if message is not None:
                data = json.loads(message.decode())
                await manager.send_personal_message(json.dumps(data), user.id)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(user.id)
        channel.close()