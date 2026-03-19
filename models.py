from sqlalchemy import create_engine, Column, String, BigInteger, Boolean, DateTime, Float, JSON, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default={})

class Wallet(Base):
    __tablename__ = 'wallets'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String, unique=True, nullable=False)
    label = Column(String)
    user_id = Column(String, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    balance = Column(Float, default=0)
    balance_usd = Column(Float, default=0)

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    signature = Column(String, unique=True, nullable=False)
    wallet_address = Column(String, nullable=False)
    from_address = Column(String, nullable=False)
    to_address = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    amount_usd = Column(Float)
    token_address = Column(String)
    token_symbol = Column(String)
    timestamp = Column(DateTime, nullable=False)
    transaction_type = Column(String)
    is_processed = Column(Boolean, default=False)

class Token(Base):
    __tablename__ = 'tokens'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    address = Column(String, unique=True, nullable=False)
    symbol = Column(String)
    name = Column(String)
    decimals = Column(Integer)
    total_supply = Column(Float)
    holders_count = Column(Integer)
    market_cap = Column(Float)
    volume_24h = Column(Float)
    price = Column(Float)
    price_change_24h = Column(Float)
    is_verified = Column(Boolean, default=False)
    risk_score = Column(Float)
    risk_factors = Column(JSON, default=[])
    last_updated = Column(DateTime, default=datetime.utcnow)

class TokenHolder(Base):
    __tablename__ = 'token_holders'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token_address = Column(String, nullable=False)
    holder_address = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    percentage = Column(Float)
    rank = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    wallet_address = Column(String)
    token_address = Column(String)
    notification_type = Column(String)
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)