from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum, 
    Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id   = Column(Integer, primary_key=True, autoincrement=True)
    request_id        = Column(Integer, ForeignKey("requests.request_id", ondelete="SET NULL"), nullable=True, unique=True)
    customer_id       = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    rider_id          = Column(Integer, ForeignKey("riders.rider_id", ondelete="SET NULL"), nullable=True)
    admin_id          = Column(Integer, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    conversation_type = Column(Enum("request_chat", "support_chat"), default="request_chat")
    status            = Column(Enum("active", "closed", "archived"), default="active")
    last_message_at   = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages          = relationship("Message", back_populates="conversation", cascade="all, delete")


class Message(Base):
    __tablename__ = "messages"

    message_id      = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    sender_id       = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    sender_type     = Column(Enum("customer", "rider", "admin"), nullable=False)
    message_type    = Column(Enum("text", "image", "file", "system"), default="text")
    content         = Column(Text, nullable=True)
    attachment_url  = Column(String(500), nullable=True)
    attachment_type = Column(String(50), nullable=True)
    is_deleted      = Column(Boolean, default=False)
    deleted_at      = Column(DateTime, nullable=True)
    sent_at         = Column(DateTime, default=datetime.utcnow)
    created_at      = Column(DateTime, default=datetime.utcnow)

    conversation    = relationship("Conversation", back_populates="messages")
    read_receipts   = relationship("MessageReadReceipt", back_populates="message", cascade="all, delete")


class MessageReadReceipt(Base):
    __tablename__ = "message_read_receipts"

    receipt_id  = Column(Integer, primary_key=True, autoincrement=True)
    message_id  = Column(Integer, ForeignKey("messages.message_id", ondelete="CASCADE"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    read_at     = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_message_user"),)

    message     = relationship("Message", back_populates="read_receipts")


class WebSocketConnection(Base):
    __tablename__ = "websocket_connections"

    connection_id   = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    socket_id       = Column(String(255), unique=True, nullable=False)
    device_type     = Column(Enum("mobile", "web", "desktop"), default="mobile")
    is_connected    = Column(Boolean, default=True)
    connected_at    = Column(DateTime, default=datetime.utcnow)
    disconnected_at = Column(DateTime, nullable=True)
    last_ping_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TypingIndicator(Base):
    __tablename__ = "typing_indicators"

    indicator_id    = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    is_typing       = Column(Boolean, default=True)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_convo_user_typing"),)