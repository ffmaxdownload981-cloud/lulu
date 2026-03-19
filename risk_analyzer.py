from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from services.price_service import price_service
from services.solscan_service import solscan_service

class RiskAnalyzer:
    def __init__(self):
        self.whale_threshold_usd = 100000  # $100k USD
        self.top_holder_count = 10
    
    async def analyze_token(self, token_address: str) -> Dict[str, Any]:
        """Comprehensive token risk analysis"""
        try:
            # Get token data
            token_info = await solscan_service.get_token_info(token_address)
            holders = await solscan_service.get_token_holders(token_address, limit=1000)
            price_data = await price_service.get_token_price(token_address)
            
            if not token_info:
                return {"error": "Token not found"}
            
            risk_score = 0
            risk_factors = []
            
            # Check if verified
            if not token_info.get('is_verified', False):
                risk_score += 20
                risk_factors.append("Token is not verified")
            
            # Check holder concentration
            if holders:
                total_supply = sum([h.get('amount', 0) for h in holders])
                if total_supply > 0:
                    top_10_amount = sum([h.get('amount', 0) for h in holders[:10]])
                    top_10_percentage = (top_10_amount / total_supply) * 100
                    
                    if top_10_percentage > 80:
                        risk_score += 30
                        risk_factors.append(f"Top 10 holders own {top_10_percentage:.1f}% of supply")
                    elif top_10_percentage > 50:
                        risk_score += 15
                        risk_factors.append(f"Top 10 holders own {top_10_percentage:.1f}% of supply")
            
            # Check liquidity
            if price_data:
                liquidity = price_data.get('liquidity_usd', 0)
                if liquidity < 100000:
                    risk_score += 25
                    risk_factors.append(f"Low liquidity (${liquidity:,.0f})")
                elif liquidity < 500000:
                    risk_score += 10
                    risk_factors.append(f"Moderate liquidity (${liquidity:,.0f})")
            
            # Check holder count
            holder_count = len(holders) if holders else 0
            if holder_count < 100:
                risk_score += 20
                risk_factors.append(f"Very few holders ({holder_count})")
            elif holder_count < 500:
                risk_score += 10
                risk_factors.append(f"Limited holder count ({holder_count})")
            
            # Check token age (if available)
            created_at = token_info.get('created_at')
            if created_at:
                try:
                    age_days = (datetime.utcnow() - datetime.fromtimestamp(created_at)).days
                    if age_days < 7:
                        risk_score += 15
                        risk_factors.append(f"Token is very new ({age_days} days old)")
                except:
                    pass
            
            # Normalize risk score
            risk_score = min(100, max(0, risk_score))
            
            # Determine risk level
            if risk_score < 30:
                risk_level = "LOW"
            elif risk_score < 60:
                risk_level = "MEDIUM"
            elif risk_score < 80:
                risk_level = "HIGH"
            else:
                risk_level = "CRITICAL"
            
            return {
                "token_address": token_address,
                "symbol": token_info.get('symbol', 'Unknown'),
                "name": token_info.get('name', 'Unknown'),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "holder_count": holder_count,
                "price_usd": price_data.get('price_usd', 0) if price_data else 0,
                "liquidity_usd": price_data.get('liquidity_usd', 0) if price_data else 0,
                "volume_24h": price_data.get('volume_24h', 0) if price_data else 0,
                "price_change_24h": price_data.get('price_change_24h', 0) if price_data else 0,
                "dex_url": price_data.get('url') if price_data else None,
                "source": price_data.get('source') if price_data else None
            }
            
        except Exception as e:
            print(f"Error analyzing token {token_address}: {e}")
            return {"error": str(e)}
    
    async def detect_whale_movements(self, transactions: List[Dict]) -> List[Dict]:
        """Detect whale movements from transactions"""
        whale_alerts = []
        sol_price = await price_service.get_sol_price()
        
        for tx in transactions:
            # Check native SOL transfers
            if 'native_transfer' in tx:
                transfer = tx['native_transfer']
                amount_usd = transfer['amount'] * sol_price
                
                if amount_usd >= self.whale_threshold_usd:
                    whale_alerts.append({
                        'signature': tx['signature'],
                        'from': transfer['from'],
                        'to': transfer['to'],
                        'amount': transfer['amount'],
                        'amount_usd': amount_usd,
                        'token': 'SOL',
                        'timestamp': tx['timestamp']
                    })
            
            # Check token transfers
            if 'token_transfer' in tx:
                transfer = tx['token_transfer']
                # Get token price if available
                token_price = await price_service.get_token_price(transfer['mint'])
                if token_price and token_price.get('price_usd'):
                    amount_usd = transfer['amount'] * token_price['price_usd']
                    
                    if amount_usd >= self.whale_threshold_usd:
                        whale_alerts.append({
                            'signature': tx['signature'],
                            'from': transfer['from'],
                            'to': transfer['to'],
                            'amount': transfer['amount'],
                            'amount_usd': amount_usd,
                            'token': transfer['symbol'],
                            'token_address': transfer['mint'],
                            'timestamp': tx['timestamp']
                        })
        
        return whale_alerts

risk_analyzer = RiskAnalyzer()