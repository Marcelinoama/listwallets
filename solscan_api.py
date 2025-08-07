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
        """
        url = f"{self.base_url}/token/meta"
        params = {'address': token_address}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {})
                    else:
                        return {}
            except Exception as e:
                print(f"Erro ao buscar info do token: {e}")
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
                    seen_wallets = set()  # Para evitar duplicatas
                    
                    for tx in transactions:
                        try:
                            # Verifica se é uma transação de compra
                            if 'to_address' in tx and 'from_address' in tx:
                                dest = tx.get('to_address', '')
                                source = tx.get('from_address', '')
                                
                                # Processa a wallet de destino (quem recebeu os tokens)
                                if (dest and len(dest) > 30 and 
                                    dest != token_address and 
                                    dest not in seen_wallets):
                                    buyers_ordered.append(dest)
                                    seen_wallets.add(dest)
                                    
                                    # Para quando atingir o limite configurado
                                    if len(buyers_ordered) >= MAX_WALLETS_DISPLAY:
                                        break
                                
                                # Se ainda não atingiu o limite, processa source também
                                if (len(buyers_ordered) < MAX_WALLETS_DISPLAY and
                                    source and len(source) > 30 and 
                                    source != token_address and 
                                    source not in seen_wallets):
                                    buyers_ordered.append(source)
                                    seen_wallets.add(source)
                                    
                                    # Para quando atingir o limite configurado
                                    if len(buyers_ordered) >= MAX_WALLETS_DISPLAY:
                                        break
                                        
                        except Exception as e:
                            print(f"Erro ao processar transação: {e}")
                            continue
                    
                    if buyers_ordered:
                        print(f"✅ API Pro Solscan: {len(buyers_ordered)} wallets encontradas")
                        return buyers_ordered, token_info
                    
            except Exception as e:
                print(f"❌ Erro na API Pro do Solscan: {e}")
        
        # Fallback: usar RPC direto da Solana (gratuito)
        print("🔄 Usando RPC Solana como alternativa...")
        try:
            buyers_rpc, token_info_rpc = await solana_rpc.extract_buyers_from_mint(token_address)
            if buyers_rpc:
                print(f"✅ RPC Solana: {len(buyers_rpc)} wallets encontradas")
                return buyers_rpc, token_info_rpc
        except Exception as e:
            print(f"❌ Erro no RPC Solana: {e}")
        
        # Se ambos falharam
        print("❌ Nenhuma fonte de dados funcionou")
        return [], {}
    
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