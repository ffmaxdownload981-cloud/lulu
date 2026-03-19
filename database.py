from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from datetime import datetime
from typing import Optional, List, Dict, Any

from .models import Base, User, Wallet, Transaction, Token, TokenHolder, Notification
from config import config

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(
            config.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    # User operations
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        session = self.get_session()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    # Wallet operations
    def add_wallet(self, telegram_id: int, user_id: str, address: str, label: str = None) -> Wallet:
        session = self.get_session()
        try:
            existing = session.query(Wallet).filter_by(address=address).first()
            if existing:
                if existing.user_id != user_id:
                    raise Exception("Wallet already tracked by another user")
                return existing
            
            wallet = Wallet(
                address=address,
                label=label,
                user_id=user_id,
                telegram_id=telegram_id
            )
            session.add(wallet)
            session.commit()
            return wallet
        finally:
            session.close()
    
    def get_user_wallets(self, user_id: str) -> List[Wallet]:
        session = self.get_session()
        try:
            return session.query(Wallet).filter_by(user_id=user_id, is_active=True).all()
        finally:
            session.close()
    
    def get_all_active_wallets(self) -> List[Wallet]:
        session = self.get_session()
        try:
            return session.query(Wallet).filter_by(is_active=True).all()
        finally:
            session.close()
    
    def update_wallet_balance(self, address: str, balance: float, balance_usd: float):
        session = self.get_session()
        try:
            wallet = session.query(Wallet).filter_by(address=address).first()
            if wallet:
                wallet.balance = balance
                wallet.balance_usd = balance_usd
                wallet.last_checked = datetime.utcnow()
                session.commit()
        finally:
            session.close()
    
    def remove_wallet(self, user_id: str, address: str):
        session = self.get_session()
        try:
            wallet = session.query(Wallet).filter_by(
                user_id=user_id, address=address
            ).first()
            if wallet:
                wallet.is_active = False
                session.commit()
        finally:
            session.close()
    
    # Transaction operations
    def add_transaction(self, transaction_data: Dict[str, Any]) -> Transaction:
        session = self.get_session()
        try:
            existing = session.query(Transaction).filter_by(
                signature=transaction_data['signature']
            ).first()
            if existing:
                return existing
            
            transaction = Transaction(**transaction_data)
            session.add(transaction)
            session.commit()
            return transaction
        finally:
            session.close()
    
    def get_unprocessed_transactions(self) -> List[Transaction]:
        session = self.get_session()
        try:
            return session.query(Transaction)\
                .filter_by(is_processed=False)\
                .order_by(Transaction.timestamp)\
                .limit(100)\
                .all()
        finally:
            session.close()
    
    def mark_transaction_processed(self, signature: str):
        session = self.get_session()
        try:
            transaction = session.query(Transaction).filter_by(signature=signature).first()
            if transaction:
                transaction.is_processed = True
                session.commit()
        finally:
            session.close()
    
    # Token operations
    def update_token_info(self, token_data: Dict[str, Any]) -> Token:
        session = self.get_session()
        try:
            token = session.query(Token).filter_by(address=token_data['address']).first()
            if not token:
                token = Token(**token_data)
                session.add(token)
            else:
                for key, value in token_data.items():
                    setattr(token, key, value)
                token.last_updated = datetime.utcnow()
            
            session.commit()
            return token
        finally:
            session.close()
    
    def get_token(self, address: str) -> Optional[Token]:
        session = self.get_session()
        try:
            return session.query(Token).filter_by(address=address).first()
        finally:
            session.close()
    
    # Notification operations
    def add_notification(self, telegram_id: int, user_id: str, message: str, 
                        notification_type: str, wallet_address: str = None, 
                        token_address: str = None) -> Notification:
        session = self.get_session()
        try:
            notification = Notification(
                user_id=user_id,
                telegram_id=telegram_id,
                wallet_address=wallet_address,
                token_address=token_address,
                notification_type=notification_type,
                message=message
            )
            session.add(notification)
            session.commit()
            return notification
        finally:
            session.close()

db_manager = DatabaseManager()