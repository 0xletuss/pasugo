from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models.messaging_models import (
    Conversation, Message, MessageReadReceipt,
    WebSocketConnection, TypingIndicator
)


class MessageService:
    def __init__(self, db: Session):
        self.db = db

    # ── Conversations ──────────────────────────────────────────

    def get_or_create_conversation(
        self,
        request_id: int,
        customer_id: int,
        rider_id: Optional[int] = None
    ) -> Conversation:
        convo = self.db.query(Conversation).filter(
            Conversation.request_id == request_id
        ).first()

        if convo:
            return convo

        convo = Conversation(
            request_id=request_id,
            customer_id=customer_id,
            rider_id=rider_id,
            conversation_type="request_chat",
            status="active"
        )
        self.db.add(convo)
        self.db.commit()
        self.db.refresh(convo)
        return convo

    def create_support_conversation(self, customer_id: int) -> Conversation:
        convo = Conversation(
            customer_id=customer_id,
            conversation_type="support_chat",
            status="active"
        )
        self.db.add(convo)
        self.db.commit()
        self.db.refresh(convo)
        return convo

    def get_user_conversations(self, user_id: int, user_type: str) -> list:
        """Get all active conversations with last message + unread count + other user name."""
        from models.user import User
        from models.rider import Rider

        query = self.db.query(Conversation).filter(
            Conversation.status != "archived"
        )

        if user_type == "customer":
            query = query.filter(Conversation.customer_id == user_id)
        elif user_type == "rider":
            query = query.join(Rider, Rider.rider_id == Conversation.rider_id).filter(
                Rider.user_id == user_id
            )

        conversations = query.order_by(Conversation.last_message_at.desc()).all()

        result = []
        for convo in conversations:
            last_msg = (
                self.db.query(Message)
                .filter(
                    Message.conversation_id == convo.conversation_id,
                    Message.is_deleted == False
                )
                .order_by(Message.sent_at.desc())
                .first()
            )

            unread = (
                self.db.query(func.count(Message.message_id))
                .outerjoin(
                    MessageReadReceipt,
                    and_(
                        MessageReadReceipt.message_id == Message.message_id,
                        MessageReadReceipt.user_id == user_id
                    )
                )
                .filter(
                    Message.conversation_id == convo.conversation_id,
                    Message.sender_id != user_id,
                    Message.is_deleted == False,
                    MessageReadReceipt.receipt_id == None
                )
                .scalar()
            )

            # Resolve the OTHER user's name
            other_user_name = None
            if user_type == "customer" and convo.rider_id:
                rider = self.db.query(Rider).filter(Rider.rider_id == convo.rider_id).first()
                if rider:
                    rider_user = self.db.query(User).filter(User.user_id == rider.user_id).first()
                    if rider_user:
                        other_user_name = rider_user.full_name
            elif user_type == "rider" and convo.customer_id:
                customer = self.db.query(User).filter(User.user_id == convo.customer_id).first()
                if customer:
                    other_user_name = customer.full_name

            result.append({
                "conversation_id":   convo.conversation_id,
                "request_id":        convo.request_id,
                "customer_id":       convo.customer_id,
                "rider_id":          convo.rider_id,
                "conversation_type": convo.conversation_type,
                "status":            convo.status,
                "last_message_at":   convo.last_message_at.isoformat() if convo.last_message_at else None,
                "unread_count":      unread or 0,
                "last_message":      last_msg.content if last_msg else None,
                "other_user_name":   other_user_name,
            })

        return result

    def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id
        ).first()

    def update_last_message_at(self, conversation_id: int):
        convo = self.get_conversation_by_id(conversation_id)
        if convo:
            convo.last_message_at = datetime.utcnow()
            self.db.commit()

    def assign_rider(self, conversation_id: int, rider_id: int):
        convo = self.get_conversation_by_id(conversation_id)
        if convo:
            convo.rider_id = rider_id
            self.db.commit()

    def close_conversation(self, conversation_id: int, status: str = "closed"):
        convo = self.get_conversation_by_id(conversation_id)
        if convo:
            convo.status = status
            self.db.commit()

    def user_has_access(self, user_id: int, user_type: str, conversation_id: int) -> bool:
        convo = self.get_conversation_by_id(conversation_id)
        if not convo:
            return False
        
        # Normalize user_type (handle both "UserType.customer" and "customer" formats)
        normalized_type = user_type.lower()
        if "customer" in normalized_type:
            normalized_type = "customer"
        elif "rider" in normalized_type:
            normalized_type = "rider"
        elif "admin" in normalized_type:
            normalized_type = "admin"
        
        if normalized_type == "admin":
            return True
        if normalized_type == "customer":
            return convo.customer_id == user_id
        if normalized_type == "rider":
            from models.rider import Rider
            rider = self.db.query(Rider).filter(Rider.user_id == user_id).first()
            return rider is not None and convo.rider_id == rider.rider_id
        return False

    # ── Messages ───────────────────────────────────────────────

    def create_message(
        self,
        conversation_id: int,
        sender_id: int,
        sender_type: str,
        message_type: str = "text",
        content: Optional[str] = None,
        attachment_url: Optional[str] = None,
        attachment_type: Optional[str] = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_type=sender_type,
            message_type=message_type,
            content=content,
            attachment_url=attachment_url,
            attachment_type=attachment_type,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        self.update_last_message_at(conversation_id)
        return msg

    def get_messages(
        self,
        conversation_id: int,
        limit: int = 50,
        before_message_id: Optional[int] = None
    ) -> list:
        query = self.db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        if before_message_id:
            query = query.filter(Message.message_id < before_message_id)

        messages = query.order_by(Message.sent_at.desc()).limit(limit).all()
        messages.reverse()

        return [self._serialize_message(m) for m in messages]

    def delete_message(self, message_id: int, user_id: int) -> bool:
        msg = self.db.query(Message).filter(
            Message.message_id == message_id,
            Message.sender_id == user_id
        ).first()
        if not msg:
            return False
        msg.is_deleted = True
        msg.deleted_at = datetime.utcnow()
        self.db.commit()
        return True

    def _serialize_message(self, msg: Message) -> dict:
        return {
            "message_id":      msg.message_id,
            "conversation_id": msg.conversation_id,
            "sender_id":       msg.sender_id,
            "sender_type":     msg.sender_type,
            "message_type":    msg.message_type,
            "content":         msg.content,
            "attachment_url":  msg.attachment_url,
            "attachment_type": msg.attachment_type,
            "sent_at":         msg.sent_at.isoformat() if msg.sent_at else None,
        }

    # ── Read Receipts ──────────────────────────────────────────

    def mark_messages_read(self, message_ids: list[int], user_id: int):
        for message_id in message_ids:
            exists_check = self.db.query(MessageReadReceipt).filter(
                MessageReadReceipt.message_id == message_id,
                MessageReadReceipt.user_id == user_id
            ).first()
            if not exists_check:
                receipt = MessageReadReceipt(message_id=message_id, user_id=user_id)
                self.db.add(receipt)
        self.db.commit()

    def get_unread_count(self, conversation_id: int, user_id: int) -> int:
        return (
            self.db.query(func.count(Message.message_id))
            .outerjoin(
                MessageReadReceipt,
                and_(
                    MessageReadReceipt.message_id == Message.message_id,
                    MessageReadReceipt.user_id == user_id
                )
            )
            .filter(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_deleted == False,
                MessageReadReceipt.receipt_id == None
            )
            .scalar() or 0
        )

    # ── WebSocket Presence ─────────────────────────────────────

    def register_connection(self, user_id: int, socket_id: str, device_type: str = "mobile"):
        existing = self.db.query(WebSocketConnection).filter(
            WebSocketConnection.socket_id == socket_id
        ).first()
        if existing:
            existing.is_connected = True
            existing.connected_at = datetime.utcnow()
            existing.disconnected_at = None
        else:
            conn = WebSocketConnection(
                user_id=user_id,
                socket_id=socket_id,
                device_type=device_type,
                is_connected=True
            )
            self.db.add(conn)
        self.db.commit()

    def deregister_connection(self, socket_id: str):
        conn = self.db.query(WebSocketConnection).filter(
            WebSocketConnection.socket_id == socket_id
        ).first()
        if conn:
            conn.is_connected = False
            conn.disconnected_at = datetime.utcnow()
            self.db.commit()

    def is_user_online(self, user_id: int) -> bool:
        return self.db.query(WebSocketConnection).filter(
            WebSocketConnection.user_id == user_id,
            WebSocketConnection.is_connected == True
        ).count() > 0

    # ── Typing Indicators ─────────────────────────────────────

    def set_typing_status(self, conversation_id: int, user_id: int, is_typing: bool):
        indicator = self.db.query(TypingIndicator).filter(
            TypingIndicator.conversation_id == conversation_id,
            TypingIndicator.user_id == user_id
        ).first()
        if indicator:
            indicator.is_typing = is_typing
            indicator.updated_at = datetime.utcnow()
        else:
            indicator = TypingIndicator(
                conversation_id=conversation_id,
                user_id=user_id,
                is_typing=is_typing
            )
            self.db.add(indicator)
        self.db.commit()