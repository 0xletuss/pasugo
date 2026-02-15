# routes/messaging.py
# ─────────────────────────────────────────────────────────────
# FastAPI WebSocket + REST routes for Pasugo Messaging - FIXED
# NOW QUERIES THE UNIFIED 'requests' TABLE (not bill_requests)
# ─────────────────────────────────────────────────────────────

import json
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import get_current_user
from utils.security import verify_token_silent
from services.message_service import MessageService

# ✅ Import the request model
try:
    from models.request import Request
except ImportError:
    from models.bill_request import BillRequest as Request

router = APIRouter(prefix="/api/messages", tags=["messaging"])


# ── Pydantic Schemas ───────────────────────────────────────────

class CreateConversationRequest(BaseModel):
    request_id: int


# ── WebSocket Connection Manager ───────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[int, dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: int, user_id: int):
        await websocket.accept()
        if conversation_id not in self.rooms:
            self.rooms[conversation_id] = {}
        self.rooms[conversation_id][user_id] = websocket

    def disconnect(self, conversation_id: int, user_id: int):
        if conversation_id in self.rooms:
            self.rooms[conversation_id].pop(user_id, None)
            if not self.rooms[conversation_id]:
                del self.rooms[conversation_id]

    async def broadcast_to_room(self, conversation_id: int, data: dict, exclude_user_id: int = None):
        if conversation_id not in self.rooms:
            return
        dead = []
        for uid, ws in self.rooms[conversation_id].items():
            if exclude_user_id and uid == exclude_user_id:
                continue
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.rooms[conversation_id].pop(uid, None)

    async def send_to_user(self, conversation_id: int, user_id: int, data: dict):
        ws = self.rooms.get(conversation_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass

    def is_user_in_room(self, conversation_id: int, user_id: int) -> bool:
        return user_id in self.rooms.get(conversation_id, {})


manager = ConnectionManager()


# ── WebSocket Endpoint ─────────────────────────────────────────

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user = verify_token_silent(token)
    if not user:
        await websocket.close(code=4001)
        return

    user_id   = int(user.get("sub"))
    user_type = user.get("user_type")
    full_name = user.get("full_name", "")
    socket_id = str(uuid.uuid4())

    service = MessageService(db)

    if not service.user_has_access(user_id, user_type, conversation_id):
        await websocket.close(code=4003)
        return

    await manager.connect(websocket, conversation_id, user_id)
    service.register_connection(user_id, socket_id)

    await manager.broadcast_to_room(conversation_id, {
        "event": "user_joined",
        "user_id": user_id,
        "full_name": full_name,
        "is_online": True,
    }, exclude_user_id=user_id)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            event = data.get("event")

            if event == "send_message":
                content        = data.get("content")
                message_type   = data.get("message_type", "text")
                attachment_url = data.get("attachment_url")
                attachment_type = data.get("attachment_type")

                if not content and not attachment_url:
                    await websocket.send_text(json.dumps({
                        "event": "error", "message": "Message content is required"
                    }))
                    continue

                msg = service.create_message(
                    conversation_id=conversation_id,
                    sender_id=user_id,
                    sender_type=user_type,
                    message_type=message_type,
                    content=content,
                    attachment_url=attachment_url,
                    attachment_type=attachment_type,
                )

                payload = {
                    "event":           "new_message",
                    "message_id":      msg.message_id,
                    "conversation_id": conversation_id,
                    "sender_id":       user_id,
                    "sender_type":     user_type,
                    "sender_name":     full_name,
                    "message_type":    msg.message_type,
                    "content":         msg.content,
                    "attachment_url":  msg.attachment_url,
                    "sent_at":         msg.sent_at.isoformat(),
                }
                await manager.broadcast_to_room(conversation_id, payload)

            elif event == "mark_read":
                message_ids = data.get("message_ids", [])
                if message_ids:
                    service.mark_messages_read(message_ids, user_id)
                    await manager.broadcast_to_room(conversation_id, {
                        "event":           "messages_read",
                        "conversation_id": conversation_id,
                        "message_ids":     message_ids,
                        "read_by":         user_id,
                        "read_at":         datetime.utcnow().isoformat(),
                    }, exclude_user_id=user_id)

            elif event == "typing_start":
                service.set_typing_status(conversation_id, user_id, True)
                await manager.broadcast_to_room(conversation_id, {
                    "event":           "user_typing",
                    "conversation_id": conversation_id,
                    "user_id":         user_id,
                    "full_name":       full_name,
                    "is_typing":       True,
                }, exclude_user_id=user_id)

            elif event == "typing_stop":
                service.set_typing_status(conversation_id, user_id, False)
                await manager.broadcast_to_room(conversation_id, {
                    "event":     "user_typing",
                    "user_id":   user_id,
                    "is_typing": False,
                }, exclude_user_id=user_id)

            elif event == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))

    except WebSocketDisconnect:
        manager.disconnect(conversation_id, user_id)
        service.deregister_connection(socket_id)
        service.set_typing_status(conversation_id, user_id, False)

        await manager.broadcast_to_room(conversation_id, {
            "event":     "user_left",
            "user_id":   user_id,
            "full_name": full_name,
            "is_online": False,
        })


# ── REST Endpoints ─────────────────────────────────────────────

@router.get("/conversations")
def get_conversations(
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    service = MessageService(db)
    conversations = service.get_user_conversations(
        current_user.user_id, current_user.user_type
    )
    return {"success": True, "data": conversations}


@router.post("/conversations")
def create_conversation(
    body: CreateConversationRequest,
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    """
    ✅ FIXED: Queries the unified 'requests' table
    Handles ALL request types: groceries, bills, delivery, pickup, pharmacy, documents
    """
    
    # ✅ Query the requests table (supports all service types)
    request = db.query(Request).filter(Request.request_id == body.request_id).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Verify access
    if current_user.user_id not in [request.customer_id, request.rider_id or 0]:
        raise HTTPException(status_code=403, detail="Access denied to this request")

    service = MessageService(db)
    convo = service.get_or_create_conversation(
        request_id=request.request_id,
        customer_id=request.customer_id,
        rider_id=request.rider_id,
    )
    
    return {"success": True, "data": {
        "conversation_id":   convo.conversation_id,
        "request_id":        convo.request_id,
        "conversation_type": convo.conversation_type,
        "status":            convo.status,
    }}


@router.post("/conversations/support")
def create_support_conversation(
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    if current_user.user_type != "customer":
        raise HTTPException(status_code=403, detail="Only customers can start support chats")

    service = MessageService(db)
    convo = service.create_support_conversation(current_user.user_id)
    return {"success": True, "data": {
        "conversation_id":   convo.conversation_id,
        "conversation_type": convo.conversation_type,
    }}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    service = MessageService(db)

    if not service.user_has_access(current_user.user_id, current_user.user_type, conversation_id):
        raise HTTPException(status_code=403, detail="Access denied")

    convo = service.get_conversation_by_id(conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = service.get_messages(conversation_id, limit=50)

    unread_ids = [m["message_id"] for m in messages if m["sender_id"] != current_user.user_id]
    if unread_ids:
        service.mark_messages_read(unread_ids, current_user.user_id)

    return {"success": True, "data": {"conversation": {
        "conversation_id":   convo.conversation_id,
        "request_id":        convo.request_id,
        "status":            convo.status,
        "conversation_type": convo.conversation_type,
    }, "messages": messages}}


@router.get("/conversations/{conversation_id}/messages")
def get_messages(
    conversation_id: int,
    limit: int = Query(default=50, le=100),
    before_message_id: Optional[int] = Query(default=None),
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    service = MessageService(db)

    if not service.user_has_access(current_user.user_id, current_user.user_type, conversation_id):
        raise HTTPException(status_code=403, detail="Access denied")

    messages = service.get_messages(conversation_id, limit=limit, before_message_id=before_message_id)
    return {"success": True, "data": messages}


@router.get("/conversations/{conversation_id}/unread")
def get_unread_count(
    conversation_id: int,
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    service = MessageService(db)

    if not service.user_has_access(current_user.user_id, current_user.user_type, conversation_id):
        raise HTTPException(status_code=403, detail="Access denied")

    count = service.get_unread_count(conversation_id, current_user.user_id)
    return {"success": True, "data": {"unread_count": count}}


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    service = MessageService(db)
    deleted = service.delete_message(message_id, current_user.user_id)
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    return {"success": True, "message": "Message deleted"}


@router.patch("/conversations/{conversation_id}/close")
def close_conversation(
    conversation_id: int,
    current_user = Depends(get_current_user),
    db: Session  = Depends(get_db),
):
    if current_user.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    service = MessageService(db)
    service.close_conversation(conversation_id)
    return {"success": True, "message": "Conversation closed"}