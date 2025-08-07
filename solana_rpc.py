import aiohttp
import asyncio
import json
import random
from typing import List, Dict, Optional, Set
from config import SOLANA_RPC_URLS, MAX_WALLETS_DISPLAY, RPC_RETRY_ATTEMPTS, RPC_RETRY_DELAY, RPC_REQUEST_DELAY
import base64
import base58

class SolanaRPC:
    def __init__(self):
        self.rpc_urls = SOLANA_RPC_URLS
        self.current_rpc_index = 0
        self.blacklisted_rpcs = {}  # RPC -> tempo_de_blacklist
        self.request_count = 0
        
    async def get_current_rpc_url(self) -> str:
        """Retorna a URL RPC atual evitando RPCs blacklisted"""
        import time
        
        # Remove RPCs expirados da blacklist (após 5 minutos)
        current_time = time.time()
        expired_rpcs = [rpc for rpc, blacklist_time in self.blacklisted_rpcs.items() 
                       if current_time - blacklist_time > 300]
        for rpc in expired_rpcs:
            del self.blacklisted_rpcs[rpc]
            print(f"🔓 RPC removido da blacklist: {rpc}")
        
        # Procura um RPC não blacklisted
        attempts = 0
        while attempts < len(self.rpc_urls):
            rpc_url = self.rpc_urls[self.current_rpc_index % len(self.rpc_urls)]
            
            if rpc_url not in self.blacklisted_rpcs:
                return rpc_url
            
            self.current_rpc_index += 1
            attempts += 1
        
        # Se todos estão blacklisted, usa o primeiro mesmo assim
        print("⚠️ Todos os RPCs estão blacklisted, usando o primeiro mesmo assim")
        return self.rpc_urls[0]
    
    def rotate_rpc(self):
        """Roda para próxima URL RPC em caso de erro"""
        self.current_rpc_index += 1
    
    async def rpc_request(self, method: str, params: list, timeout: int = 30) -> Optional[Dict]:
        """Faz requisição RPC para Solana com retry automático e rate limiting"""
        
        for rpc_attempt in range(len(self.rpc_urls)):
            rpc_url = await self.get_current_rpc_url()
            
            # Tenta várias vezes na mesma RPC antes de trocar
            for retry_attempt in range(RPC_RETRY_ATTEMPTS):
                payload = {
                    "jsonrpc": "2.0",
                    "id": random.randint(1, 10000),
                    "method": method,
                    "params": params
                }
                
                try:
                    # Delay entre requisições para evitar rate limiting
                    if retry_attempt > 0:
                        delay = RPC_RETRY_DELAY * (2 ** retry_attempt)  # Backoff exponencial
                        print(f"⏳ Aguardando {delay}s antes de tentar novamente...")
                        await asyncio.sleep(delay)
                    else:
                        await asyncio.sleep(RPC_REQUEST_DELAY)
                    
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                        async with session.post(rpc_url, json=payload) as response:
                            if response.status == 200:
                                data = await response.json()
                                if 'result' in data:
                                    return data['result']
                                elif 'error' in data:
                                    error_msg = data['error']
                                    print(f"❌ RPC Error: {error_msg}")
                                    # Se é erro de método ou parâmetro, não tentar novamente
                                    if error_msg.get('code') in [-32601, -32602]:
                                        return None
                                    # Para outros erros, continua tentando
                                    continue
                            elif response.status == 429:
                                print(f"⚠️ Rate limit atingido em {rpc_url} - tentativa {retry_attempt + 1}/{RPC_RETRY_ATTEMPTS}")
                                # Se é a última tentativa, blacklista o RPC
                                if retry_attempt >= RPC_RETRY_ATTEMPTS - 1:
                                    import time
                                    self.blacklisted_rpcs[rpc_url] = time.time()
                                    print(f"🚫 RPC blacklisted por 5 min: {rpc_url}")
                                continue  # Tenta novamente com delay
                            else:
                                print(f"❌ HTTP Error {response.status} em {rpc_url}")
                                break  # Troca de RPC
                                
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout em {rpc_url} - tentativa {retry_attempt + 1}/{RPC_RETRY_ATTEMPTS}")
                    continue
                except Exception as e:
                    print(f"❌ Erro na RPC {rpc_url}: {e}")
                    break  # Troca de RPC
            
            # Roda para próxima RPC se todas as tentativas falharam
            print(f"🔄 Trocando para próxima RPC...")
            self.rotate_rpc()
        
        print("❌ Todas as RPCs falharam")
        return None
    
    async def get_token_accounts_by_mint(self, mint_address: str) -> List[Dict]:
        """
        Busca todas as contas de token para um mint específico
        """
        params = [
            mint_address,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed"
            }
        ]
        
        result = await self.rpc_request("getTokenLargestAccounts", params)
        if result and 'value' in result:
            return result['value']
        return []
    
    async def get_token_supply(self, mint_address: str) -> Dict:
        """
        Busca informações de supply do token
        """
        params = [
            mint_address,
            {"commitment": "confirmed"}
        ]
        
        result = await self.rpc_request("getTokenSupply", params)
        if result and 'value' in result:
            return result['value']
        return {}
    
    async def get_signatures_for_address(self, address: str, limit: int = 1000) -> List[Dict]:
        """
        Busca assinaturas de transações para um endereço
        """
        params = [
            address,
            {
                "limit": limit,
                "commitment": "confirmed"
            }
        ]
        
        result = await self.rpc_request("getSignaturesForAddress", params)
        return result if result else []
    
    async def get_transaction(self, signature: str) -> Optional[Dict]:
        """
        Busca detalhes de uma transação específica
        """
        params = [
            signature,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed",
                "maxSupportedTransactionVersion": 0
            }
        ]
        
        return await self.rpc_request("getTransaction", params)
    
    async def get_account_info(self, address: str) -> Optional[Dict]:
        """
        Busca informações de uma conta
        """
        params = [
            address,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed"
            }
        ]
        
        return await self.rpc_request("getAccountInfo", params)
    
    async def extract_buyers_from_mint(self, mint_address: str) -> tuple[List[str], Dict]:
        """
        Extrai compradores de um token usando RPC direto da Solana (versão otimizada)
        Método alternativo quando API do Solscan não funciona
        """
        print(f"🔍 Buscando compradores via RPC Solana para: {mint_address}")
        print("⚡ Versão otimizada com menos requisições para evitar rate limiting")
        
        try:
            self.request_count = 0
            
            # Busca informações básicas do token (1 requisição)
            print("📊 Buscando informações do token...")
            token_info = {
                'name': 'Token Solana',
                'symbol': 'UNKNOWN', 
                'decimals': 9,
                'supply': '0'
            }
            
            self.request_count += 1
            await asyncio.sleep(RPC_REQUEST_DELAY * 2)  # Delay maior
            
            account_info = await self.get_account_info(mint_address)
            if account_info and account_info.get('value'):
                parsed_info = account_info['value'].get('data', {}).get('parsed', {}).get('info', {})
                token_info.update({
                    'decimals': parsed_info.get('decimals', 9),
                    'supply': parsed_info.get('supply', '0')
                })
                print(f"✅ Token info: {token_info.get('decimals', 9)} decimais")
            
            # Busca as maiores contas do token (1 requisição)
            print("🔎 Buscando maiores contas do token...")
            
            self.request_count += 1 
            await asyncio.sleep(RPC_REQUEST_DELAY * 2)  # Delay maior
            
            largest_accounts = await self.get_token_accounts_by_mint(mint_address)
            
            if not largest_accounts:
                print("❌ Nenhuma conta de token encontrada")
                print("💡 Possíveis motivos:")
                print("   - Token não existe na blockchain")  
                print("   - Endereço de token inválido")
                print("   - Token muito novo sem holders")
                return [], token_info
            
            print(f"✅ Encontradas {len(largest_accounts)} contas de token")
            
            buyers_list = []
            processed_owners = set()
            
            # DRASTICAMENTE REDUZIDO: apenas 2 contas para evitar rate limit
            max_accounts_to_process = min(2, len(largest_accounts))
            print(f"⚙️ Processando apenas {max_accounts_to_process} contas (mínimo para evitar rate limit)")
            
            # Para cada conta de token, busca apenas algumas transações
            for i, account in enumerate(largest_accounts[:max_accounts_to_process]):
                account_address = account.get('address')
                if not account_address:
                    continue
                
                print(f"📜 Conta {i+1}/{max_accounts_to_process}: {account_address[:8]}...")
                
                # LIMITE ULTRA REDUZIDO: apenas 10 transações
                self.request_count += 1
                await asyncio.sleep(RPC_REQUEST_DELAY * 3)  # Delay ainda maior
                
                signatures = await self.get_signatures_for_address(account_address, 10)
                
                if not signatures:
                    print(f"⚠️ Nenhuma transação encontrada para {account_address[:8]}")
                    continue
                
                print(f"✅ Encontradas {len(signatures)} transações")
                
                # Processa apenas as 3 transações mais antigas
                max_sigs_to_process = min(3, len(signatures))
                
                for j, sig_info in enumerate(reversed(signatures[-max_sigs_to_process:])):
                    try:
                        signature = sig_info.get('signature')
                        block_time = sig_info.get('blockTime', 0)
                        
                        if not signature:
                            continue
                        
                        print(f"🔍 Transação {j+1}/{max_sigs_to_process}...")
                        
                        self.request_count += 1
                        await asyncio.sleep(RPC_REQUEST_DELAY * 3)  # Delay grande
                        
                        # Busca detalhes da transação
                        tx_details = await self.get_transaction(signature)
                        
                        if not tx_details:
                            continue
                        
                        # Extrai wallets das contas envolvidas
                        transaction = tx_details.get('transaction', {})
                        message = transaction.get('message', {})
                        account_keys = message.get('accountKeys', [])
                        
                        # Adiciona as primeiras contas como possíveis compradores
                        for account_key in account_keys[:3]:  # Apenas 3 primeiras
                            if isinstance(account_key, str):
                                wallet = account_key
                            else:
                                wallet = account_key.get('pubkey', '')
                            
                            if (wallet and len(wallet) > 30 and 
                                wallet != mint_address and
                                wallet not in processed_owners):
                                
                                buyers_list.append(wallet)
                                processed_owners.add(wallet)
                                
                                print(f"✅ Wallet encontrada: {wallet[:8]}... (timestamp: {block_time})")
                                
                                if len(buyers_list) >= min(10, MAX_WALLETS_DISPLAY):
                                    print(f"🎯 Limite de wallets atingido!")
                                    break
                        
                        if len(buyers_list) >= min(10, MAX_WALLETS_DISPLAY):
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Erro ao processar transação: {e}")
                        continue
                
                if len(buyers_list) >= min(10, MAX_WALLETS_DISPLAY):
                    break
                
                # Delay grande entre contas
                print("⏳ Aguardando 3s entre contas...")
                await asyncio.sleep(3)
            
            print(f"🎉 Processo concluído! Encontradas {len(buyers_list)} wallets via RPC Solana")
            print(f"📊 Total de requisições feitas: {self.request_count}")
            
            return buyers_list, token_info
            
        except Exception as e:
            print(f"❌ Erro geral ao buscar compradores via RPC: {e}")
            return [], {}

# Instância global da RPC
solana_rpc = SolanaRPC()