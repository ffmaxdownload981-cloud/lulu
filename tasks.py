import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

from database.crud import db_manager
from services.solana_service import solana_service
from services.helius_service import helius_service
from services.price_service import price_service
from services.risk_analyzer import risk_analyzer
from config import config

class BackgroundTasks:
    def __init__(self, application):
        self.application = application
        self.is_running = False
    
    async def start(self):
        """Start all background tasks"""
        self.is_running = True
        asyncio.create_task(self.wallet_monitor())
        asyncio.create_task(self.transaction_processor())
        asyncio.create_task(self.whale_detector())
        print("✅ Background tasks started")
    
    async def stop(self):
        """Stop all background tasks"""
        self.is_running = False
        print("🛑 Background tasks stopped")
    
    async def wallet_monitor(self):
        """Monitor tracked wallets for balance changes"""
        while self.is_running:
            try:
                # Get all active wallets
                wallets = db_manager.get_all_active_wallets()
                
                if not wallets:
                    await asyncio.sleep(config.CHECK_INTERVAL)
                    continue
                
                # Process in batches
                for i in range(0, len(wallets), config.BATCH_SIZE):
                    batch = wallets[i:i + config.BATCH_SIZE]
                    
                    # Check balances concurrently
                    tasks = [self.check_wallet_balance(wallet) for wallet in batch]
                    await asyncio.gather(*tasks)
                    
                    # Small delay between batches
                    await asyncio.sleep(2)
                
                # Wait before next check
                await asyncio.sleep(config.CHECK_INTERVAL)
                
            except Exception as e:
                print(f"Error in wallet monitor: {e}")
                await asyncio.sleep(10)
    
    async def check_wallet_balance(self, wallet):
        """Check individual wallet balance"""
        try:
            new_balance = await solana_service.get_balance(wallet.address)
            sol_price = await price_service.get_sol_price()
            new_balance_usd = new_balance * sol_price
            
            # Check for significant change (> 0.1 SOL)
            if abs(new_balance - wallet.balance) > 0.1:
                change = new_balance - wallet.balance
                change_usd = new_balance_usd - wallet.balance_usd
                
                # Send notification
                await self.send_balance_alert(
                    wallet.telegram_id,
                    wallet.user_id,
                    wallet.address,
                    new_balance,
                    new_balance_usd,
                    change,
                    change_usd
                )
                
                # Auto-track new wallets from transactions
                if change > 0:  # Received funds
                    await self.check_for_new_wallets(wallet.address)
            
            # Update database
            db_manager.update_wallet_balance(wallet.address, new_balance, new_balance_usd)
            
        except Exception as e:
            print(f"Error checking wallet {wallet.address}: {e}")
    
    async def transaction_processor(self):
        """Process new transactions"""
        while self.is_running:
            try:
                # Get unprocessed transactions
                transactions = db_manager.get_unprocessed_transactions()
                
                for tx in transactions:
                    try:
                        # Analyze transaction for whale movements
                        whale_alerts = await risk_analyzer.detect_whale_movements([tx])
                        
                        for alert in whale_alerts:
                            await self.send_whale_alert(alert)
                        
                        # Mark as processed
                        db_manager.mark_transaction_processed(tx.signature)
                        
                    except Exception as e:
                        print(f"Error processing transaction {tx.signature}: {e}")
                
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Error in transaction processor: {e}")
                await asyncio.sleep(10)
    
    async def whale_detector(self):
        """Detect whale movements across all tracked wallets"""
        while self.is_running:
            try:
                # Get all wallets
                wallets = db_manager.get_all_active_wallets()
                
                for wallet in wallets:
                    try:
                        # Get recent transactions
                        transactions = await helius_service.get_transactions(wallet.address, 10)
                        
                        # Check for whale movements
                        whale_alerts = await risk_analyzer.detect_whale_movements(transactions)
                        
                        for alert in whale_alerts:
                            await self.send_whale_alert(alert)
                            
                            # Auto-track new whale wallets
                            if alert.get('to') and alert['to'] != wallet.address:
                                await self.auto_track_wallet(alert['to'], "whale")
                        
                    except Exception as e:
                        print(f"Error checking whale movements for {wallet.address}: {e}")
                    
                    await asyncio.sleep(1)  # Rate limiting
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Error in whale detector: {e}")
                await asyncio.sleep(30)
    
    async def check_for_new_wallets(self, address: str):
        """Check transactions for new wallets to auto-track"""
        try:
            # Get recent transactions
            transactions = await helius_service.get_transactions(address, 5)
            
            for tx in transactions:
                # Extract new wallet addresses
                if 'native_transfer' in tx:
                    transfer = tx['native_transfer']
                    if transfer['from'] == address and transfer['to'] != address:
                        # Sending to new wallet
                        await self.auto_track_wallet(transfer['to'], "auto_track")
                
                if 'token_transfer' in tx:
                    transfer = tx['token_transfer']
                    if transfer['from'] == address and transfer['to'] != address:
                        await self.auto_track_wallet(transfer['to'], "auto_track")
                        
        except Exception as e:
            print(f"Error checking for new wallets: {e}")
    
    async def auto_track_wallet(self, address: str, source: str):
        """Automatically track a new wallet"""
        try:
            # Check if already tracked
            all_wallets = db_manager.get_all_active_wallets()
            if any(w.address == address for w in all_wallets):
                return
            
            # Find users tracking the source wallet
            # This would need to be implemented based on your needs
            
            print(f"🔍 Auto-track candidate: {address} from {source}")
            
        except Exception as e:
            print(f"Error auto-tracking wallet: {e}")
    
    async def send_balance_alert(self, telegram_id: int, user_id: str, address: str, 
                                 new_balance: float, new_balance_usd: float,
                                 change: float, change_usd: float):
        """Send balance change alert to user"""
        try:
            direction = "📈 Increased" if change > 0 else "📉 Decreased"
            
            message = (
                f"{direction} <b>Balance Alert</b>\n"
                f"Wallet: <code>{format_address(address)}</code>\n"
                f"New Balance: {new_balance:.4f} SOL ({format_usd(new_balance_usd)})\n"
                f"Change: {change:+.4f} SOL ({format_usd(abs(change_usd))})"
            )
            
            # Save notification
            db_manager.add_notification(
                telegram_id=telegram_id,
                user_id=user_id,
                message=message,
                notification_type='balance_alert',
                wallet_address=address
            )
            
            # Send to Telegram
            await self.application.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            print(f"Error sending balance alert: {e}")
    
    async def send_whale_alert(self, alert: Dict[str, Any]):
        """Send whale alert"""
        try:
            # Format message
            if alert.get('token') == 'SOL':
                message = (
                    f"🐋 <b>Whale Alert!</b>\n"
                    f"Amount: {alert['amount']:.2f} SOL\n"
                    f"Value: {format_usd(alert['amount_usd'])}\n"
                    f"From: <code>{format_address(alert['from'])}</code>\n"
                    f"To: <code>{format_address(alert['to'])}</code>\n"
                )
            else:
                message = (
                    f"🐋 <b>Whale Alert!</b>\n"
                    f"Token: {alert.get('token', 'Unknown')}\n"
                    f"Amount: {format_number(alert['amount'])}\n"
                    f"Value: {format_usd(alert['amount_usd'])}\n"
                    f"From: <code>{format_address(alert['from'])}</code>\n"
                    f"To: <code>{format_address(alert['to'])}</code>\n"
                )
            
            if alert.get('signature'):
                message += f"Tx: <code>{format_address(alert['signature'])}</code>"
            
            # Get all users (in a real implementation, you'd filter by preferences)
            # For now, just log it
            print(f"🐋 Whale Alert: {message}")
            
            # TODO: Send to relevant users based on their tracked wallets
            
        except Exception as e:
            print(f"Error sending whale alert: {e}")