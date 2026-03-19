import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config

class HeliusService:
    def __init__(self):
        self.api_key = config.HELIUS_API_KEY
        self.base_url = "https://api.helius.xyz/v0"
    
    async def get_transactions(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get enhanced transactions for an address"""
        url = f"{self.base_url}/addresses/{address}/transactions"
        params = {
            'api-key': self.api_key,
            'limit': limit
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_transactions(data)
                return []
    
    def _parse_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Parse Helius transactions"""
        parsed = []
        for tx in transactions:
            try:
                parsed_tx = {
                    'signature': tx.get('signature'),
                    'timestamp': datetime.fromtimestamp(tx.get('timestamp', 0)),
                    'type': tx.get('type', 'UNKNOWN'),
                    'status': tx.get('status', 'unknown'),
                    'fee': tx.get('fee', 0) / 1e9,
                    'description': tx.get('description', '')
                }
                
                # Extract transfer info
                if 'tokenTransfers' in tx and tx['tokenTransfers']:
                    transfer = tx['tokenTransfers'][0]
                    parsed_tx['token_transfer'] = {
                        'from': transfer.get('fromUserAccount'),
                        'to': transfer.get('toUserAccount'),
                        'amount': transfer.get('tokenAmount'),
                        'mint': transfer.get('mint'),
                        'symbol': transfer.get('symbol', 'Unknown')
                    }
                
                # Extract native transfer
                if 'nativeTransfers' in tx and tx['nativeTransfers']:
                    transfer = tx['nativeTransfers'][0]
                    parsed_tx['native_transfer'] = {
                        'from': transfer.get('fromUserAccount'),
                        'to': transfer.get('toUserAccount'),
                        'amount': transfer.get('amount', 0) / 1e9
                    }
                
                parsed.append(parsed_tx)
            except Exception as e:
                print(f"Error parsing transaction: {e}")
                continue
        
        return parsed
    
    async def get_parsed_transaction(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get parsed transaction by signature"""
        url = f"{self.base_url}/transactions/?api-key={self.api_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=[signature]) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        return self._parse_transactions([data[0]])[0]
                return None
    
    async def get_token_metadata(self, mint_address: str) -> Optional[Dict[str, Any]]:
        """Get token metadata"""
        url = f"{self.base_url}/token-metadata"
        params = {
            'api-key': self.api_key,
            'mint': mint_address
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                return None

helius_service = HeliusService()