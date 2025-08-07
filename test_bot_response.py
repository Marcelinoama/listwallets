#!/usr/bin/env python3
"""
Teste simplificado para verificar se o bot consegue responder
"""

import asyncio
from solscan_api import solscan_api

async def test_bot_flow():
    """Simula o fluxo do bot"""
    
    print("🧪 TESTANDO FLUXO COMPLETO DO BOT")
    print("=" * 50)
    
    # Token de teste (use um token real da Solana)
    test_token = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    
    try:
        print(f"1. 🔍 Validando token: {test_token}")
        if not solscan_api.validate_token_address(test_token):
            print("❌ Token inválido")
            return
        print("✅ Token válido")
        
        print("\n2. 🔎 Buscando compradores...")
        buyers, token_info = await solscan_api.extract_buyers(test_token)
        
        print(f"\n3. 📊 Resultado da busca:")
        print(f"   - Wallets encontradas: {len(buyers)}")
        print(f"   - Token info: {token_info}")
        
        if buyers:
            print(f"\n4. 💰 Primeiras wallets:")
            for i, wallet in enumerate(buyers[:3], 1):
                print(f"   {i}. {wallet}")
        
        print("\n5. 📝 Montando resposta do bot...")
        
        # Simula a montagem da resposta
        from config import MAX_WALLETS_DISPLAY
        
        token_name = token_info.get('name', 'Token Desconhecido')
        token_symbol = token_info.get('symbol', 'N/A')
        
        result_text = f"✅ **Análise Concluída**\n\n"
        result_text += f"🪙 **Token:** {token_name} ({token_symbol})\n"
        result_text += f"📝 **Endereço:** `{test_token}`\n"
        result_text += f"👥 **Primeiros compradores:** {len(buyers)}/{MAX_WALLETS_DISPLAY}\n"
        result_text += f"⏰ **Ordem:** Cronológica (primeiro → último)\n\n"
        
        if buyers:
            result_text += "🥇 **Primeiras wallets que compraram:**\n"
            for i, wallet in enumerate(buyers[:5], 1):
                result_text += f"`{i:2d}.` `{wallet}`\n"
        else:
            result_text += "❌ **Nenhuma wallet encontrada**"
        
        print(f"\n6. 📤 Resposta pronta ({len(result_text)} caracteres):")
        print("-" * 50)
        print(result_text)
        print("-" * 50)
        
        print("\n✅ TESTE COMPLETO - SEM ERROS!")
        print("O problema pode estar na comunicação com o Telegram")
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot_flow())