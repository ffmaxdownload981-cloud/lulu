WELCOME_TEXT = """
🚀 <b>Welcome to Solana Tracker Bot!</b>

Hello {name}! I'm your comprehensive Solana blockchain tracker.

I can help you track wallets, analyze tokens, monitor whale movements, and much more!

<b>Quick Commands:</b>
• /track &lt;address&gt; - Start tracking a wallet
• /check &lt;token&gt; - Analyze token risk
• /holders &lt;token&gt; - View top token holders
• /whales - Recent whale alerts
• /help - Show all commands

Get started by sending me a Solana address or using a command!
"""

HELP_TEXT = """
<b>📚 Solana Tracker Bot Commands</b>

<b>Wallet Tracking:</b>
/track &lt;address&gt; [label] - Track a wallet
/untrack &lt;address&gt; - Stop tracking a wallet
/list - Show your tracked wallets
/balance &lt;address&gt; - Check wallet balance
/transactions &lt;address&gt; [limit] - View recent transactions

<b>Token Analysis:</b>
/check &lt;token_address&gt; - Analyze token risk
/holders &lt;token_address&gt; [limit] - View top token holders

<b>Price & Market Data:</b>
/price &lt;token_address&gt; - Get current token price
/search &lt;query&gt; - Search for tokens
/trending - Top trending tokens on Solana

<b>Alerts & Monitoring:</b>
/whales - View recent whale alerts
/stats - Bot statistics

<b>General:</b>
/start - Start the bot
/help - Show this help message

<b>Features:</b>
✅ Automatic wallet tracking
✅ Real-time balance updates
✅ Token risk analysis
✅ Holder concentration tracking
✅ Whale movement alerts
✅ DexScreener & CoinGecko price data
✅ No limits, completely free

<b>Tips:</b>
• Send any Solana address for quick actions
• Add labels to easily identify wallets
• Use /check before investing in any token
"""

RISK_LEVELS = {
    "LOW": {
        "emoji": "🟢",
        "color": "green",
        "description": "Low risk - Standard token with good metrics"
    },
    "MEDIUM": {
        "emoji": "🟡",
        "color": "yellow",
        "description": "Medium risk - Some concerns, do your research"
    },
    "HIGH": {
        "emoji": "🟠",
        "color": "orange",
        "description": "High risk - Multiple red flags, be cautious"
    },
    "CRITICAL": {
        "emoji": "🔴",
        "color": "red",
        "description": "Critical risk - Likely scam or extremely risky"
    }
}

TRANSACTION_TYPES = {
    "TRANSFER": "💸 Transfer",
    "SWAP": "🔄 Swap",
    "MINT": "🪙 Mint",
    "BURN": "🔥 Burn",
    "STAKE": "🔒 Stake",
    "UNSTAKE": "🔓 Unstake",
    "CREATE_ACCOUNT": "📝 Create Account",
    "CLOSE_ACCOUNT": "❌ Close Account"
}

WHALE_THRESHOLD_USD = 100000  # $100k USD

ERROR_MESSAGES = {
    "invalid_address": "❌ Invalid Solana address",
    "not_found": "❌ Information not found",
    "api_error": "❌ API error, please try again later",
    "rate_limit": "⏳ Rate limit reached, please wait",
    "not_tracking": "❌ You're not tracking this wallet",
    "already_tracking": "❌ Already tracking this wallet",
    "max_wallets": "❌ You've reached the maximum limit of 100 tracked wallets"
}

SUCCESS_MESSAGES = {
    "wallet_tracked": "✅ Successfully tracking wallet: {address}",
    "wallet_untracked": "✅ Stopped tracking wallet: {address}",
    "alert_set": "✅ Alert set successfully"
}

BUTTONS = {
    "refresh": "🔄 Refresh",
    "holders": "📊 Holders",
    "price": "💰 Price",
    "transactions": "📜 Transactions",
    "back": "◀️ Back",
    "cancel": "❌ Cancel",
    "track": "➕ Track",
    "analyze": "🔍 Analyze"
}