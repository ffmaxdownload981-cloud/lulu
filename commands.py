from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from datetime import datetime
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
from utils.constants import HELP_TEXT, WELCOME_TEXT, ERROR_MESSAGES

class CommandHandlers:
    def __init__(self, application):
        self.application = application
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup all command handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("track", self.track_wallet))
        self.application.add_handler(CommandHandler("untrack", self.untrack_wallet))
        self.application.add_handler(CommandHandler("list", self.list_wallets))
        self.application.add_handler(CommandHandler("balance", self.get_balance))
        self.application.add_handler(CommandHandler("transactions", self.get_transactions))
        self.application.add_handler(CommandHandler("check", self.check_token))
        self.application.add_handler(CommandHandler("holders", self.get_holders))
        self.application.add_handler(CommandHandler("price", self.get_price))
        self.application.add_handler(CommandHandler("search", self.search_token))
        self.application.add_handler(CommandHandler("whales", self.get_whale_alerts))
        self.application.add_handler(CommandHandler("trending", self.get_trending))
        self.application.add_handler(CommandHandler("stats", self.get_stats))
        
        # Message handler for wallet addresses
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        
        # Save user to database
        db_manager.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        await update.message.reply_text(
            WELCOME_TEXT.format(name=user.first_name),
            parse_mode='HTML'
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        await update.message.reply_text(HELP_TEXT, parse_mode='HTML')
    
    async def track_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Track a wallet address"""
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a wallet address to track.\n"
                "Example: /track <wallet_address> [label]"
            )
            return
        
        address = context.args[0]
        label = ' '.join(context.args[1:]) if len(context.args) > 1 else None
        
        # Validate address
        if not is_valid_solana_address(address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
        # Check user wallet limit
        db_user = db_manager.get_or_create_user(telegram_id=user.id)
        user_wallets = db_manager.get_user_wallets(user_id=db_user.id)
        
        if len(user_wallets) >= 100:
            await update.message.reply_text(ERROR_MESSAGES["max_wallets"])
            return
        
        try:
            # Add wallet to database
            wallet = db_manager.add_wallet(
                telegram_id=user.id,
                user_id=db_user.id,
                address=address,
                label=label
            )
            
            # Get initial balance
            balance = await solana_service.get_balance(address)
            sol_price = await price_service.get_sol_price()
            balance_usd = balance * sol_price
            
            db_manager.update_wallet_balance(address, balance, balance_usd)
            
            message = (
                f"✅ Successfully tracking wallet:\n"
                f"<code>{format_address(address)}</code>\n"
                f"Label: {label or 'Not set'}\n"
                f"Balance: {balance:.4f} SOL ({format_usd(balance_usd)})"
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            if "already tracked" in str(e):
                await update.message.reply_text(ERROR_MESSAGES["already_tracking"])
            else:
                await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def untrack_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop tracking a wallet"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a wallet address to stop tracking.\n"
                "Example: /untrack <wallet_address>"
            )
            return
        
        address = context.args[0]
        user = update.effective_user
        
        try:
            db_user = db_manager.get_or_create_user(telegram_id=user.id)
            db_manager.remove_wallet(user_id=db_user.id, address=address)
            
            await update.message.reply_text(
                f"✅ Stopped tracking wallet: <code>{format_address(address)}</code>",
                parse_mode='HTML'
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def list_wallets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List all tracked wallets"""
        user = update.effective_user
        
        db_user = db_manager.get_or_create_user(telegram_id=user.id)
        wallets = db_manager.get_user_wallets(user_id=db_user.id)
        
        if not wallets:
            await update.message.reply_text(
                "You're not tracking any wallets yet.\n"
                "Use /track <address> to start tracking."
            )
            return
        
        message = "📋 <b>Your Tracked Wallets:</b>\n\n"
        for i, wallet in enumerate(wallets, 1):
            label = f" ({wallet.label})" if wallet.label else ""
            message += f"{i}. <code>{format_address(wallet.address)}</code>{label}\n"
            message += f"   Balance: {wallet.balance:.4f} SOL ({format_usd(wallet.balance_usd)})\n"
            message += f"   Added: {wallet.added_at.strftime('%Y-%m-%d')}\n\n"
        
        # Split message if too long
        if len(message) > 4000:
            for chunk in [message[i:i+4000] for i in range(0, len(message), 4000)]:
                await update.message.reply_text(chunk, parse_mode='HTML')
        else:
            await update.message.reply_text(message, parse_mode='HTML')
    
    async def get_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get balance for a wallet"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a wallet address.\n"
                "Example: /balance <wallet_address>"
            )
            return
        
        address = context.args[0]
        
        if not is_valid_solana_address(address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
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
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def get_transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get recent transactions for a wallet"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a wallet address.\n"
                "Example: /transactions <wallet_address> [limit]"
            )
            return
        
        address = context.args[0]
        limit = int(context.args[1]) if len(context.args) > 1 else 10
        limit = min(limit, 50)
        
        if not is_valid_solana_address(address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
        try:
            await update.message.reply_text("🔍 Fetching transactions...")
            
            # Get transactions from Helius
            transactions = await helius_service.get_transactions(address, limit)
            
            if not transactions:
                await update.message.reply_text("No recent transactions found")
                return
            
            message = f"📊 <b>Recent Transactions</b>\n"
            message += f"<code>{format_address(address)}</code>\n\n"
            
            for i, tx in enumerate(transactions[:limit], 1):
                tx_type = tx.get('type', 'UNKNOWN')
                timestamp = tx.get('timestamp')
                
                message += f"{i}. <b>{tx_type}</b>\n"
                if timestamp:
                    message += f"   Time: {format_timestamp(timestamp)}\n"
                
                # Add transfer info
                if 'native_transfer' in tx:
                    transfer = tx['native_transfer']
                    message += f"   💸 {transfer['amount']:.4f} SOL\n"
                elif 'token_transfer' in tx:
                    transfer = tx['token_transfer']
                    message += f"   💸 {transfer['amount']} {transfer['symbol']}\n"
                
                message += f"   Signature: <code>{format_address(tx.get('signature', ''))}</code>\n\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def check_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check token risk and information"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token contract address.\n"
                "Example: /check <token_address>"
            )
            return
        
        token_address = context.args[0]
        
        if not is_valid_solana_address(token_address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
        try:
            await update.message.reply_text("🔍 Analyzing token... This may take a few seconds.")
            
            # Analyze token
            analysis = await risk_analyzer.analyze_token(token_address)
            
            if "error" in analysis:
                await update.message.reply_text(f"❌ {analysis['error']}")
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
            
            if analysis.get('dex_url'):
                keyboard = [[InlineKeyboardButton("📊 View on DexScreener", url=analysis['dex_url'])]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def get_holders(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get top token holders"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token address.\n"
                "Example: /holders <token_address> [limit]"
            )
            return
        
        token_address = context.args[0]
        limit = int(context.args[1]) if len(context.args) > 1 else 10
        limit = min(limit, 50)
        
        if not is_valid_solana_address(token_address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
        try:
            await update.message.reply_text("🔍 Fetching holders...")
            
            holders = await solscan_service.get_token_holders(token_address, limit=100)
            
            if not holders:
                await update.message.reply_text("No holder data found")
                return
            
            # Calculate total supply
            total_supply = sum([h.get('amount', 0) for h in holders])
            
            message = f"📊 <b>Top {limit} Token Holders</b>\n"
            message += f"<code>{format_address(token_address)}</code>\n\n"
            
            for i, holder in enumerate(holders[:limit], 1):
                amount = holder.get('amount', 0)
                percentage = (amount / total_supply * 100) if total_supply > 0 else 0
                address = holder.get('owner', 'Unknown')
                
                message += f"{i}. <code>{format_address(address)}</code>\n"
                message += f"   {format_number(amount)} ({percentage:.2f}%)\n\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def get_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get token price"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token address.\n"
                "Example: /price <token_address>"
            )
            return
        
        token_address = context.args[0]
        
        if not is_valid_solana_address(token_address):
            await update.message.reply_text(ERROR_MESSAGES["invalid_address"])
            return
        
        try:
            price_data = await price_service.get_token_price(token_address)
            
            if not price_data or not price_data.get('price_usd'):
                await update.message.reply_text("Price data not found")
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
            
            if price_data.get('url'):
                keyboard = [[InlineKeyboardButton("📊 View Chart", url=price_data['url'])]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
            else:
                await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def search_token(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Search for tokens"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a search query.\n"
                "Example: /search bonk"
            )
            return
        
        query = ' '.join(context.args)
        
        try:
            await update.message.reply_text(f"🔍 Searching for '{query}'...")
            
            results = await price_service.search_token(query)
            
            if not results:
                await update.message.reply_text("No tokens found")
                return
            
            message = f"📊 <b>Search Results for '{query}'</b>\n\n"
            
            for i, token in enumerate(results[:10], 1):
                message += f"{i}. <b>{token['symbol']}</b> - {token['name']}\n"
                message += f"   Price: ${token['price_usd']:.8f}\n"
                message += f"   Liquidity: {format_usd(token['liquidity_usd'])}\n"
                message += f"   Address: <code>{format_address(token['token_address'])}</code>\n\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def get_whale_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Placeholder for whale alerts"""
        await update.message.reply_text(
            "🐋 Whale alerts will appear here automatically when detected!\n\n"
            "Use /track to start monitoring wallets and receive alerts."
        )
    
    async def get_trending(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get trending tokens"""
        try:
            await update.message.reply_text("🔍 Fetching trending tokens...")
            
            # Get top tokens by liquidity
            tokens = await price_service.search_token("solana")
            
            if not tokens:
                await update.message.reply_text("No trending data available")
                return
            
            message = "📈 <b>Top Trending Tokens on Solana</b>\n\n"
            
            for i, token in enumerate(tokens[:10], 1):
                message += f"{i}. <b>{token['symbol']}</b>\n"
                message += f"   Price: ${token['price_usd']:.8f}\n"
                message += f"   Liquidity: {format_usd(token['liquidity_usd'])}\n\n"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get bot statistics"""
        await update.message.reply_text(
            "📊 <b>Bot Statistics</b>\n\n"
            "Bot is running smoothly! 🚀\n\n"
            "<i>Detailed stats coming soon...</i>",
            parse_mode='HTML'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages"""
        text = update.message.text.strip()
        
        # Check if it's a wallet address
        if is_valid_solana_address(text):
            keyboard = [
                [
                    InlineKeyboardButton("💰 Check Balance", callback_data=f"bal_{text}"),
                    InlineKeyboardButton("➕ Track", callback_data=f"track_{text}")
                ],
                [
                    InlineKeyboardButton("📜 Transactions", callback_data=f"tx_{text}"),
                    InlineKeyboardButton("🔍 Analyze Token", callback_data=f"check_{text}")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📝 <code>{format_address(text)}</code>\n\n"
                f"What would you like to do with this address?",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "Send a valid Solana address or use /help to see available commands."
            )