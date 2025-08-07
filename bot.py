import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from solscan_api import solscan_api
from config import TELEGRAM_BOT_TOKEN

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ListWalletBot:
    def __init__(self):
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura os handlers do bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        welcome_text = """
🔍 **Bot de Busca de Wallets - Solana**

Bem-vindo! Este bot encontra as **primeiras wallets** que compraram um token específico na blockchain Solana.

📝 **Como usar:**
1. Envie o endereço do token que você quer analisar
2. Aguarde enquanto busco as transações no Solscan
3. Receba a lista em **ordem cronológica** (primeiro → último)

⚙️ **Configurável:**
- Número de wallets configurável no arquivo .env
- Padrão: 50 primeiras wallets que compraram

💡 **Exemplo de token:**
`So11111111111111111111111111111111111111112`

Digite /help para mais informações.
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        # Verifica qual fonte está configurada
        from config import SOLSCAN_PRO_API_KEY
        fonte_config = "✅ API Pro Solscan (configurada)" if SOLSCAN_PRO_API_KEY else "⚡ RPC Solana (gratuito)"
        
        help_text = f"""
📖 **Ajuda - Bot de Busca de Wallets**

🔗 **Formato do Token:**
- O endereço deve ser um token válido da Solana
- Geralmente tem entre 32-44 caracteres
- Exemplo: `So11111111111111111111111111111111111111112`

⚙️ **Funcionalidades:**
- Busca as primeiras wallets que compraram o token
- **Ordem cronológica:** do primeiro ao último comprador
- Número configurável no arquivo .env (MAX_WALLETS_DISPLAY)
- Mostra informações básicas do token
- Fonte atual: {fonte_config}

📊 **Configuração:**
- Edite MAX_WALLETS_DISPLAY no arquivo .env
- Padrão: 50 wallets (primeiras que compraram)
- Ordem: cronológica (primeiro → último)
- SOLSCAN_PRO_API_KEY (opcional): Para melhor performance

🔄 **Fontes de Dados:**
- **API Pro Solscan**: Rápida, requer API key paga
- **RPC Solana**: Gratuita, pode ser mais lenta
- O bot escolhe automaticamente a melhor disponível

🚫 **Limitações:**
- Performance varia conforme a fonte de dados
- Pode haver delay em tokens muito populares
- Ordem baseada no timestamp das transações

❓ **Problemas comuns:**
- "Token não encontrado": Verifique se o endereço está correto
- "Sem compradores": Token pode ser muito novo ou sem transações
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto (endereços de token)"""
        user_input = update.message.text.strip()
        
        # Valida se parece com um endereço de token
        if not solscan_api.validate_token_address(user_input):
            error_msg = f"❌ **Endereço de Token Inválido**\n\n"
            
            # Diagnóstico específico do erro
            if len(user_input) < 32:
                error_msg += f"🔍 **Problema:** Endereço muito curto ({len(user_input)} caracteres)\n"
                error_msg += f"📏 **Necessário:** 32-44 caracteres\n\n"
            elif len(user_input) > 44:
                error_msg += f"🔍 **Problema:** Endereço muito longo ({len(user_input)} caracteres)\n"
                error_msg += f"📏 **Necessário:** 32-44 caracteres\n\n"
            elif user_input.startswith('0x'):
                error_msg += f"🔍 **Problema:** Este parece ser um endereço Ethereum\n"
                error_msg += f"🌐 **Rede:** Este bot funciona apenas com tokens Solana\n\n"
            else:
                error_msg += f"🔍 **Problema:** Caracteres inválidos no endereço\n"
                error_msg += f"✅ **Válidos:** Apenas caracteres Base58 (1-9, A-H, J-N, P-Z, a-k, m-z)\n\n"
            
            error_msg += f"💡 **Exemplo de token Solana válido:**\n"
            error_msg += f"`So11111111111111111111111111111111111111112`\n\n"
            error_msg += f"🔗 **Encontre tokens em:** solscan.io"
            
            try:
                await update.message.reply_text(error_msg, parse_mode='Markdown')
            except:
                # Fallback simples sem Markdown
                simple_error = f"❌ ENDEREÇO DE TOKEN INVÁLIDO\n\n"
                simple_error += f"Problema: {user_input[:50]}...\n\n"
                simple_error += f"Exemplo válido:\n"
                simple_error += f"So11111111111111111111111111111111111111112\n\n"
                simple_error += f"Encontre tokens em: solscan.io"
                await update.message.reply_text(simple_error)
            return
        
        # Verifica qual fonte será usada
        from config import SOLSCAN_PRO_API_KEY
        fonte_info = "🔗 Fonte: API Pro Solscan" if SOLSCAN_PRO_API_KEY else "🔗 Fonte: RPC Solana (gratuito)"
        
        # Envia mensagem de processamento
        processing_msg = await update.message.reply_text(
            "🔍 **Buscando wallets...**\n\n"
            f"{fonte_info}\n"
            "⏳ Analisando transações na blockchain...\n"
            "⚡ **Versão otimizada** - pode levar 1-2 minutos\n"
            "🛡️ Delays anti-rate-limiting aplicados",
            parse_mode='Markdown'
        )
        
        try:
            print(f"🔍 Iniciando busca para token: {user_input}")
            
            # Busca as wallets que compraram o token (agora com saldos)
            try:
                buyers, token_info, balance_info = await solscan_api.extract_buyers(user_input)
            except ValueError:
                # Fallback para compatibilidade
                buyers, token_info = await solscan_api.extract_buyers(user_input)
                balance_info = []
            
            print(f"📊 Busca concluída: {len(buyers)} wallets encontradas")
            
            # Edita a mensagem com os resultados (incluindo saldos)
            await self.send_results(update, processing_msg, user_input, buyers, token_info, balance_info)
            
            print("✅ Processo completo finalizado")
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO ao processar token {user_input}: {e}")
            logger.error(f"Erro ao processar token {user_input}: {e}")
            
            try:
                await processing_msg.edit_text(
                    "❌ **Erro ao buscar dados**\n\n"
                    f"Erro: {str(e)[:100]}\n\n"
                    "Tente novamente em alguns minutos.",
                    parse_mode='Markdown'
                )
            except Exception as e2:
                print(f"❌ Erro ao enviar mensagem de erro: {e2}")
                # Última tentativa
                try:
                    await update.message.reply_text(
                        f"❌ Erro ao processar token: {str(e)[:100]}"
                    )
                except:
                    print("❌ Falha total na comunicação com Telegram")
    
    async def send_results(self, update, processing_msg, token_address, buyers, token_info, balance_info=None):
        """Envia os resultados da busca"""
        if not buyers:
            # Importa a configuração atual
            from config import MAX_WALLETS_DISPLAY
            
            # Mensagem mais clara para tokens não encontrados
            error_text = f"❌ **Token Não Encontrado**\n\n"
            error_text += f"🪙 **Endereço:** `{token_address[:20]}...`\n\n"
            error_text += f"💡 **Possíveis motivos:**\n"
            error_text += f"• Token não existe na blockchain Solana\n"
            error_text += f"• Endereço de token inválido\n"
            error_text += f"• Token muito novo sem holders\n"
            error_text += f"• Token sem transações registradas\n\n"
            error_text += f"🔍 **Verifique:**\n"
            error_text += f"• Se o endereço está completo e correto\n"
            error_text += f"• Se é um token da rede Solana (não Ethereum)\n"
            error_text += f"• Se o token realmente existe no Solscan"
            
            try:
                await processing_msg.edit_text(error_text, parse_mode='Markdown')
                print(f"✅ Mensagem de token não encontrado enviada")
            except Exception as e:
                # Fallback simples
                simple_msg = f"❌ TOKEN NÃO ENCONTRADO\n\n"
                simple_msg += f"Endereço: {token_address[:30]}...\n\n"
                simple_msg += f"Possíveis motivos:\n"
                simple_msg += f"- Token não existe na Solana\n"
                simple_msg += f"- Endereço inválido\n"
                simple_msg += f"- Token muito novo\n\n"
                simple_msg += f"Verifique o endereço e tente novamente."
                
                try:
                    await processing_msg.edit_text(simple_msg)
                    print("✅ Mensagem simples de erro enviada")
                except Exception as e2:
                    print(f"❌ Erro ao enviar mensagem de erro: {e2}")
            return
        
        # Informações do token
        token_name = token_info.get('name', 'Desconhecido')
        token_symbol = token_info.get('symbol', 'N/A')
        
        # Importa a configuração atual
        from config import MAX_WALLETS_DISPLAY
        
        # Monta o texto com os resultados
        result_text = f"✅ **Análise Concluída**\n\n"
        result_text += f"🪙 **Token:** {token_name} ({token_symbol})\n"
        result_text += f"📝 **Endereço:** `{token_address}`\n"
        result_text += f"👥 **Primeiros compradores:** {len(buyers)}/{MAX_WALLETS_DISPLAY}\n"
        result_text += f"⏰ **Ordem:** Cronológica (primeiro → último)\n\n"
        
        # VERSÃO SIMPLIFICADA para evitar problemas de Markdown
        result_text += "🥇 PRIMEIRAS WALLETS QUE COMPRARAM:\n\n"
        
        # Mostra TODAS as wallets encontradas com saldos em formato monospace
        if balance_info and len(balance_info) > 0:
            # Usa dados detalhados com saldo
            for i, wallet_data in enumerate(balance_info, 1):
                wallet = wallet_data.get('wallet', '')
                balance = wallet_data.get('balance', 0.0)
                result_text += f"{i}. `{wallet}` **{balance:.2f}**\n"
        else:
            # Fallback: busca saldos das wallets na hora (mais lento)
            from solana_rpc import solana_rpc
            print("💰 Buscando saldos das wallets...")
            for i, wallet in enumerate(buyers, 1):
                try:
                    balance = await solana_rpc.get_wallet_balance(wallet)
                    result_text += f"{i}. `{wallet}` **{balance:.2f}**\n"
                    print(f"💰 Wallet {i}: {balance:.2f}")
                except:
                    result_text += f"{i}. `{wallet}` **0.00**\n"
        
        result_text += f"\n🎯 **Total:** {len(buyers)} wallets em ordem cronológica"
        
        # REMOVE BOTÕES temporariamente para evitar problemas
        reply_markup = None
        
        try:
            # Primeira tentativa: com Markdown
            await processing_msg.edit_text(result_text, parse_mode='Markdown', reply_markup=reply_markup)
            print(f"✅ Resposta enviada com sucesso! {len(buyers)} wallets")
        except Exception as e:
            print(f"❌ Erro ao enviar resposta com Markdown: {e}")
            
            # Segunda tentativa: sem Markdown
            try:
                # Remove caracteres especiais do Markdown
                simple_text = result_text.replace('**', '').replace('`', '').replace('*', '')
                await processing_msg.edit_text(simple_text, reply_markup=reply_markup)
                print("✅ Resposta enviada sem Markdown")
            except Exception as e2:
                print(f"❌ Erro ao editar mensagem: {e2}")
                
                # Terceira tentativa: nova mensagem simples com TODAS as wallets e saldos
                try:
                    simple_msg = f"✅ ENCONTRADAS {len(buyers)} WALLETS:\n\n"
                    
                    if balance_info and len(balance_info) > 0:
                        # Usa dados com saldo se disponível (monospace)
                        for i, wallet_data in enumerate(balance_info, 1):
                            wallet = wallet_data.get('wallet', '')
                            balance = wallet_data.get('balance', 0.0)
                            simple_msg += f"{i}. {wallet} {balance:.2f}\n"
                    else:
                        # Fallback sem saldo (monospace)
                        for i, wallet in enumerate(buyers, 1):
                            simple_msg += f"{i}. {wallet} Saldo não disponível\n"
                            
                    simple_msg += f"\nTotal: {len(buyers)} wallets com saldos"
                    
                    await update.message.reply_text(simple_msg)
                    print("✅ Resposta enviada com todas as wallets e saldos")
                except Exception as e3:
                    print(f"❌ Erro total na comunicação: {e3}")
                    return
        
        # Armazena os dados no contexto para callbacks
        try:
            # Usa o bot da mensagem de processamento
            bot = processing_msg.bot if hasattr(processing_msg, 'bot') else context.bot
            if not hasattr(bot, '_wallet_cache'):
                bot._wallet_cache = {}
            bot._wallet_cache[token_address] = buyers
            print(f"✅ Cache armazenado para {len(buyers)} wallets")
        except Exception as e:
            print(f"⚠️ Erro ao armazenar cache: {e}")
            # Não é crítico, continua mesmo sem cache
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa callbacks dos botões"""
        query = update.callback_query
        await query.answer()
        
        action, token_address = query.data.split(':', 1)
        
        # Recupera os dados do cache
        try:
            cache = getattr(context.bot, '_wallet_cache', {})
            buyers = cache.get(token_address, [])
            print(f"📋 Cache recuperado: {len(buyers)} wallets para {token_address[:8]}...")
        except Exception as e:
            print(f"⚠️ Erro ao recuperar cache: {e}")
            buyers = []
        
        if action == "full_list":
            await self.show_full_list(query, token_address, buyers)
        elif action == "download":
            await self.send_download(query, token_address, buyers)
    
    async def show_full_list(self, query, token_address, buyers):
        """Mostra a lista completa de wallets"""
        if not buyers:
            await query.edit_message_text("❌ Dados não encontrados no cache.")
            return
        
        # Divide a lista em páginas
        page_size = 30
        pages = [buyers[i:i + page_size] for i in range(0, len(buyers), page_size)]
        
        # Importa a configuração atual
        from config import MAX_WALLETS_DISPLAY
        
        text = f"📋 **Lista Completa - Página 1/{len(pages)}**\n\n"
        text += f"🪙 **Token:** `{token_address[:16]}...`\n"
        text += f"👥 **Total:** {len(buyers)}/{MAX_WALLETS_DISPLAY} wallets\n"
        text += f"⏰ **Ordem:** Cronológica (primeiro → último)\n\n"
        
        for i, wallet in enumerate(pages[0], 1):
            text += f"`{i:2d}.` `{wallet}`\n"
        
        keyboard = []
        if len(pages) > 1:
            keyboard.append([InlineKeyboardButton("➡️ Próxima", callback_data=f"page:1:{token_address}")])
        keyboard.append([InlineKeyboardButton("⬅️ Voltar", callback_data=f"back:{token_address}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def send_download(self, query, token_address, buyers):
        """Envia arquivo TXT com a lista completa"""
        if not buyers:
            await query.edit_message_text("❌ Dados não encontrados no cache.")
            return
        
        # Cria conteúdo do arquivo
        content = f"Lista de Wallets que compraram o token: {token_address}\n"
        content += f"Total: {len(buyers)} wallets\n"
        content += f"Gerado em: {asyncio.get_event_loop().time()}\n\n"
        
        for i, wallet in enumerate(buyers, 1):
            content += f"{i:3d}. {wallet}\n"
        
        # Salva arquivo temporário
        filename = f"wallets_{token_address[:8]}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Envia o arquivo
        await query.message.reply_document(
            document=open(filename, 'rb'),
            filename=filename,
            caption=f"📄 Lista completa de {len(buyers)} wallets"
        )
        
        # Remove arquivo temporário
        import os
        os.remove(filename)
    
    def run(self):
        """Inicia o bot"""
        print("🤖 Iniciando bot de busca de wallets...")
        print(f"🔗 Conectando com token: {TELEGRAM_BOT_TOKEN[:10]}...")
        self.app.run_polling()

if __name__ == "__main__":
    if TELEGRAM_BOT_TOKEN == "SEU_TOKEN_AQUI":
        print("❌ Erro: Configure o TELEGRAM_BOT_TOKEN no arquivo config.py ou .env")
        exit(1)
    
    bot = ListWalletBot()
    bot.run()