#!/usr/bin/env python3
"""
Solana Tracker Telegram Bot
Complete bot for tracking wallets, analyzing tokens, and monitoring whale movements
"""

import asyncio
import logging
from telegram.ext import ApplicationBuilder

from config import config
from database.crud import db_manager
from handlers.commands import CommandHandlers
from handlers.callbacks import CallbackHandlers
from handlers.tasks import BackgroundTasks

# Setup logging
logging.basicFormat(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SolanaTrackerBot:
    def __init__(self):
        # Initialize bot application
        self.application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
        self.background_tasks = BackgroundTasks(self.application)
        
        # Verify configuration
        self._verify_config()
        
        # Setup handlers
        self.command_handlers = CommandHandlers(self.application)
        self.callback_handlers = CallbackHandlers(self.application)
        
        logger.info("✅ Bot initialized successfully")
    
    def _verify_config(self):
        """Verify required configuration"""
        if not config.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        
        if not config.HELIUS_API_KEY:
            logger.warning("⚠️ HELIUS_API_KEY not set - some features may not work")
        
        if not config.SOLSCAN_API_KEY:
            logger.warning("⚠️ SOLSCAN_API_KEY not set - token holder data may be limited")
    
    async def post_init(self):
        """Run after bot initialization"""
        logger.info("🚀 Bot is starting up...")
        
        # Test database connection
        try:
            session = db_manager.get_session()
            session.execute("SELECT 1")
            session.close()
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
        
        # Start background tasks
        logger.info("🔄 Starting background tasks...")
        await self.background_tasks.start()
        
        # Set bot commands
        await self._set_bot_commands()
        
        logger.info("✅ Bot is ready!")
    
    async def post_shutdown(self):
        """Run before bot shutdown"""
        logger.info("🛑 Bot is shutting down...")
        
        # Stop background tasks
        await self.background_tasks.stop()
        
        logger.info("✅ Bot shutdown complete")
    
    async def _set_bot_commands(self):
        """Set bot commands in Telegram"""
        commands = [
            ("start", "Start the bot"),
            ("help", "Show help message"),
            ("track", "Track a wallet"),
            ("untrack", "Stop tracking a wallet"),
            ("list", "List tracked wallets"),
            ("balance", "Check wallet balance"),
            ("transactions", "View recent transactions"),
            ("check", "Analyze token risk"),
            ("holders", "View top token holders"),
            ("price", "Get token price"),
            ("search", "Search for tokens"),
            ("whales", "View whale alerts"),
            ("trending", "Top trending tokens"),
            ("stats", "Bot statistics")
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("✅ Bot commands set")
    
    def run(self):
        """Run the bot"""
        try:
            # Add post init and shutdown handlers
            self.application.post_init = self.post_init
            self.application.post_shutdown = self.post_shutdown
            
            # Start the bot
            logger.info("▶️ Starting bot polling...")
            self.application.run_polling()
            
        except KeyboardInterrupt:
            logger.info("⏸️ Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Bot crashed: {e}")
        finally:
            # Ensure cleanup
            asyncio.run(self.post_shutdown())

def main():
    """Main entry point"""
    bot = SolanaTrackerBot()
    bot.run()

if __name__ == "__main__":
    main()