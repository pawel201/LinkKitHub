from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

# 1. CREATORS MODEL
class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    instagram_handle = Column(String(100), unique=True, nullable=True)
    is_active_subscription = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

# 2. AUTODM RULES MODEL
class AutoDMRule(Base):
    __tablename__ = "autodm_rules"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"))
    trigger_keyword = Column(String(50), nullable=False)
    reply_message = Column(Text, nullable=False)  # Capital 'Text' use kiya hai
    is_enabled = Column(Boolean, default=True)
    total_triggers_sent = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())