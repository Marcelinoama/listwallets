#!/usr/bin/env python3
"""
Script de inicialização do ListWallet Bot

Este script verifica as configurações e inicia o bot.
"""

import os
import sys

def check_requirements():
    """Verifica se os requisitos estão instalados"""
    try:
        import telegram
        import aiohttp
        import requests
        print("✅ Todas as dependências estão instaladas")
        return True
    except ImportError as e:
        print(f"❌ Dependência não encontrada: {e}")
        print("💡 Execute: pip install -r requirements.txt")
        return False

def check_token():
    """Verifica se o token do bot está configurado"""
    from config import TELEGRAM_BOT_TOKEN
    
    if TELEGRAM_BOT_TOKEN == "SEU_TOKEN_AQUI":
        print("❌ Token do bot não configurado!")
        print("💡 Configure o TELEGRAM_BOT_TOKEN no arquivo config.py ou crie um arquivo .env")
        print("📱 Obtenha o token no @BotFather do Telegram")
        return False
    
    print("✅ Token do bot configurado")
    return True

def main():
    """Função principal"""
    print("🤖 ListWallet Bot - Verificando configurações...\n")
    
    # Verifica dependências
    if not check_requirements():
        sys.exit(1)
    
    # Verifica token
    if not check_token():
        sys.exit(1)
    
    print("\n🚀 Iniciando o bot...")
    
    # Importa e executa o bot
    try:
        from bot import ListWalletBot
        bot = ListWalletBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Bot interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao executar o bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()