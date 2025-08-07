#!/usr/bin/env python3
"""
Teste das validações de token
"""

from solscan_api import solscan_api

def test_token_validation():
    print("🧪 TESTANDO VALIDAÇÃO DE TOKENS")
    print("=" * 50)
    
    # Casos de teste
    test_cases = [
        # (endereço, esperado, descrição)
        ("So11111111111111111111111111111111111111112", True, "Token SOL válido"),
        ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", True, "Token USDC válido"),
        ("", False, "Endereço vazio"),
        ("123", False, "Muito curto"),
        ("So111111111111111111111111111111111111111122222222222222", False, "Muito longo"),
        ("0x1234567890123456789012345678901234567890", False, "Endereço Ethereum"),
        ("So11111111111111111111111111111111111111O", False, "Contém 'O' (inválido em Base58)"),
        ("So111111111111111111111111111111111111110", False, "Contém '0' (inválido em Base58)"),
        ("So11111111111111111111111111111111111111I", False, "Contém 'I' (inválido em Base58)"),
        ("So11111111111111111111111111111111111111l", False, "Contém 'l' (inválido em Base58)"),
        ("abc", False, "Muito curto"),
    ]
    
    print("Casos de teste:")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    for i, (address, expected, description) in enumerate(test_cases, 1):
        result = solscan_api.validate_token_address(address)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        display_addr = address[:20] + "..." if len(address) > 20 else address
        print(f"{i:2d}. {status} {description}")
        print(f"    Endereço: {display_addr}")
        print(f"    Esperado: {expected}, Resultado: {result}")
        print()
    
    print("=" * 50)
    print(f"📊 RESULTADO DOS TESTES:")
    print(f"✅ Passou: {passed}")
    print(f"❌ Falhou: {failed}")
    print(f"📈 Taxa de sucesso: {(passed/(passed+failed)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n⚠️ {failed} teste(s) falharam")

if __name__ == "__main__":
    test_token_validation()