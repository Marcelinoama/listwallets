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
        # Armazena configurações de saldo mínimo por usuário
        self.user_min_balance = {}  # user_id -> min_balance_sol
        # Armazena estado do comando samewallets por usuário
        self.samewallets_waiting = {}  # user_id -> True (aguardando tokens)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Configura os handlers do bot"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("balance", self.balance_command))
        self.app.add_handler(CommandHandler("samewallets", self.samewallets_command))
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

💰 **Filtro de saldo:** Use `/balance 2` para mostrar apenas wallets com 2+ SOL
🔍 **Wallets comuns:** Use `/samewallets tokenA tokenB` para encontrar holders múltiplos

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
- **Filtro de saldo:** `/balance X` para mostrar apenas wallets com X+ SOL
- **Wallets comuns:** `/samewallets` para encontrar holders de múltiplos tokens
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
- RPC Helius otimizado para máxima velocidade
- Ordem baseada no timestamp das transações

❓ **Problemas comuns:**
- "Token não encontrado": Verifique se o endereço está correto
- "Sem compradores": Token pode ser muito novo ou sem transações
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance para definir saldo mínimo de SOL"""
        user_id = update.effective_user.id
        
        # Se não há argumentos, mostra o valor atual
        if not context.args:
            current_balance = self.user_min_balance.get(user_id, 0.0)
            status_text = f"""
💰 **Filtro de Saldo Mínimo**

🔧 **Configuração Atual:**
• Saldo mínimo: {current_balance} SOL
• Status: {'✅ Ativo' if current_balance > 0 else '❌ Desativado'}

📝 **Como usar:**
• `/balance 2` - Define saldo mínimo de 2 SOL
• `/balance 0.5` - Define saldo mínimo de 0.5 SOL  
• `/balance 0` - Desativa o filtro (padrão)

💡 **Exemplo:**
Com `/balance 2`, apenas wallets com 2+ SOL aparecerão nos resultados.
            """
            await update.message.reply_text(status_text, parse_mode='Markdown')
            return
        
        # Valida e define o novo valor
        try:
            min_balance = float(context.args[0])
            
            if min_balance < 0:
                await update.message.reply_text(
                    "❌ **Erro:** O saldo mínimo não pode ser negativo.\n"
                    "Use `/balance 0` para desativar o filtro.",
                    parse_mode='Markdown'
                )
                return
            
            # Armazena a configuração
            self.user_min_balance[user_id] = min_balance
            
            if min_balance == 0:
                success_text = """
✅ **Filtro Desativado**

🔓 Todas as wallets serão exibidas, independente do saldo.
📊 Configuração salva para suas próximas consultas.
                """
            else:
                success_text = f"""
✅ **Filtro Configurado**

💰 **Saldo mínimo:** {min_balance} SOL
🎯 **Efeito:** Apenas wallets com {min_balance}+ SOL aparecerão
📊 **Configuração salva** para suas próximas consultas

💡 Use `/balance 0` para desativar o filtro
                """
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            print(f"✅ Usuário {user_id} definiu saldo mínimo: {min_balance} SOL")
            
        except ValueError:
            await update.message.reply_text(
                "❌ **Erro:** Valor inválido.\n\n"
                "**Exemplos válidos:**\n"
                "• `/balance 2` (2 SOL)\n"
                "• `/balance 0.5` (0.5 SOL)\n"
                "• `/balance 0` (desativar)",
                parse_mode='Markdown'
            )
    
    async def samewallets_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /samewallets para encontrar wallets que compraram múltiplos tokens"""
        user_id = update.effective_user.id
        
        # Se há argumentos, processa no modo antigo (para compatibilidade)
        if context.args:
            await self.process_samewallets_tokens(update, context.args)
            return
        
        # Modo interativo - solicita tokens
        self.samewallets_waiting[user_id] = True
        
        help_text = """
🔍 **Comando /samewallets - Modo Interativo**

📝 **Agora envie os endereços dos tokens que você quer analisar:**

**Formato:** Um token por linha
**Exemplo:**
```
B1xq3paAWCZGJh39f7tfCGGZLTh8Cub8QTKUiNHkBAGS
BxrYotq7fzH5tw4k4UQyekYje8n7rhNNgRCwa5Shpump
```

⚙️ **Instruções:**
• Envie **2-5 tokens** (um por linha)
• Cole cada endereço em uma mensagem separada OU
• Cole todos os endereços de uma vez (separados por quebra de linha)
• Digite `/cancel` para cancelar

🎯 **O bot encontrará wallets que compraram TODOS os tokens listados**

💡 **Aguardando seus tokens...**
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        print(f"✅ Usuário {user_id} iniciou modo interativo /samewallets")
    
    async def process_samewallets_tokens(self, update, tokens):
        """Processa lista de tokens para comando samewallets"""
        user_id = update.effective_user.id
        
        # Valida número de tokens
        if len(tokens) < 2:
            await update.message.reply_text(
                "❌ **Erro:** Você precisa fornecer pelo menos 2 tokens.\n\n"
                "**Use novamente:** `/samewallets`\n"
                "**E forneça pelo menos 2 endereços**",
                parse_mode='Markdown'
            )
            return
        
        if len(tokens) > 5:
            await update.message.reply_text(
                "❌ **Erro:** Máximo de 5 tokens por consulta.\n\n"
                "**Use novamente:** `/samewallets`\n"
                "**E forneça no máximo 5 endereços**",
                parse_mode='Markdown'
            )
            return
        
        # Valida cada token
        invalid_tokens = []
        for i, token in enumerate(tokens, 1):
            if not solscan_api.validate_token_address(token):
                invalid_tokens.append(f"Token {i}: {token[:20]}...")
        
        if invalid_tokens:
            error_msg = "❌ **Tokens inválidos encontrados:**\n\n"
            for invalid in invalid_tokens:
                error_msg += f"• {invalid}\n"
            error_msg += "\n💡 Verifique os endereços e use `/samewallets` novamente."
            
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return
        
        # Inicia processamento
        processing_msg = await update.message.reply_text(
            f"🔍 **Buscando wallets comuns...**\n\n"
            f"🎯 **Tokens a analisar:** {len(tokens)}\n"
            f"📊 **Processando:** 1/{len(tokens)} tokens...\n"
            f"⏳ **Estimativa:** {len(tokens) * 30}-{len(tokens) * 60} segundos\n"
            f"🔄 **Aguarde o processamento completo...**",
            parse_mode='Markdown'
        )
        
        try:
            print(f"🔍 Iniciando busca de wallets comuns para {len(tokens)} tokens")
            
            # Busca wallets para cada token
            all_wallets_data = {}
            token_names = {}
            
            for i, token in enumerate(tokens, 1):
                try:
                    # Atualiza progresso
                    await processing_msg.edit_text(
                        f"🔍 **Buscando wallets comuns...**\n\n"
                        f"🎯 **Tokens a analisar:** {len(tokens)}\n"
                        f"📊 **Processando:** {i}/{len(tokens)} tokens...\n"
                        f"🔄 **Token atual:** {token[:8]}...\n"
                        f"⏳ **Aguarde o processamento...**",
                        parse_mode='Markdown'
                    )
                    
                    print(f"📊 Processando token {i}/{len(tokens)}: {token}")
                    
                    # Busca wallets do token
                    buyers, token_info, balance_info = await solscan_api.extract_buyers(token)
                    
                    if not buyers:
                        await processing_msg.edit_text(
                            f"❌ **Token sem wallets encontradas**\n\n"
                            f"🎯 **Token:** {token[:8]}...\n"
                            f"📊 **Posição:** {i}/{len(tokens)}\n\n"
                            f"💡 **Possíveis motivos:**\n"
                            f"• Token muito novo\n"
                            f"• Token sem holders\n"
                            f"• Problema temporário de rede",
                            parse_mode='Markdown'
                        )
                        return
                    
                    # Armazena dados
                    token_name = token_info.get('name', f'Token {i}')
                    token_symbol = token_info.get('symbol', 'N/A')
                    token_names[token] = f"{token_name} ({token_symbol})"
                    
                    # Converte para set para interseção rápida
                    all_wallets_data[token] = set(buyers)
                    
                    print(f"✅ Token {i}: {len(buyers)} wallets encontradas - {token_name}")
                    
                except Exception as e:
                    print(f"❌ Erro ao processar token {token}: {e}")
                    await processing_msg.edit_text(
                        f"❌ **Erro ao processar token**\n\n"
                        f"🎯 **Token:** {token[:8]}...\n"
                        f"📊 **Posição:** {i}/{len(tokens)}\n\n"
                        f"💡 **Tente usar `/samewallets` novamente**",
                        parse_mode='Markdown'
                    )
                    return
            
            # Encontra interseção (wallets comuns)
            print("🔍 Calculando interseção de wallets...")
            
            await processing_msg.edit_text(
                f"🔍 **Calculando wallets comuns...**\n\n"
                f"✅ **Todos os tokens processados**\n"
                f"🧮 **Calculando interseção...**\n"
                f"⏳ **Finalizando análise...**",
                parse_mode='Markdown'
            )
            
            # Começa com wallets do primeiro token
            common_wallets = all_wallets_data[tokens[0]]
            
            # Faz interseção com cada token subsequente
            for token in tokens[1:]:
                common_wallets = common_wallets.intersection(all_wallets_data[token])
            
            # Converte de volta para lista
            common_wallets_list = list(common_wallets)
            
            print(f"📊 Interseção calculada: {len(common_wallets_list)} wallets comuns")
            
            # Comando samewallets não aplica filtro de saldo
            print(f"📊 Wallets comuns encontradas: {len(common_wallets_list)}")
            print("ℹ️ Comando /samewallets ignora filtros de saldo")
            
            # Envia resultados
            await self.send_samewallets_results(
                update, processing_msg, tokens, token_names, 
                common_wallets_list, all_wallets_data
            )
            
        except Exception as e:
            print(f"❌ Erro geral no comando samewallets: {e}")
            await processing_msg.edit_text(
                f"❌ **Erro durante processamento**\n\n"
                f"🔧 **Detalhes:** {str(e)[:100]}...\n\n"
                f"💡 **Use `/samewallets` para tentar novamente**",
                parse_mode='Markdown'
            )
    
    async def send_samewallets_results(self, update, processing_msg, tokens, token_names, common_wallets, all_wallets_data):
        """Envia resultados do comando /samewallets"""
        
        if not common_wallets:
            # Nenhuma wallet comum encontrada
            error_text = "⚠️ **Nenhuma wallet comum encontrada**\n\n"
            
            error_text += "📊 **Resumo da análise:**\n"
            for i, token in enumerate(tokens, 1):
                token_name = token_names.get(token, f"Token {i}")
                wallet_count = len(all_wallets_data.get(token, set()))
                error_text += f"• {token_name}: {wallet_count} wallets\n"
            
            error_text += f"\n🔍 **Interseção:** 0 wallets comuns\n\n"
            
            error_text += f"💡 **Possíveis razões:**\n"
            error_text += f"• Tokens têm públicos diferentes\n"
            error_text += f"• Tokens muito específicos/nichados\n"
            error_text += f"• Poucos holders em comum\n"
            error_text += f"• Tokens com poucos compradores\n\n"
            
            error_text += f"🔧 **Sugestões:**\n"
            error_text += f"• Tente tokens mais populares\n"
            error_text += f"• Analise tokens relacionados\n"
            error_text += f"• Verifique se os tokens têm atividade recente"
            
            try:
                await processing_msg.edit_text(error_text, parse_mode='Markdown')
            except:
                await processing_msg.edit_text(
                    f"⚠️ NENHUMA WALLET COMUM ENCONTRADA\n\n"
                    f"Os tokens analisados não têm wallets em comum.\n"
                    f"Tente tokens mais populares ou relacionados."
                )
            return
        
        # Monta texto com resultados
        result_text = f"✅ **Análise de Wallets Comuns Concluída**\n\n"
        
        # Lista tokens analisados
        result_text += f"🎯 **Tokens analisados:**\n"
        for i, token in enumerate(tokens, 1):
            token_name = token_names.get(token, f"Token {i}")
            wallet_count = len(all_wallets_data.get(token, set()))
            result_text += f"{i}. {token_name}: {wallet_count} wallets\n"
        
        result_text += f"\n🔍 **Wallets comuns encontradas:** {len(common_wallets)}\n"
        result_text += f"📊 **Critério:** Compraram **TODOS** os {len(tokens)} tokens\n\n"
        
        # Mostra TODAS as wallets comuns (sem limite)
        result_text += f"💰 **WALLETS QUE COMPRARAM TODOS OS TOKENS:**\n\n```\n"
        
        for i, wallet in enumerate(common_wallets, 1):
            result_text += f"{i:2d}. {wallet}\n"
        
        result_text += "```\n"
        
        # Estatísticas
        if len(tokens) == 2:
            overlap_rate = (len(common_wallets) / min(len(all_wallets_data[tokens[0]]), len(all_wallets_data[tokens[1]]))) * 100
            result_text += f"\n📈 **Taxa de sobreposição:** {overlap_rate:.1f}%"
        
        # Envia resultado
        try:
            await processing_msg.edit_text(result_text, parse_mode='Markdown')
            print(f"✅ Resultados enviados: {len(common_wallets)} wallets comuns")
        except Exception as e:
            # Fallback sem Markdown
            simple_text = f"ANALISE DE WALLETS COMUNS CONCLUIDA\n\n"
            simple_text += f"Tokens analisados: {len(tokens)}\n"
            simple_text += f"Wallets comuns: {len(common_wallets)}\n\n"
            simple_text += f"WALLETS QUE COMPRARAM TODOS OS TOKENS:\n\n"
            
            for i, wallet in enumerate(common_wallets, 1):
                simple_text += f"{i:2d}. {wallet}\n"
            
            try:
                await processing_msg.edit_text(simple_text)
                print("✅ Resultados enviados (fallback)")
            except Exception as e2:
                print(f"❌ Erro ao enviar resultados: {e2}")
    
    async def process_interactive_samewallets(self, update, user_input):
        """Processa tokens fornecidos no modo interativo do samewallets"""
        user_id = update.effective_user.id
        
        # Remove usuário do modo de espera
        if user_id in self.samewallets_waiting:
            del self.samewallets_waiting[user_id]
        
        # Processa entrada - pode ser múltiplas linhas ou tokens separados
        lines = user_input.strip().split('\n')
        tokens = []
        
        # Extrai tokens válidos de todas as linhas
        for line in lines:
            line = line.strip()
            if line and not line.startswith('/'):
                # Pode ter múltiplos tokens separados por espaço na mesma linha
                line_tokens = line.split()
                tokens.extend(line_tokens)
        
        # Remove duplicatas mantendo ordem
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        
        tokens = unique_tokens
        
        print(f"📝 Usuário {user_id} forneceu {len(tokens)} tokens: {[t[:8]+'...' for t in tokens]}")
        
        # Valida se forneceu tokens
        if not tokens:
            await update.message.reply_text(
                "❌ **Nenhum token válido encontrado**\n\n"
                "📝 **Formato esperado:**\n"
                "```\n"
                "B1xq3paAWCZGJh39f7tfCGGZLTh8Cub8QTKUiNHkBAGS\n"
                "BxrYotq7fzH5tw4k4UQyekYje8n7rhNNgRCwa5Shpump\n"
                "```\n\n"
                "💡 Use `/samewallets` para tentar novamente.",
                parse_mode='Markdown'
            )
            return
        
        # Confirma tokens recebidos
        confirm_text = f"✅ **Tokens recebidos: {len(tokens)}**\n\n"
        confirm_text += f"📋 **Lista de tokens a analisar:**\n"
        
        for i, token in enumerate(tokens[:5], 1):  # Mostra até 5
            confirm_text += f"{i}. `{token[:8]}...{token[-8:]}`\n"
        
        if len(tokens) > 5:
            confirm_text += f"... e mais {len(tokens) - 5} tokens\n"
        
        confirm_text += f"\n🔍 **Iniciando busca de wallets comuns...**"
        
        confirmation_msg = await update.message.reply_text(confirm_text, parse_mode='Markdown')
        
        # Processa os tokens
        await self.process_samewallets_tokens(update, tokens)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa mensagens de texto (endereços de token)"""
        user_input = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Verifica se usuário está no modo interativo samewallets
        if user_id in self.samewallets_waiting:
            # Comando cancel
            if user_input.lower() in ['/cancel', 'cancel', 'cancelar']:
                del self.samewallets_waiting[user_id]
                await update.message.reply_text(
                    "❌ **Comando /samewallets cancelado**\n\n"
                    "💡 Use `/samewallets` novamente quando quiser analisar wallets comuns.",
                    parse_mode='Markdown'
                )
                return
            
            # Processa tokens fornecidos
            await self.process_interactive_samewallets(update, user_input)
            return
        
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
            "⚡ RPC Helius: Processamento ultra-rápido",
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
            
            # APLICA FILTRO DE SALDO MÍNIMO SE CONFIGURADO
            user_id = update.effective_user.id
            min_balance = self.user_min_balance.get(user_id, 0.0)
            
            if min_balance > 0 and buyers:
                print(f"🔍 Aplicando filtro de saldo mínimo: {min_balance} SOL")
                original_count = len(buyers)
                
                # Se não há balance_info completa, busca saldos das wallets
                if not balance_info or len(balance_info) != len(buyers):
                    print(f"⚠️ Informações de saldo incompletas, buscando saldos individuais...")
                    
                    # Atualiza mensagem de processamento
                    try:
                        await processing_msg.edit_text(
                            "🔍 **Buscando wallets...**\n\n"
                            f"💰 **Aplicando filtro:** {min_balance} SOL mínimo\n"
                            "⏳ Verificando saldos das wallets...\n"
                            "⚡ Isso pode levar alguns momentos",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                    
                    # Busca saldos individuais para todas as wallets
                    new_balance_info = []
                    for i, wallet in enumerate(buyers):
                        try:
                            wallet_balance = await solscan_api.get_wallet_balance(wallet)
                            new_balance_info.append({
                                'wallet': wallet,
                                'balance': wallet_balance,
                                'timestamp': 0,
                                'account_index': 0,
                                'sig_index': i
                            })
                        except:
                            # Se falhar, assume saldo 0
                            new_balance_info.append({
                                'wallet': wallet,
                                'balance': 0.0,
                                'timestamp': 0,
                                'account_index': 0,
                                'sig_index': i
                            })
                    
                    balance_info = new_balance_info
                
                # Agora filtra com base no saldo mínimo
                filtered_balance_info = []
                
                for item in balance_info:
                    wallet_balance = item.get('balance', 0.0) if isinstance(item, dict) else 0.0
                    if wallet_balance >= min_balance:
                        filtered_balance_info.append(item)
                
                balance_info = filtered_balance_info
                buyers = [item.get('wallet', '') for item in balance_info] if balance_info else []
                
                filtered_count = len(buyers)
                print(f"📊 Filtro aplicado: {original_count} → {filtered_count} wallets (mín: {min_balance} SOL)")
                
                # Se todas as wallets foram filtradas
                if filtered_count == 0:
                    await processing_msg.edit_text(
                        f"⚠️ **Nenhuma wallet encontrada**\n\n"
                        f"🎯 **Filtro ativo:** {min_balance} SOL mínimo\n"
                        f"📊 **Wallets encontradas:** {original_count}\n"
                        f"💰 **Wallets com saldo suficiente:** 0\n\n"
                        f"💡 **Sugestões:**\n"
                        f"• Use `/balance 0` para desativar o filtro\n"
                        f"• Ou use `/balance` com valor menor\n"
                        f"• Verifique se o token tem holders ativos",
                        parse_mode='Markdown'
                    )
                    return
            
            # ORDENAÇÃO CRONOLÓGICA FINAL DETERMINÍSTICA
            if balance_info and len(balance_info) > 0:
                print(f"🔄 APLICANDO ORDENAÇÃO CRONOLÓGICA FINAL...")
                
                # Ordena por timestamp, índices e wallet (CONSISTÊNCIA TOTAL)
                balance_info.sort(key=lambda x: (
                    x.get('timestamp', 0), 
                    x.get('account_index', 0), 
                    x.get('sig_index', 0), 
                    x.get('wallet', '')
                ))
                buyers = [item.get('wallet', '') for item in balance_info]
                print(f"✅ ORDEM CRONOLÓGICA DETERMINÍSTICA GARANTIDA!")
                print(f"🎯 Resultados serão IDÊNTICOS em consultas futuras do mesmo token")
            
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
        
        # VERSÃO SEM QUEBRA DE LINHA usando bloco de código
        result_text += "🥇 **PRIMEIRAS WALLETS QUE COMPRARAM:**\n\n```\n"
        
        # Mostra TODAS as wallets encontradas em bloco de código (sem quebra) - COM NUMERAÇÃO
        if balance_info and len(balance_info) > 0:
            # Usa dados detalhados com saldo
            for i, wallet_data in enumerate(balance_info, 1):
                wallet = wallet_data.get('wallet', '')
                balance = wallet_data.get('balance', 0.0)
                result_text += f"{i}. {wallet} - {balance:.2f}\n"
        else:
            # Fallback: busca saldos das wallets na hora (mais lento)
            from solana_rpc import solana_rpc
            print("💰 Buscando saldos das wallets...")
            for i, wallet in enumerate(buyers, 1):
                try:
                    balance = await solana_rpc.get_wallet_balance(wallet)
                    result_text += f"{i}. {wallet} - {balance:.2f}\n"
                    print(f"💰 Wallet {i}: {balance:.2f}")
                except:
                    result_text += f"{i}. {wallet} - 0.00\n"
        
        result_text += "```"
        
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
                    simple_msg = f"✅ ENCONTRADAS {len(buyers)} WALLETS:\n\n```\n"
                    
                    if balance_info and len(balance_info) > 0:
                        # Usa dados com saldo - formato sem quebra COM NUMERAÇÃO
                        for i, wallet_data in enumerate(balance_info, 1):
                            wallet = wallet_data.get('wallet', '')
                            balance = wallet_data.get('balance', 0.0)
                            simple_msg += f"{i}. {wallet} - {balance:.2f}\n"
                    else:
                        # Fallback sem saldo - formato sem quebra COM NUMERAÇÃO
                        for i, wallet in enumerate(buyers, 1):
                            simple_msg += f"{i}. {wallet} - Saldo não disponível\n"
                    
                    simple_msg += f"```\nTotal: {len(buyers)} wallets em ordem cronológica"
                    
                    await update.message.reply_text(simple_msg)
                    print("✅ Resposta enviada com todas as wallets e saldos")
                except Exception as e3:
                    print(f"❌ Erro total na comunicação: {e3}")
                    return
        
        # Armazena os dados no contexto para callbacks (se disponível)
        try:
            # Usa o bot da mensagem de processamento (se existir)
            if hasattr(processing_msg, 'bot'):
                bot = processing_msg.bot
                if not hasattr(bot, '_wallet_cache'):
                    bot._wallet_cache = {}
                bot._wallet_cache[token_address] = buyers
                print(f"✅ Cache armazenado para {len(buyers)} wallets")
            else:
                print(f"⚠️ Bot não disponível para cache, mas isso não é crítico")
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