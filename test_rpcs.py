#!/usr/bin/env python3
"""
Script para testar RPCs da Solana
"""

import asyncio
import aiohttp
import json
import time
from typing import List, Dict

# Lista de RPCs para testar
TEST_RPCS = [
    "http://103.219.168.143:8899/",
    "http://67.209.52.149:8899/",
    "http://67.209.52.93:8899/",
    "http://149.22.232.154:8899/",
    "http://194.126.172.254:8899/",
    "http://5.255.78.21:8899/",
    "http://62.113.194.72:8899/",
    "http://162.19.168.181:8899/",
    "http://168.119.210.168:8899/",
    "http://208.85.20.143:8899/",
    "http://5.199.172.134:8899/",
    "http://66.235.169.232:8899/",
    "http://38.32.103.29:8899/",
    "http://198.20.161.102:8899/",
    "http://45.250.254.119:8899/",
    "http://15.235.117.140:8899/",
    "http://38.55.75.19:8899/",
    "http://204.16.246.43:8899/",
    "http://144.202.55.165:8899/",
    "http://69.162.89.194:8899/",
    "http://108.171.203.218:8899/",
    "http://103.88.234.69:8899/",
    "http://103.219.170.117:8899/",
    "http://139.84.136.101:8899/",
    "http://216.144.245.202:8899/",
    "http://45.250.255.95:8899/",
    "http://8.222.245.91:8899/",
    "http://45.250.255.37:8899/",
    "http://45.250.255.94:8899/"
]

async def test_rpc(session: aiohttp.ClientSession, rpc_url: str, timeout: int = 5) -> Dict:
    """Testa um RPC específico"""
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getVersion",
        "params": []
    }
    
    start_time = time.time()
    
    try:
        async with session.post(
            rpc_url, 
            json=payload, 
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as response:
            
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)  # em ms
            
            if response.status == 200:
                data = await response.json()
                if 'result' in data and 'solana-core' in data['result']:
                    version = data['result']['solana-core']
                    return {
                        'url': rpc_url,
                        'status': 'SUCCESS',
                        'response_time': response_time,
                        'version': version,
                        'error': None
                    }
                else:
                    return {
                        'url': rpc_url,
                        'status': 'ERROR',
                        'response_time': response_time,
                        'version': None,
                        'error': 'Invalid response format'
                    }
            else:
                return {
                    'url': rpc_url,
                    'status': 'HTTP_ERROR',
                    'response_time': response_time,
                    'version': None,
                    'error': f'HTTP {response.status}'
                }
                
    except asyncio.TimeoutError:
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        return {
            'url': rpc_url,
            'status': 'TIMEOUT',
            'response_time': response_time,
            'version': None,
            'error': f'Timeout after {timeout}s'
        }
    except Exception as e:
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        return {
            'url': rpc_url,
            'status': 'EXCEPTION',
            'response_time': response_time,
            'version': None,
            'error': str(e)
        }

async def test_all_rpcs():
    """Testa todos os RPCs da lista"""
    
    print(f"🧪 Testando {len(TEST_RPCS)} RPCs da Solana...")
    print("=" * 80)
    
    results = []
    working_rpcs = []
    failed_rpcs = []
    
    async with aiohttp.ClientSession() as session:
        # Testa todos os RPCs em paralelo com limite
        semaphore = asyncio.Semaphore(10)  # Max 10 simultâneos
        
        async def test_with_semaphore(rpc_url):
            async with semaphore:
                return await test_rpc(session, rpc_url)
        
        # Executa testes em paralelo
        tasks = [test_with_semaphore(rpc_url) for rpc_url in TEST_RPCS]
        results = await asyncio.gather(*tasks)
    
    # Separa sucessos e falhas
    for result in results:
        if result['status'] == 'SUCCESS':
            working_rpcs.append(result)
        else:
            failed_rpcs.append(result)
    
    # Ordena por tempo de resposta (mais rápidos primeiro)
    working_rpcs.sort(key=lambda x: x['response_time'])
    
    # Mostra resultados
    print(f"\n✅ RPCs FUNCIONANDO ({len(working_rpcs)}):")
    print("-" * 80)
    
    if working_rpcs:
        for i, rpc in enumerate(working_rpcs, 1):
            print(f"{i:2d}. {rpc['url']:<30} | {rpc['response_time']:>6}ms | v{rpc['version']}")
    else:
        print("Nenhum RPC funcionando encontrado.")
    
    print(f"\n❌ RPCs COM PROBLEMAS ({len(failed_rpcs)}):")
    print("-" * 80)
    
    if failed_rpcs:
        for rpc in failed_rpcs:
            status_icon = {
                'TIMEOUT': '⏰',
                'HTTP_ERROR': '🔴',
                'ERROR': '⚠️',
                'EXCEPTION': '💥'
            }.get(rpc['status'], '❓')
            
            print(f"{status_icon} {rpc['url']:<30} | {rpc['response_time']:>6}ms | {rpc['error']}")
    
    print("\n" + "=" * 80)
    print(f"📊 RESUMO:")
    print(f"   ✅ Funcionando: {len(working_rpcs)}")
    print(f"   ❌ Com problemas: {len(failed_rpcs)}")
    print(f"   📈 Taxa de sucesso: {(len(working_rpcs)/len(TEST_RPCS)*100):.1f}%")
    
    # Gera lista para .env
    if working_rpcs:
        print(f"\n🔧 RPCS PARA USAR NO .env:")
        print("-" * 40)
        print("CUSTOM_RPC_URLS=" + ",".join([rpc['url'] for rpc in working_rpcs[:10]]))
        
        print(f"\n⚡ TOP 5 MAIS RÁPIDOS:")
        print("-" * 40)
        top5_urls = [rpc['url'] for rpc in working_rpcs[:5]]
        print("CUSTOM_RPC_URLS=" + ",".join(top5_urls))

if __name__ == "__main__":
    asyncio.run(test_all_rpcs())