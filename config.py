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

# RPCs customizados (prioridade se configurados)
CUSTOM_RPC_URLS_STRING = os.getenv('CUSTOM_RPC_URLS', '').strip()

# URLs RPC da Solana padrão (testadas e funcionais)
_DEFAULT_RPC_URLS = [
    "https://api.mainnet-beta.solana.com",  # ✅ Testado - 47ms
    "https://api.devnet.solana.com",        # ✅ Testado - 299ms (backup)
    
    # RPCs abaixo têm limitações (rate limit, API key, etc)
    # Mantidos como fallback final
    "https://solana-api.projectserum.com", 
    "https://rpc.ankr.com/solana",
    "https://solana-mainnet.g.alchemy.com/v2/demo",
    "https://mainnet.helius-rpc.com/?api-key=demo",
    "https://rpc.solana.com"
]

# Processa RPCs customizados separados por vírgula
CUSTOM_RPC_URLS = []
if CUSTOM_RPC_URLS_STRING:
    # Divide por vírgula e limpa espaços
    custom_urls = [url.strip() for url in CUSTOM_RPC_URLS_STRING.split(',') if url.strip()]
    CUSTOM_RPC_URLS = custom_urls
    print(f"🚀 {len(CUSTOM_RPC_URLS)} RPCs customizados configurados:")
    for i, url in enumerate(CUSTOM_RPC_URLS, 1):
        print(f"   {i}. {url}")

# Combina RPCs customizados (se configurados) com RPCs padrão
SOLANA_RPC_URLS = CUSTOM_RPC_URLS + _DEFAULT_RPC_URLS

# Configurações para rate limiting (lidas do .env ou valores padrão)
# AUMENTADOS para evitar rate limiting
RPC_RETRY_ATTEMPTS = int(os.getenv('RPC_RETRY_ATTEMPTS', '2'))  # Reduzido de 3 para 2
RPC_RETRY_DELAY = float(os.getenv('RPC_RETRY_DELAY', '3.0'))  # Aumentado de 2 para 3 segundos  
RPC_REQUEST_DELAY = float(os.getenv('RPC_REQUEST_DELAY', '1.5'))  # Aumentado de 0.5 para 1.5 segundos

# Configurações do bot (lidas do .env ou valores padrão)
MAX_WALLETS_DISPLAY = int(os.getenv('MAX_WALLETS_DISPLAY', '50'))  # Máximo de wallets para exibir
CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '300'))  # Timeout do cache em segundos