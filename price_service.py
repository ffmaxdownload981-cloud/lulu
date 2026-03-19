import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from cachetools import TTLCache

class PriceService:
    def __init__(self):
        # DexScreener API
        self.dexscreener_base = "https://api.dexscreener.com/latest/dex"
        
        # CoinGecko API
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        
        # Cache prices for 1 minute
        self.price_cache = TTLCache(maxsize=1000, ttl=60)
        self.token_cache = TTLCache(maxsize=500, ttl=300)
        
        # Rate limiting
        self.last_request = datetime.now()
        self.request_count = 0
        
        # Known DEXes on Solana
        self.solana_dexes = [
            "raydium", "orca", "jupiter", "saber", 
            "lifinity", "meteora", "phoenix", "openbook"
        ]
    
    async def get_token_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get token price from DexScreener (primary) and CoinGecko (fallback)"""
        # Try DexScreener first
        price_data = await self._get_dexscreener_price(token_address)
        
        if price_data and price_data.get('price_usd'):
            return price_data
        
        # Fallback to CoinGecko
        return await self._get_coingecko_price(token_address)
    
    async def _get_dexscreener_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get price from DexScreener"""
        cache_key = f"dexscreener_{token_address}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        await self._rate_limit()
        
        try:
            url = f"{self.dexscreener_base}/tokens/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('pairs'):
                            # Filter Solana pairs
                            solana_pairs = [
                                pair for pair in data['pairs'] 
                                if pair.get('chainId') == 'solana'
                            ]
                            
                            if solana_pairs:
                                # Get pair with highest liquidity
                                best_pair = max(
                                    solana_pairs, 
                                    key=lambda x: float(x.get('liquidity', {}).get('usd', 0))
                                )
                                
                                result = {
                                    'price_usd': float(best_pair.get('priceUsd', 0)),
                                    'price_sol': float(best_pair.get('priceNative', 0)),
                                    'liquidity_usd': float(best_pair.get('liquidity', {}).get('usd', 0)),
                                    'volume_24h': float(best_pair.get('volume', {}).get('h24', 0)),
                                    'price_change_24h': float(best_pair.get('priceChange', {}).get('h24', 0)),
                                    'dex': best_pair.get('dexId', 'unknown'),
                                    'pair_address': best_pair.get('pairAddress'),
                                    'url': f"https://dexscreener.com/solana/{best_pair.get('pairAddress')}",
                                    'source': 'dexscreener'
                                }
                                
                                self.price_cache[cache_key] = result
                                return result
                    
                    return None
                    
        except Exception as e:
            print(f"Error fetching from DexScreener: {e}")
            return None
    
    async def _get_coingecko_price(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get price from CoinGecko"""
        cache_key = f"coingecko_{token_address}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        await self._rate_limit()
        
        try:
            # Get token info from CoinGecko
            url = f"{self.coingecko_base}/coins/solana/contract/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        market_data = data.get('market_data', {})
                        result = {
                            'price_usd': market_data.get('current_price', {}).get('usd'),
                            'price_sol': None,  # CoinGecko doesn't provide SOL price directly
                            'market_cap': market_data.get('market_cap', {}).get('usd'),
                            'volume_24h': market_data.get('total_volume', {}).get('usd'),
                            'price_change_24h': market_data.get('price_change_percentage_24h'),
                            'source': 'coingecko',
                            'symbol': data.get('symbol', '').upper(),
                            'name': data.get('name', '')
                        }
                        
                        self.price_cache[cache_key] = result
                        return result
                    
                    return None
                    
        except Exception as e:
            print(f"Error fetching from CoinGecko: {e}")
            return None
    
    async def search_token(self, query: str) -> List[Dict[str, Any]]:
        """Search for tokens on DexScreener"""
        await self._rate_limit()
        
        try:
            url = f"{self.dexscreener_base}/search"
            params = {'q': query}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        results = []
                        if data.get('pairs'):
                            for pair in data['pairs']:
                                if pair.get('chainId') == 'solana':
                                    results.append({
                                        'token_address': pair.get('baseToken', {}).get('address'),
                                        'symbol': pair.get('baseToken', {}).get('symbol'),
                                        'name': pair.get('baseToken', {}).get('name'),
                                        'price_usd': float(pair.get('priceUsd', 0)),
                                        'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                                        'dex': pair.get('dexId', 'unknown'),
                                        'url': f"https://dexscreener.com/solana/{pair.get('pairAddress')}"
                                    })
                            
                            # Sort by liquidity
                            results.sort(key=lambda x: x.get('liquidity_usd', 0), reverse=True)
                        
                        return results
                    return []
                    
        except Exception as e:
            print(f"Error searching tokens: {e}")
            return []
    
    async def get_sol_price(self) -> float:
        """Get current SOL price in USD"""
        cache_key = "sol_price"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        # Use wrapped SOL address
        sol_address = "So11111111111111111111111111111111111111112"
        
        price_data = await self._get_dexscreener_price(sol_address)
        if price_data and price_data.get('price_usd'):
            price = price_data['price_usd']
            self.price_cache[cache_key] = price
            return price
        
        # Fallback to CoinGecko
        try:
            url = f"{self.coingecko_base}/simple/price"
            params = {
                'ids': 'solana',
                'vs_currencies': 'usd'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('solana', {}).get('usd', 100)
                        self.price_cache[cache_key] = price
                        return price
        except:
            pass
        
        return 100  # Default fallback
    
    async def get_token_pairs(self, token_address: str) -> List[Dict[str, Any]]:
        """Get all trading pairs for a token"""
        await self._rate_limit()
        
        try:
            url = f"{self.dexscreener_base}/tokens/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        pairs = []
                        if data.get('pairs'):
                            for pair in data['pairs']:
                                if pair.get('chainId') == 'solana':
                                    pairs.append({
                                        'dex': pair.get('dexId', 'unknown'),
                                        'pair_address': pair.get('pairAddress'),
                                        'price_usd': float(pair.get('priceUsd', 0)),
                                        'liquidity_usd': float(pair.get('liquidity', {}).get('usd', 0)),
                                        'volume_24h': float(pair.get('volume', {}).get('h24', 0)),
                                        'url': f"https://dexscreener.com/solana/{pair.get('pairAddress')}"
                                    })
                            
                            pairs.sort(key=lambda x: x.get('liquidity_usd', 0), reverse=True)
                        
                        return pairs
                    return []
                    
        except Exception as e:
            print(f"Error getting token pairs: {e}")
            return []
    
    async def _rate_limit(self):
        """Simple rate limiting"""
        now = datetime.now()
        if (now - self.last_request).seconds >= 60:
            self.request_count = 0
            self.last_request = now
        
        self.request_count += 1
        
        if self.request_count > 30:  # 30 requests per minute max
            wait_time = 60 - (now - self.last_request).seconds
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                self.request_count = 0
                self.last_request = datetime.now()
        
        await asyncio.sleep(0.1)

price_service = PriceService()