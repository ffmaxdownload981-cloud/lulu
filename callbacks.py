from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import asyncio

from database.crud import db_manager
from services.solana_service import solana_service
from services.helius_service import helius_service
from services.price_service import price_service
from services.risk_analyzer import risk_analyzer
from utils.helpers import (
    is_valid_solana_address, format_address, format_number,
    format_usd, get_risk_emoji, format_timestamp
)
from utils.constants import ERROR_MESSAGES

class CallbackHandlers:
    def __init__(self, application):
        self.application = application
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all callback query handlers"""
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all callback queries"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        try:
            if data.startswith("bal_"):
                address = data[4:]
                await self.show_balance(query, address)
            
            elif data.startswith("track_"):
                address = data[6:]
                await self.track_wallet(query, address)
            
            elif data.startswith("tx_"):
                address = data[3:]
                await self.show_transactions(query, address)
            
            elif data.startswith("check_"):
                address = data[6:]
                await self.check_token(query, address)
            
            elif data.startswith("holders_"):
                token = data[8:]
                await self.show_holders(query, token)
            
            elif data.startswith("price_"):
                token = data[6:]
                await self.show_price(query, token)
            
            elif data.startswith("refresh_"):
                token = data[8:]
                await self.refresh_token(query, token)
            
            elif data == "cancel":
                await query.edit_message_text("❌ Action cancelled.")
            
            elif data == "back":
                await query.edit_message_text("🔙 Going back...")
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_balance(self, query, address: str):
        """Show wallet balance from callback"""
        try:
            # Get SOL balance
            sol_balance = await solana_service.get_balance(address)
            sol_price = await price_service.get_sol_price()
            sol_usd = sol_balance * sol_price
            
            # Get token balances
            token_accounts = await solana_service.get_token_accounts(address)
            
            message = f"💰 <b>Wallet Balance</b>\n"
            message += f"<code>{address}</code>\n\n"
            message += f"<b>SOL:</b> {sol_balance:.4f} ({format_usd(sol_usd)})\n\n"
            
            if token_accounts:
                message += "<b>Tokens:</b>\n"
                valid_tokens = [t for t in token_accounts if t['amount'] and t['amount'] > 0]
                
                for token in valid_tokens[:10]:
                    message += f"• {token['amount']:.4f} (Token: {format_address(token['mint'])})\n"
                
                if len(valid_tokens) > 10:
                    message += f"\n... and {len(valid_tokens) - 10} more tokens"
            else:
                message += "No token balances found"
            
            # Add refresh button
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"bal_{address}")],
                [InlineKeyboardButton("◀️ Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message, 
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def track_wallet(self, query, address: str):
        """Track wallet from callback"""
        user = query.from_user
        
        try:
            # Check user wallet limit
            db_user = db_manager.get_or_create_user(telegram_id=user.id)
            user_wallets = db_manager.get_user_wallets(user_id=db_user.id)
            
            if len(user_wallets) >= 100:
                await query.edit_message_text(ERROR_MESSAGES["max_wallets"])
                return
            
            # Add wallet to database
            wallet = db_manager.add_wallet(
                telegram_id=user.id,
                user_id=db_user.id,
                address=address
            )
            
            # Get initial balance
            balance = await solana_service.get_balance(address)
            sol_price = await price_service.get_sol_price()
            balance_usd = balance * sol_price
            
            db_manager.update_wallet_balance(address, balance, balance_usd)
            
            message = (
                f"✅ Successfully tracking wallet:\n"
                f"<code>{format_address(address)}</code>\n"
                f"Balance: {balance:.4f} SOL ({format_usd(balance_usd)})"
            )
            
            await query.edit_message_text(message, parse_mode='HTML')
            
        except Exception as e:
            if "already tracked" in str(e):
                await query.edit_message_text(ERROR_MESSAGES["already_tracking"])
            else:
                await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_transactions(self, query, address: str):
        """Show recent transactions from callback"""
        try:
            await query.edit_message_text("🔍 Fetching transactions...")
            
            # Get transactions from Helius
            transactions = await helius_service.get_transactions(address, 10)
            
            if not transactions:
                await query.edit_message_text("No recent transactions found")
                return
            
            message = f"📊 <b>Recent Transactions</b>\n"
            message += f"<code>{format_address(address)}</code>\n\n"
            
            for i, tx in enumerate(transactions[:10], 1):
                tx_type = tx.get('type', 'UNKNOWN')
                timestamp = tx.get('timestamp')
                
                message += f"{i}. <b>{tx_type}</b>\n"
                if timestamp:
                    message += f"   Time: {format_timestamp(timestamp)}\n"
                
                if 'native_transfer' in tx:
                    transfer = tx['native_transfer']
                    message += f"   💸 {transfer['amount']:.4f} SOL\n"
                elif 'token_transfer' in tx:
                    transfer = tx['token_transfer']
                    message += f"   💸 {transfer['amount']} {transfer['symbol']}\n"
                
                message += f"   Signature: <code>{format_address(tx.get('signature', ''))}</code>\n\n"
            
            # Add refresh button
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"tx_{address}")],
                [InlineKeyboardButton("◀️ Back", callback_data="back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def check_token(self, query, token_address: str):
        """Check token from callback"""
        try:
            await query.edit_message_text("🔍 Analyzing token...")
            
            # Analyze token
            analysis = await risk_analyzer.analyze_token(token_address)
            
            if "error" in analysis:
                await query.edit_message_text(f"❌ {analysis['error']}")
                return
            
            # Format message
            risk_emoji = get_risk_emoji(analysis['risk_level'])
            
            message = f"{risk_emoji} <b>Token Risk Analysis</b>\n\n"
            message += f"<b>Token:</b> {analysis['symbol']} ({analysis['name']})\n"
            message += f"<b>Address:</b> <code>{format_address(analysis['token_address'])}</code>\n\n"
            
            message += f"<b>Risk Score:</b> {analysis['risk_score']}/100\n"
            message += f"<b>Risk Level:</b> {analysis['risk_level']}\n\n"
            
            if analysis['risk_factors']:
                message += "<b>Risk Factors:</b>\n"
                for factor in analysis['risk_factors']:
                    message += f"• {factor}\n"
                message += "\n"
            
            message += f"<b>Holders:</b> {analysis['holder_count']:,}\n"
            
            if analysis['price_usd']:
                message += f"<b>Price:</b> ${analysis['price_usd']:.8f}\n"
            
            if analysis['liquidity_usd']:
                message += f"<b>Liquidity:</b> {format_usd(analysis['liquidity_usd'])}\n"
            
            if analysis['volume_24h']:
                message += f"<b>24h Volume:</b> {format_usd(analysis['volume_24h'])}\n"
            
            # Add buttons
            keyboard = [
                [
                    InlineKeyboardButton("📊 Holders", callback_data=f"holders_{token_address}"),
                    InlineKeyboardButton("💰 Price", callback_data=f"price_{token_address}")
                ],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{token_address}")]
            ]
            
            if analysis.get('dex_url'):
                keyboard.insert(0, [InlineKeyboardButton("📈 View on DexScreener", url=analysis['dex_url'])])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_holders(self, query, token_address: str):
        """Show top holders from callback"""
        try:
            await query.edit_message_text("🔍 Fetching holders...")
            
            holders = await solscan_service.get_token_holders(token_address, limit=50)
            
            if not holders:
                await query.edit_message_text("No holder data found")
                return
            
            # Calculate total supply
            total_supply = sum([h.get('amount', 0) for h in holders])
            
            message = f"📊 <b>Top Token Holders</b>\n"
            message += f"<code>{format_address(token_address)}</code>\n\n"
            
            for i, holder in enumerate(holders[:10], 1):
                amount = holder.get('amount', 0)
                percentage = (amount / total_supply * 100) if total_supply > 0 else 0
                address = holder.get('owner', 'Unknown')
                
                message += f"{i}. <code>{format_address(address)}</code>\n"
                message += f"   {format_number(amount)} ({percentage:.2f}%)\n\n"
            
            # Add buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Analyze", callback_data=f"check_{token_address}"),
                    InlineKeyboardButton("💰 Price", callback_data=f"price_{token_address}")
                ],
                [InlineKeyboardButton("◀️ Back", callback_data=f"check_{token_address}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def show_price(self, query, token_address: str):
        """Show token price from callback"""
        try:
            await query.edit_message_text("💰 Fetching price data...")
            
            price_data = await price_service.get_token_price(token_address)
            
            if not price_data or not price_data.get('price_usd'):
                await query.edit_message_text("Price data not found")
                return
            
            message = f"💰 <b>Token Price</b>\n"
            message += f"<code>{format_address(token_address)}</code>\n\n"
            message += f"<b>Price:</b> ${price_data['price_usd']:.8f}\n"
            
            if price_data.get('price_sol'):
                message += f"<b>Price in SOL:</b> {price_data['price_sol']:.8f} SOL\n"
            
            if price_data.get('price_change_24h'):
                change = price_data['price_change_24h']
                emoji = "📈" if change > 0 else "📉"
                message += f"<b>24h Change:</b> {emoji} {change:.2f}%\n"
            
            if price_data.get('liquidity_usd'):
                message += f"<b>Liquidity:</b> {format_usd(price_data['liquidity_usd'])}\n"
            
            if price_data.get('volume_24h'):
                message += f"<b>24h Volume:</b> {format_usd(price_data['volume_24h'])}\n"
            
            message += f"<b>Source:</b> {price_data.get('source', 'Unknown')}\n"
            
            # Add buttons
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Analyze", callback_data=f"check_{token_address}"),
                    InlineKeyboardButton("📊 Holders", callback_data=f"holders_{token_address}")
                ],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"price_{token_address}")]
            ]
            
            if price_data.get('url'):
                keyboard.insert(0, [InlineKeyboardButton("📈 View Chart", url=price_data['url'])])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def refresh_token(self, query, token_address: str):
        """Refresh token analysis"""
        await self.check_token(query, token_address)