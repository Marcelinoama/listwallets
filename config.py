import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Token do bot do Telegram (obtenha no @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'SEU_TOKEN_AQUI')

# URL base da API do Solscan (PRO - requer API key)
SOLSCAN_API_BASE = "https://pro-api.solscan.io/v2.0"
SOLSCAN_PRO_API_KEY = os.getenv('SOLSCAN_PRO_API_KEY', '')

# Headers para requisições à API do Solscan Pro
SOLSCAN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'token': SOLSCAN_PRO_API_KEY
}

# Configuração simplificada - APENAS HELIUS
# RPC Helius Fast (testado e funcional)
HELIUS_RPC_URL = "https://rahel-v0lqwp-fast-mainnet.helius-rpc.com/"

print(f"🚀 Configuração simplificada: APENAS Helius")
print(f"🔑 RPC único: rahel-v0lqwp-fast-mainnet.helius-rpc.com")
print(f"✅ Funcionalidade: Busca de tokens FUNCIONANDO")

# Lista de RPCs simplificada - APENAS HELIUS
SOLANA_RPC_URLS = [HELIUS_RPC_URL]

# Configurações especiais por RPC (vazio para Helius)
RPC_CONFIGS = {}

# Configurações otimizadas para Helius (sem limitações de velocidade)
RPC_RETRY_ATTEMPTS = int(os.getenv('RPC_RETRY_ATTEMPTS', '1'))  # Tentativa única - Helius é confiável
RPC_RETRY_DELAY = float(os.getenv('RPC_RETRY_DELAY', '0.1'))  # Delay mínimo entre tentativas
RPC_REQUEST_DELAY = float(os.getenv('RPC_REQUEST_DELAY', '0.0'))  # SEM delay entre requisições

# Configurações do bot (lidas do .env ou valores padrão)
MAX_WALLETS_DISPLAY = int(os.getenv('MAX_WALLETS_DISPLAY', '50'))  # Máximo de wallets para exibir
CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '300'))  # Timeout do cache em segundos