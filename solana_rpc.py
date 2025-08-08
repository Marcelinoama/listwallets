import aiohttp
import asyncio
import json
import random
import time
from typing import List, Dict, Optional, Set
from config import SOLANA_RPC_URLS, MAX_WALLETS_DISPLAY, RPC_RETRY_ATTEMPTS, RPC_RETRY_DELAY, RPC_REQUEST_DELAY, RPC_CONFIGS
import base64
import base58

class SolanaRPC:
    def __init__(self):
        self.rpc_urls = SOLANA_RPC_URLS
        self.current_rpc_index = 0
        self.blacklisted_rpcs = {}  # RPC -> tempo_de_blacklist
        self.request_count = 0
        self.token_cache = {}  # Cache para consistência cronológica
        
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
    
    def is_using_premium_rpc(self) -> bool:
        """Verifica se está usando RPC premium (Tatum) atualmente"""
        try:
            current_rpc = self.rpc_urls[self.current_rpc_index % len(self.rpc_urls)]
            return current_rpc in RPC_CONFIGS
        except:
            return False
    
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
        Busca o saldo de SOL de uma wallet
        Retorna o saldo em SOL (convertido de lamports)
        """
        try:
            result = await self.rpc_request('getBalance', [wallet_address])
            if result and 'value' in result:
                lamports = result['value']
                # Converte lamports para SOL (1 SOL = 1,000,000,000 lamports)
                sol_balance = lamports / 1_000_000_000
                return sol_balance
        except Exception as e:
            print(f"⚠️ Erro ao buscar saldo: {e}")
        return 0.0
    
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
                    
                    # Verifica se este RPC precisa de headers especiais (ex: Tatum)
                    headers = {}
                    if rpc_url in RPC_CONFIGS:
                        headers = RPC_CONFIGS[rpc_url]['headers']
                        rpc_type = RPC_CONFIGS[rpc_url]['type']
                        if retry_attempt == 0:  # Log apenas na primeira tentativa
                            print(f"🔑 Usando RPC premium ({rpc_type}): {rpc_url[:30]}...")
                    
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                        async with session.post(rpc_url, json=payload, headers=headers) as response:
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
        
        # Se falhou, verifica se o token existe
        basic_info = await self.rpc_request("getAccountInfo", [mint_address, {"encoding": "jsonParsed"}])
        
        if basic_info and basic_info.get('value'):
            print(f"⚠️ Token existe mas não tem holders significativos")
        else:
            print(f"❌ Token não encontrado na blockchain")
        
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
        
        # Ordena signatures por blockTime (das mais antigas para as mais novas) para ordem cronológica consistente
        if result:
            # Filtra signatures que têm blockTime e ordena cronologicamente
            signatures_with_time = [sig for sig in result if sig.get('blockTime')]
            signatures_with_time.sort(key=lambda x: x.get('blockTime', 0))
            print(f"📅 Signatures ordenadas cronologicamente: {len(signatures_with_time)} de {len(result)}")
            return signatures_with_time
        
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
    
    async def get_token_metadata_jupiter(self, mint_address: str) -> Dict:
        """
        Busca metadados do token usando a API do Jupiter
        Retorna informações como nome, símbolo e outras propriedades
        """
        try:
            url = f"https://tokens.jup.ag/token/{mint_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"✅ Jupiter API: Metadados encontrados para {mint_address[:8]}...")
                        return {
                            'name': data.get('name', 'Token Solana'),
                            'symbol': data.get('symbol', 'UNKNOWN'),
                            'decimals': data.get('decimals', 9),
                            'logoURI': data.get('logoURI', ''),
                            'tags': data.get('tags', [])
                        }
                    else:
                        print(f"⚠️ Jupiter API: Token não encontrado (status {response.status})")
                        return {}
                        
        except Exception as e:
            print(f"⚠️ Erro ao buscar metadados via Jupiter API: {e}")
            return {}
    
    async def extract_buyers_from_mint(self, mint_address: str) -> tuple[List[str], Dict]:
        """
        Extrai compradores de um token usando RPC direto da Solana (versão otimizada)
        Método alternativo quando API do Solscan não funciona
        """
        print(f"🔍 Buscando compradores via RPC Solana para: {mint_address}")
        print("⚡ Versão otimizada com menos requisições para evitar rate limiting")
        
        try:
            self.request_count = 0
            
            # Busca informações básicas do token via Jupiter API primeiro
            print("📊 Buscando metadados do token via Jupiter API...")
            jupiter_metadata = await self.get_token_metadata_jupiter(mint_address)
            
            # Informações básicas do token (com metadados do Jupiter se disponível)
            token_info = {
                'name': jupiter_metadata.get('name', 'Token Solana'),
                'symbol': jupiter_metadata.get('symbol', 'UNKNOWN'), 
                'decimals': jupiter_metadata.get('decimals', 9),
                'supply': '0',
                'logoURI': jupiter_metadata.get('logoURI', ''),
                'tags': jupiter_metadata.get('tags', [])
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
                return [], token_info, []
            
            print(f"✅ Encontradas {len(largest_accounts)} contas de token")
            
            buyers_list = []
            buyers_with_balance = []  # Lista com wallets e saldos
            processed_owners = set()
            
            # Calcula quantas contas processar - mais agressivo com RPC premium
            if self.is_using_premium_rpc():
                # RPC premium: sem limitações, pode processar muito mais
                accounts_needed = min(20, len(largest_accounts), MAX_WALLETS_DISPLAY // 2)
                print(f"⭐ RPC Premium detectado - processamento acelerado!")
            else:
                # RPC gratuito: limitações para evitar rate limiting
                accounts_needed = max(3, min(10, (MAX_WALLETS_DISPLAY // 3) + 2))
                print(f"⚙️ RPC gratuito - processamento conservador")
            
            max_accounts_to_process = min(accounts_needed, len(largest_accounts))
            print(f"⚙️ Processando {max_accounts_to_process} contas para buscar {MAX_WALLETS_DISPLAY} wallets")
            
            # Para cada conta de token, busca apenas algumas transações
            for i, account in enumerate(largest_accounts[:max_accounts_to_process]):
                # account é um dicionário com chaves: address, amount, decimals, uiAmount, uiAmountString
                account_address = account.get('address') if isinstance(account, dict) else None
                if not account_address:
                    print(f"⚠️ Conta {i+1} sem endereço válido: {account}")
                    continue
                
                print(f"📜 Conta {i+1}/{max_accounts_to_process}: {account_address[:8]}...")
                
                # Busca signatures para a conta
                self.request_count += 1
                
                # Delay otimizado baseado no tipo de RPC
                if self.is_using_premium_rpc():
                    await asyncio.sleep(0.2)  # RPC premium: delay mínimo
                    signatures_limit = min(100, MAX_WALLETS_DISPLAY)  # Mais signatures
                else:
                    await asyncio.sleep(RPC_REQUEST_DELAY * 3)  # RPC gratuito: delay maior
                    signatures_limit = max(10, min(50, MAX_WALLETS_DISPLAY // 2))
                
                signatures = await self.get_signatures_for_address(account_address, signatures_limit)
                
                if not signatures:
                    print(f"⚠️ Nenhuma transação encontrada para {account_address[:8]}")
                    continue
                
                print(f"✅ Encontradas {len(signatures)} transações")
                
                # Calcula quantas transações processar - otimizado para premium
                if self.is_using_premium_rpc():
                    # RPC premium: processa mais transações
                    sigs_needed = min(20, len(signatures), MAX_WALLETS_DISPLAY // max_accounts_to_process + 5)
                else:
                    # RPC gratuito: limitado
                    sigs_needed = max(3, min(10, MAX_WALLETS_DISPLAY // max_accounts_to_process))
                
                max_sigs_to_process = min(sigs_needed, len(signatures))
                
                # Processa signatures em ordem cronológica (já ordenadas das mais antigas para mais novas)
                for j, sig_info in enumerate(signatures[:max_sigs_to_process]):
                    try:
                        signature = sig_info.get('signature')
                        block_time = sig_info.get('blockTime', 0)
                        
                        if not signature:
                            continue
                        
                        print(f"🔍 Transação {j+1}/{max_sigs_to_process}...")
                        
                        self.request_count += 1
                        
                        # Delay otimizado para premium
                        if self.is_using_premium_rpc():
                            await asyncio.sleep(0.1)  # RPC premium: super rápido
                        else:
                            await asyncio.sleep(RPC_REQUEST_DELAY * 3)  # RPC gratuito: delay grande
                        
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
                            
                            # Usa o filtro robusto para validar wallets
                            if (wallet and 
                                self.is_valid_user_wallet(wallet, mint_address) and
                                wallet not in processed_owners):
                                
                                # Busca saldo da wallet
                                print(f"💰 Buscando saldo para: {wallet[:8]}...")
                                balance = await self.get_wallet_balance(wallet)
                                
                                # Timestamp mais preciso e estável
                                final_timestamp = block_time if block_time > 0 else int(time.time())
                                
                                buyers_list.append(wallet)
                                buyers_with_balance.append({
                                    'wallet': wallet,
                                    'balance': balance,
                                    'timestamp': final_timestamp,
                                    'account_index': i,  # Índice da conta processada
                                    'sig_index': j       # Índice da signature processada
                                })
                                processed_owners.add(wallet)
                                
                                print(f"✅ Wallet: {wallet[:8]}... | Saldo: {balance:.2f} | TS: {final_timestamp} | Conta: {i} | Sig: {j}")
                                
                                if len(buyers_list) >= MAX_WALLETS_DISPLAY:
                                    print(f"🎯 Limite de wallets atingido!")
                                    break
                                    
                            elif wallet and wallet in self.SYSTEM_PROGRAMS:
                                print(f"🔧 Programa filtrado: {wallet[:8]}... (sistema Solana)")
                        
                        if len(buyers_list) >= MAX_WALLETS_DISPLAY:
                            break
                            
                    except Exception as e:
                        print(f"⚠️ Erro ao processar transação: {e}")
                        continue
                
                if len(buyers_list) >= MAX_WALLETS_DISPLAY:
                    break
                
                # Delay otimizado entre contas
                if self.is_using_premium_rpc():
                    print("⏳ RPC premium: delay mínimo...")
                    await asyncio.sleep(0.3)  # Premium: delay mínimo
                else:
                    print("⏳ Aguardando 3s entre contas...")
                    await asyncio.sleep(3)  # Gratuito: delay grande
            
            # ORDENAÇÃO CRONOLÓGICA ROBUSTA E DETERMINÍSTICA
            if buyers_with_balance:
                print(f"🔄 APLICANDO ORDENAÇÃO CRONOLÓGICA DETERMINÍSTICA...")
                
                # Ordena por timestamp, índice da conta, índice da signature e wallet (100% determinístico)
                buyers_with_balance.sort(key=lambda x: (
                    x.get('timestamp', 0), 
                    x.get('account_index', 0), 
                    x.get('sig_index', 0), 
                    x.get('wallet', '')
                ))
                buyers_list = [item['wallet'] for item in buyers_with_balance]
                
                print(f"📅 {len(buyers_with_balance)} wallets ordenadas cronologicamente")
                print(f"🎯 VERIFICAÇÃO DE CONSISTÊNCIA CRONOLÓGICA:")
                
                # Log DETALHADO das primeiras 5 wallets com timestamps
                for i, item in enumerate(buyers_with_balance[:min(5, len(buyers_with_balance))], 1):
                    ts = item.get('timestamp', 0)
                    wallet = item.get('wallet', '')
                    
                    # Converte timestamp para data legível (se > 0)
                    if ts > 0:
                        from datetime import datetime
                        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                        print(f"⏰ {i}. {wallet[:12]}... | TS: {ts} | Data: {date_str}")
                    else:
                        print(f"⏰ {i}. {wallet[:12]}... | TS: {ts} | Data: SEM TIMESTAMP")
                
                # Cache do resultado para consistência
                cache_key = f"{mint_address}_{len(buyers_with_balance)}"
                self.token_cache[cache_key] = buyers_with_balance.copy()
                print(f"💾 Resultado cacheado: {cache_key}")
            
            print(f"🎉 Processo concluído! Encontradas {len(buyers_list)} wallets via RPC Solana")
            print(f"📊 Total de requisições feitas: {self.request_count}")
            
            # Retorna tanto a lista simples quanto os dados detalhados com saldos
            return buyers_list, token_info, buyers_with_balance
            
        except Exception as e:
            print(f"❌ Erro geral ao buscar compradores via RPC: {e}")
            return [], {}, []

# Instância global da RPC
solana_rpc = SolanaRPC()