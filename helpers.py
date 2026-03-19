import re
import base58
from typing import Optional
from datetime import datetime, timedelta

def is_valid_solana_address(address: str) -> bool:
    """Validate Solana address"""
    try:
        # Check if it's a base58 string of correct length
        if len(address) not in [32, 44, 43]:
            return False
        
        # Try to decode
        decoded = base58.b58decode(address)
        return len(decoded) == 32
    except:
        return False

def format_address(address: str, length: int = 8) -> str:
    """Format address for display"""
    if not address or len(address) <= length * 2:
        return address
    return f"{address[:length]}...{address[-length:]}"

def format_number(num: float, decimals: int = 2) -> str:
    """Format number with K/M/B suffixes"""
    if num >= 1e9:
        return f"{num/1e9:.{decimals}f}B"
    elif num >= 1e6:
        return f"{num/1e6:.{decimals}f}M"
    elif num >= 1e3:
        return f"{num/1e3:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"

def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display"""
    if not timestamp:
        return "Unknown"
    
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return "just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return timestamp.strftime("%Y-%m-%d %H:%M")

def extract_addresses(text: str) -> list:
    """Extract Solana addresses from text"""
    # Solana addresses are base58 strings of length 32-44
    pattern = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
    return re.findall(pattern, text)

def calculate_percentage_change(old: float, new: float) -> float:
    """Calculate percentage change"""
    if old == 0:
        return 0
    return ((new - old) / old) * 100

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length"""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def format_usd(amount: float) -> str:
    """Format USD amount"""
    if amount >= 1e9:
        return f"${amount/1e9:.2f}B"
    elif amount >= 1e6:
        return f"${amount/1e6:.2f}M"
    elif amount >= 1e3:
        return f"${amount/1e3:.2f}K"
    else:
        return f"${amount:.2f}"

def get_risk_emoji(risk_level: str) -> str:
    """Get emoji for risk level"""
    risk_emojis = {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🟠",
        "CRITICAL": "🔴"
    }
    return risk_emojis.get(risk_level, "⚪")

def safe_float_convert(value, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default