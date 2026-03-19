import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config

class SolscanService:
    def __init__(self):
        self.api_key = config.SOLSCAN_API_KEY
        self.base_url = config.SOLSCAN_BASE_URL
        self.headers = {
            'Accept': 'application/json',
            'token': self.api_key
        }
    
    async def get_account_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        url = f"{self.base_url}/account/{address}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    
    async def get_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get token information"""
        url = f"{self.base_url}/token/meta"
        params = {'address': token_address}
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data.get('data', {})
                return None
    
    async def get_token_holders(self, token_address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get token holders"""
        url = f"{self.base_url}/token/holders"
        params = {
            'address': token_address,
            'limit': limit,
            'offset': 0
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data.get('data', [])
                return []
    
    async def get_token_market_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get token market data"""
        url = f"{self.base_url}/market/token/{token_address}"
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data.get('data', {})
                return None
    
    async def get_account_transactions(self, address: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get account transactions"""
        url = f"{self.base_url}/account/transactions"
        params = {
            'address': address,
            'limit': limit,
            'sort': 'blocktime'
        }
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        return data.get('data', [])
                return []

solscan_service = SolscanService()