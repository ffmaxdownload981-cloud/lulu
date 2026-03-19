from solana.rpc.api import Client
from solana.publickey import PublicKey
from solders.signature import Signature
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config

class SolanaService:
    def __init__(self):
        self.client = Client(config.HELIUS_RPC_URL)
    
    async def get_balance(self, address: str) -> float:
        """Get SOL balance for a wallet"""
        try:
            pubkey = PublicKey(address)
            response = self.client.get_balance(pubkey)
            if response['result']:
                return response['result']['value'] / 1e9
            return 0
        except Exception as e:
            print(f"Error getting balance for {address}: {e}")
            return 0
    
    async def get_token_accounts(self, address: str) -> List[Dict[str, Any]]:
        """Get all token accounts for a wallet"""
        try:
            pubkey = PublicKey(address)
            token_program = PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            
            response = self.client.get_token_accounts_by_owner(
                pubkey,
                {"programId": token_program}
            )
            
            token_accounts = []
            if response['result']:
                for account in response['result']['value']:
                    try:
                        account_info = account['account']['data']['parsed']['info']
                        token_accounts.append({
                            'mint': account_info['mint'],
                            'amount': account_info['tokenAmount']['uiAmount'],
                            'decimals': account_info['tokenAmount']['decimals']
                        })
                    except:
                        continue
            
            return token_accounts
        except Exception as e:
            print(f"Error getting token accounts for {address}: {e}")
            return []
    
    async def get_recent_transactions(self, address: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent transactions for a wallet"""
        try:
            pubkey = PublicKey(address)
            signatures = self.client.get_signatures_for_address(pubkey, limit=limit)
            
            transactions = []
            if signatures['result']:
                for sig_info in signatures['result']:
                    tx = await self.get_transaction_details(sig_info['signature'])
                    if tx:
                        transactions.append(tx)
            
            return transactions
        except Exception as e:
            print(f"Error getting transactions for {address}: {e}")
            return []
    
    async def get_transaction_details(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get detailed transaction information"""
        try:
            response = self.client.get_transaction(signature, encoding="jsonParsed")
            
            if response['result']:
                tx = response['result']
                return self._parse_transaction(tx, signature)
            return None
        except Exception as e:
            print(f"Error getting transaction details for {signature}: {e}")
            return None
    
    def _parse_transaction(self, tx_data: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """Parse transaction data"""
        try:
            meta = tx_data['meta']
            transaction = tx_data['transaction']
            
            # Get timestamp
            timestamp = None
            if 'blockTime' in tx_data:
                timestamp = datetime.fromtimestamp(tx_data['blockTime'])
            
            # Get accounts involved
            message = transaction['message']
            accounts = message.get('accountKeys', [])
            
            # Determine transaction type and amount
            tx_type = "UNKNOWN"
            amount = 0
            from_address = ""
            to_address = ""
            
            # Check for transfer instructions
            if 'instructions' in message:
                for ix in message['instructions']:
                    if 'parsed' in ix:
                        parsed = ix['parsed']
                        if parsed.get('type') == 'transfer':
                            tx_type = "TRANSFER"
                            info = parsed.get('info', {})
                            from_address = info.get('source', '')
                            to_address = info.get('destination', '')
                            amount = info.get('lamports', 0) / 1e9
            
            return {
                'signature': signature,
                'timestamp': timestamp,
                'type': tx_type,
                'status': 'success' if not meta.get('err') else 'failed',
                'fee': meta.get('fee', 0) / 1e9,
                'from_address': from_address,
                'to_address': to_address,
                'amount': amount,
                'accounts': accounts
            }
            
        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None

solana_service = SolanaService()