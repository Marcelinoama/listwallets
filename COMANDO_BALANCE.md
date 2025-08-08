# Comando /balance - Filtro de Saldo Mínimo

## 🎯 Funcionalidade

O comando `/balance` permite filtrar wallets com base no saldo mínimo de SOL, mostrando apenas aquelas que possuem o valor especificado ou superior.

## 📝 Como Usar

### Configurar Filtro
```
/balance 2      # Mostra apenas wallets com 2+ SOL
/balance 0.5    # Mostra apenas wallets com 0.5+ SOL
/balance 10     # Mostra apenas wallets com 10+ SOL
```

### Ver Configuração Atual
```
/balance        # Sem argumentos - mostra configuração atual
```

### Desativar Filtro
```
/balance 0      # Desativa o filtro (padrão)
```

## ✅ Exemplos Práticos

### Exemplo 1: Filtro para Whales
```
/balance 100
```
**Resultado:** Apenas wallets com 100+ SOL aparecerão

### Exemplo 2: Filtro Moderado  
```
/balance 5
```
**Resultado:** Apenas wallets com 5+ SOL aparecerão

### Exemplo 3: Filtro Baixo
```
/balance 0.1
```
**Resultado:** Apenas wallets com 0.1+ SOL aparecerão (remove wallets vazias)

## 🔧 Funcionamento Interno

1. **Armazenamento por usuário**: Cada usuário tem sua própria configuração
2. **Aplicado automaticamente**: Filtro é aplicado em todas as consultas futuras
3. **Mantém ordem cronológica**: Wallets filtradas continuam em ordem cronológica
4. **Informação clara**: Bot informa quantas wallets foram filtradas

## 📊 Fluxo de Filtragem

```
1. Buscar wallets do token (ex: 20 wallets encontradas)
2. Aplicar filtro de saldo (ex: /balance 2)
3. Filtrar wallets com saldo ≥ 2 SOL (ex: 8 wallets restam)
4. Exibir resultado filtrado
```

## ⚠️ Cenários Especiais

### Nenhuma Wallet Atende o Critério
Se todas as wallets tiverem saldo menor que o filtro:
```
⚠️ Nenhuma wallet encontrada

🎯 Filtro ativo: 50 SOL mínimo
📊 Wallets encontradas: 15
💰 Wallets com saldo suficiente: 0

💡 Sugestões:
• Use /balance 0 para desativar o filtro
• Ou use /balance com valor menor
• Verifique se o token tem holders ativos
```

## 🚀 Vantagens

- **Foco em holders relevantes**: Ignora wallets com saldos insignificantes
- **Análise de whales**: Encontra facilmente os grandes holders
- **Personalização**: Cada usuário define seu próprio critério
- **Flexibilidade**: Pode ser ativado/desativado a qualquer momento

## 🔍 Casos de Uso

### Para Traders
- `/balance 10` - Encontrar traders com capital significativo
- `/balance 1` - Filtrar contas muito pequenas

### Para Análise de Projetos
- `/balance 50` - Identificar investidores sérios
- `/balance 0.1` - Remover contas inativas/vazias

### Para Pesquisa de Whales
- `/balance 1000` - Encontrar apenas os maiores holders
- `/balance 100` - Holders com investimento substancial

---

## 🎉 Resultado

**ANTES**: Todas as wallets eram exibidas, incluindo com 0.001 SOL
**DEPOIS**: Apenas wallets com saldo relevante são mostradas

O filtro torna a análise muito mais eficiente e focada nos holders que realmente importam!
