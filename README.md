# 🔍 ListWallet Bot - Solana Token Buyers Tracker

Bot de Telegram que busca e lista as wallets que compraram um token específico na blockchain Solana usando a API do Solscan.

## 🚀 Funcionalidades

- 📊 Busca automática das **primeiras wallets** que compraram tokens Solana
- ⏰ **Ordem cronológica**: do primeiro ao último comprador
- 🔢 Número configurável no `.env` (padrão: 50 wallets)
- 📄 Download da lista completa em formato TXT
- ✅ Validação de endereços de token
- 🔍 Informações básicas do token

## 📋 Requisitos

- Python 3.8+
- Token de bot do Telegram (obtido no @BotFather)
- Conexão com internet

## 🛠️ Instalação

1. **Clone ou baixe os arquivos do projeto**

2. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

3. **Configure o token do bot:**
   - Crie um arquivo `.env` na pasta do projeto
   - Adicione seu token do Telegram:
```
TELEGRAM_BOT_TOKEN=SEU_TOKEN_AQUI
```

   **OU** edite diretamente o arquivo `config.py` e substitua `SEU_TOKEN_AQUI` pelo seu token.

4. **Execute o bot:**
```bash
python3 bot.py
```

## 🤖 Como obter o token do bot

1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Escolha um nome e username para seu bot
4. Copie o token fornecido pelo BotFather
5. Cole o token no arquivo de configuração

## 📱 Como usar o bot

1. **Inicie uma conversa com seu bot**
2. **Envie o comando `/start` para ver as instruções**
3. **Envie o endereço de um token Solana**
   - Exemplo: `So11111111111111111111111111111111111111112`
4. **Aguarde a análise** (pode levar alguns segundos)
5. **Visualize os resultados:**
   - Lista das primeiras 10 wallets
   - Botão para ver lista completa
   - Botão para download em TXT

## 🔧 Comandos disponíveis

- `/start` - Inicia o bot e mostra instruções
- `/help` - Mostra ajuda detalhada
- Enviar endereço de token - Busca compradores

## 📁 Estrutura do projeto

```
listwallet/
├── bot.py              # Bot principal do Telegram
├── solscan_api.py      # Integração com API do Solscan
├── config.py           # Configurações do bot
├── requirements.txt    # Dependências Python
└── README.md          # Este arquivo
```

## ⚙️ Configurações

Você pode ajustar as seguintes configurações no arquivo `.env`:

- `MAX_WALLETS_DISPLAY`: Número de primeiras wallets que compraram para retornar (padrão: 50)
- `CACHE_TIMEOUT`: Tempo de cache em segundos (padrão: 300)

**Exemplo de configuração no .env:**
```env
TELEGRAM_BOT_TOKEN=seu_token_aqui
MAX_WALLETS_DISPLAY=100
CACHE_TIMEOUT=600
```

**📊 Importante sobre MAX_WALLETS_DISPLAY:**
- Define quantas **primeiras wallets** que compraram o token serão retornadas
- As wallets são ordenadas cronologicamente (primeiro → último comprador)
- Você pode ajustar este número conforme sua necessidade

## 🚨 Limitações

- Número de wallets limitado pela configuração MAX_WALLETS_DISPLAY
- Dependente da disponibilidade da API do Solscan
- Pode haver delay em tokens muito populares
- Tokens muito novos podem não ter dados suficientes
- Ordem cronológica baseada no timestamp das transações do Solscan

## 🐛 Problemas comuns

### "Token não encontrado"
- Verifique se o endereço do token está correto
- Certifique-se de que o token existe na Solana

### "Sem compradores encontrados"
- Token pode ser muito novo
- Token pode não ter transações registradas
- API do Solscan pode estar indisponível

### Bot não responde
- Verifique se o token está correto
- Verifique a conexão com internet
- Reinicie o bot

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs do console
2. Confirme se todas as dependências estão instaladas
3. Teste com tokens conhecidos (como USDC)

## 🔒 Segurança

- Mantenha seu token do bot privado
- Não compartilhe o arquivo `.env`
- Use apenas em servidores confiáveis

---

**Desenvolvido para busca de compradores de tokens Solana via Solscan** 🔍# listwallets
