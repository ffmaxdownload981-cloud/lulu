import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # APIs
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
    HELIUS_RPC_URL = f"https://rpc.helius.xyz/?api-key={HELIUS_API_KEY}"
    
    SOLSCAN_API_KEY = os.getenv("SOLSCAN_API_KEY")
    SOLSCAN_BASE_URL = "https://api.solscan.io"
    
    COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
    
    # Bot Settings
    CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
    MAX_WALLETS_PER_USER = int(os.getenv("MAX_WALLETS_PER_USER", "100"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))

config = Config()