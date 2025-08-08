import aiohttp
import asyncio
from typing import List, Dict, Set
import json
from config import SOLSCAN_API_BASE, SOLSCAN_HEADERS, SOLSCAN_PRO_API_KEY, MAX_WALLETS_DISPLAY
from solana_rpc import solana_rpc

class SolscanAPI:
    def __init__(self):
        self.base_url = SOLSCAN_API_BASE
        self.headers = SOLSCAN_HEADERS
        
        # Endereços de programas do sistema Solana que devem ser filtrados  
        self.SYSTEM_PROGRAMS = {
            '11111111111111111111111111111111',  # System Program
            'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA',  # Token Program  
            'ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL',  # Associated Token Program
            'ComputeBudget111111111111111111111111111111',  # Compute Budget Program
            'SysvarRent111111111111111111111111111111111',  # Sysvar Rent
            'SysvarC1ock11111111111111111111111111111111',  # Sysvar Clock
            'Vote111111111111111111111111111111111111111',  # Vote Program
            'Stake11111111111111111111111111111111111111',  # Stake Program
            'Config1111111111111111111111111111111111111',  # Config Program
            'BPFLoaderUpgradeab1e11111111111111111111111',  # BPF Upgradeable Loader
        }
    
    def is_valid_user_wallet(self, wallet_address: str, mint_address: str) -> bool:
        """
        Verifica se um endereço é uma wallet de usuário válida
        Filtra programas do sistema, endereços vazios e o próprio token
        """
        if not wallet_address or len(wallet_address) < 32:
            return False
            
        # Filtra o próprio token
        if wallet_address == mint_address:
            return False
            
        # Filtra programas do sistema Solana
        if wallet_address in self.SYSTEM_PROGRAMS:
            return False
            
        # Filtra endereços que são claramente programas (terminam com muitos 1s)
        if wallet_address.endswith('1' * 10):  # 10 ou mais '1's no final
            return False
            
        return True
    
    async def get_wallet_balance(self, wallet_address: str) -> float:
        """
        Busca o saldo de SOL de uma wallet usando RPC
        """
        try:
            # Usa o RPC Solana para buscar saldo  
            balance = await solana_rpc.get_wallet_balance(wallet_address)
            return balance
        except Exception as e:
            print(f"⚠️ Erro ao buscar saldo via Solscan: {e}")
            return 0.0
        
    async def get_token_transactions(self, token_address: str, limit: int = 2000) -> List[Dict]:
        """
        Busca transações de um token específico no Solscan
        Retorna transações ordenadas por tempo (mais antigas primeiro)
        """
        url = f"{self.base_url}/token/transfer"
        params = {
            'address': token_address,
            'limit': limit,
            'offset': 0
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('data', [])
                        
                        # Ordena transações por timestamp (mais antigas primeiro)
                        # Para pegar as primeiras wallets que compraram
                        sorted_transactions = sorted(
                            transactions, 
                            key=lambda x: x.get('blockTime', 0) or x.get('slot', 0)
                        )
                        
                        return sorted_transactions
                    else:
                        print(f"Erro na API: {response.status}")
                        return []
            except Exception as e:
                print(f"Erro ao buscar transações: {e}")
                return []
    
    async def get_token_info(self, token_address: str) -> Dict:
        """
        Busca informações básicas do token
        Tenta primeiro via Solscan, depois via Jupiter API como fallback
        """
        url = f"{self.base_url}/token/meta"
        params = {'address': token_address}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        token_data = data.get('data', {})
                        if token_data and token_data.get('symbol'):
                            print(f"✅ Solscan: Metadados encontrados para {token_address[:8]}...")
                            return token_data
                    else:
                        print(f"⚠️ Solscan API falhou (status {response.status}), tentando Jupiter...")
            except Exception as e:
                print(f"⚠️ Erro no Solscan: {e}, tentando Jupiter API...")
        
        # Fallback: Jupiter API
        try:
            jupiter_url = f"https://tokens.jup.ag/token/{token_address}"
            async with session.get(jupiter_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Jupiter API: Metadados encontrados para {token_address[:8]}...")
                    return {
                        'name': data.get('name', 'Token Desconhecido'),
                        'symbol': data.get('symbol', 'N/A'),
                        'decimals': data.get('decimals', 9),
                        'logoURI': data.get('logoURI', ''),
                        'tags': data.get('tags', [])
                    }
                else:
                    print(f"⚠️ Jupiter API também falhou (status {response.status})")
        except Exception as e:
            print(f"⚠️ Erro na Jupiter API: {e}")
        
        return {}
    
    async def extract_buyers(self, token_address: str) -> tuple[List[str], Dict]:
        """
        Extrai a lista de wallets que compraram o token em ordem cronológica
        Usa API Pro do Solscan (se disponível) ou RPC Solana como fallback
        Retorna: (lista_de_wallets_ordenada, info_do_token)
        """
        print(f"Buscando compradores para o token: {token_address}")
        
        # Verifica se tem API key do Solscan Pro
        if SOLSCAN_PRO_API_KEY:
            print("Tentando usar API Pro do Solscan...")
            try:
                # Busca informações do token
                token_info = await self.get_token_info(token_address)
                
                # Busca transações do token (já ordenadas por tempo)
                transactions = await self.get_token_transactions(token_address)
                
                if transactions:
                    buyers_ordered = []  # Lista ordenada para manter sequência cronológica
                    buyers_with_balance = []  # Lista com wallets e saldos
                    seen_wallets = set()  # Para evitar duplicatas
                    
                    for tx in transactions:
                        try:
                            # Verifica se é uma transação de compra
                            if 'to_address' in tx and 'from_address' in tx:
                                dest = tx.get('to_address', '')
                                source = tx.get('from_address', '')
                                
                                # Processa a wallet de destino (quem recebeu os tokens)
                                if (dest and 
                                    self.is_valid_user_wallet(dest, token_address) and
                                    dest not in seen_wallets):
                                    buyers_ordered.append(dest)
                                    seen_wallets.add(dest)
                                    
                                    # Continua buscando todas as wallets (sem limite)
                                elif dest and dest in self.SYSTEM_PROGRAMS:
                                    print(f"🔧 Programa filtrado (dest): {dest[:20]}...")
                                
                                # Processa source também (sem limite)
                                if (source and 
                                    self.is_valid_user_wallet(source, token_address) and
                                    source not in seen_wallets):
                                    buyers_ordered.append(source)
                                    seen_wallets.add(source)
                                    
                                    # Continua buscando todas as wallets (sem limite)
                                elif source and source in self.SYSTEM_PROGRAMS:
                                    print(f"🔧 Programa filtrado (source): {source[:20]}...")
                                        
                        except Exception as e:
                            print(f"Erro ao processar transação: {e}")
                            continue
                    
                    if buyers_ordered:
                        print(f"✅ API Pro Solscan: {len(buyers_ordered)} wallets encontradas")
                        
                        # Busca saldos das wallets encontradas  
                        print("💰 Buscando saldos das wallets via RPC...")
                        buyers_with_balance = []
                        for wallet in buyers_ordered:  # Busca saldo de todas as wallets
                            try:
                                balance = await self.get_wallet_balance(wallet)
                                buyers_with_balance.append({
                                    'wallet': wallet,
                                    'balance': balance,
                                    'timestamp': 0  # Solscan não tem timestamp individual
                                })
                                print(f"💰 {wallet[:8]}... {balance:.2f}")
                            except:
                                buyers_with_balance.append({
                                    'wallet': wallet, 
                                    'balance': 0.0,
                                    'timestamp': 0
                                })
                        
                        # Garante ordem cronológica final mesmo no Solscan
                        print(f"📅 Solscan: Ordem cronológica mantida - {len(buyers_ordered)} wallets")
                        return buyers_ordered, token_info, buyers_with_balance
                    
            except Exception as e:
                print(f"❌ Erro na API Pro do Solscan: {e}")
        
        # Fallback: usar RPC direto da Solana (gratuito)
        print("🔄 Usando RPC Solana como alternativa...")
        try:
            buyers_rpc, token_info_rpc, balance_info = await solana_rpc.extract_buyers_from_mint(token_address)
            if buyers_rpc:
                print(f"✅ RPC Solana: {len(buyers_rpc)} wallets encontradas")
                return buyers_rpc, token_info_rpc, balance_info
        except Exception as e:
            print(f"❌ Erro no RPC Solana: {e}")
        
        # Se ambos falharam
        print("❌ Nenhuma fonte de dados funcionou")
        return [], {}, []
    
    def validate_token_address(self, address: str) -> bool:
        """
        Valida se o endereço do token tem formato válido
        """
        if not address:
            return False
        
        # Endereços Solana geralmente têm entre 32-44 caracteres
        if len(address) < 32 or len(address) > 44:
            return False
        
        # Deve conter apenas caracteres alfanuméricos válidos para Base58
        import re
        # Base58 não usa 0, O, I, l para evitar confusão
        if not re.match(r'^[1-9A-HJ-NP-Za-km-z]+$', address):
            return False
            
        # Verificações adicionais básicas
        if address.startswith('0x'):  # Não é Ethereum
            return False
            
        return True

# Instância global da API
solscan_api = SolscanAPI()