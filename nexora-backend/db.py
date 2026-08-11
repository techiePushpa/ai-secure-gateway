"""
db.py — persistence layer for Nexora.

Works with any standard Postgres connection string (Neon, Render Postgres,
local Postgres, etc.) via DATABASE_URL. If DATABASE_URL isn't set, every
function here degrades gracefully — the API endpoints that need it will
report "Database Not Configured" instead of crashing, and the rest of the
gateway (chat, security pipeline, guest mode) keeps working exactly as
before with zero persistence.

Guests are intentionally never persisted here — only authenticated users
(a verified Auth0 token) get conversations saved. This matches the original
guest policy: guests get text chat but no chat sync across devices/sessions.

Neon specifically: copy the "Connection string" from your Neon project
dashboard (it already includes `sslmode=require`) and use it directly as
DATABASE_URL — no changes needed.
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

engine = None
SessionLocal = None
Base = declarative_base()

if DATABASE_URL:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    except Exception as e:
        print(f"[db] Failed to create engine: {e}")
        engine = None


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    auth0_sub = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255))
    name = Column(String(255))
    picture = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), default="New Chat")
    pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                             cascade="all, delete-orphan", order_by="Message.id")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")


def init_db():
    """Create tables if they don't exist yet. Safe to call on every startup."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)


def is_configured() -> bool:
    return engine is not None


def get_db():
    """FastAPI dependency. Yields a session, or None if no DATABASE_URL is set."""
    if SessionLocal is None:
        yield None
        return
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_or_create_user(session, user_claims: dict) -> "User":
    db_user = session.query(User).filter_by(auth0_sub=user_claims["sub"]).first()
    if db_user is None:
        db_user = User(
            auth0_sub=user_claims["sub"],
            email=user_claims.get("email"),
            name=user_claims.get("name"),
            picture=user_claims.get("picture"),
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    else:
        # Keep the profile fresh in case name/picture changed on Auth0's side.
        db_user.email = user_claims.get("email") or db_user.email
        db_user.name = user_claims.get("name") or db_user.name
        db_user.picture = user_claims.get("picture") or db_user.picture
        session.commit()
    return db_user


def persist_turn(session, user_claims: dict, conversation_id, user_text: str, assistant_text: str, blocked: bool):
    """Save one user+assistant exchange. Creates a conversation if conversation_id
    is missing/invalid. Returns the conversation id, or None if persistence
    isn't available (no DB configured, or no authenticated user)."""
    if session is None or user_claims is None:
        return None
    db_user = get_or_create_user(session, user_claims)

    conv = None
    if conversation_id:
        conv = session.query(Conversation).filter_by(id=conversation_id, user_id=db_user.id).first()
    if conv is None:
        title = user_text[:42] + ("…" if len(user_text) > 42 else "")
        conv = Conversation(user_id=db_user.id, title=title or "New Chat")
        session.add(conv)
        session.commit()
        session.refresh(conv)

    session.add(Message(conversation_id=conv.id, role="user", content=user_text))
    session.add(Message(conversation_id=conv.id, role="assistant", content=assistant_text, blocked=blocked))
    conv.updated_at = func.now()
    session.commit()
    return conv.id
