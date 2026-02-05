"""
Script de teste para validar integração com dados reais da B3.

Testa:
- Conexão com StatusInvest
- Busca de cotações via Yahoo Finance
- Busca de cadeia de opções
- Cálculo de indicadores técnicos
- Cache Redis
"""

import asyncio
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data import B3RealData, TechnicalIndicators, cache


async def test_cotacao():
    """Testa busca de cotação."""
    print("\n" + "="*50)
    print("TESTE 1: Buscar Cotação (Yahoo Finance)")
    print("="*50)
    
    data_fetcher = B3RealData()
    
    try:
        cotacao = await data_fetcher.get_cotacao("PETR4")
        print(f"✅ Cotação obtida com sucesso!")
        print(f"   Ticker: {cotacao['ticker']}")
        print(f"   Preço: R$ {cotacao['preco']:.2f}")
        print(f"   Variação: {cotacao['variacao']:.2f}%")
        print(f"   Volume: {cotacao['volume']:,}")
        return True
    except Exception as e:
        print(f"❌ Erro ao buscar cotação: {e}")
        return False


async def test_cadeia_opcoes():
    """Testa busca de cadeia de opções."""
    print("\n" + "="*50)
    print("TESTE 2: Buscar Cadeia de Opções")
    print("="*50)
    
    data_fetcher = B3RealData()
    
    try:
        cadeia = await data_fetcher.get_cadeia_opcoes("PETR4")
        
        if cadeia.empty:
            print("⚠️  Nenhuma opção encontrada (pode ser normal fora do horário de mercado)")
            return True
        
        print(f"✅ Cadeia obtida com sucesso!")
        print(f"   Total de opções: {len(cadeia)}")
        print(f"   Calls: {len(cadeia[cadeia['tipo'] == 'CALL'])}")
        print(f"   Puts: {len(cadeia[cadeia['tipo'] == 'PUT'])}")
        
        print("\n   Primeiras 3 opções:")
        print(cadeia.head(3)[['ticker_opcao', 'tipo', 'strike', 'preco', 'volume']])
        
        return True
    except Exception as e:
        print(f"❌ Erro ao buscar cadeia: {e}")
        return False


async def test_historico():
    """Testa busca de histórico."""
    print("\n" + "="*50)
    print("TESTE 3: Buscar Histórico")
    print("="*50)
    
    data_fetcher = B3RealData()
    
    try:
        hist = await data_fetcher.get_historico("PETR4", days=30)
        print(f"✅ Histórico obtido com sucesso!")
        print(f"   Dias de dados: {len(hist)}")
        print(f"   Período: {hist.index[0].date()} até {hist.index[-1].date()}")
        print(f"   Último fechamento: R$ {hist['Close'].iloc[-1]:.2f}")
        return True
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return False


async def test_technicals():
    """Testa cálculo de indicadores técnicos."""
    print("\n" + "="*50)
    print("TESTE 4: Calcular Indicadores Técnicos")
    print("="*50)
    
    data_fetcher = B3RealData()
    tech_calculator = TechnicalIndicators()
    
    try:
        # Busca histórico
        hist = await data_fetcher.get_historico("PETR4", days=60)
        
        # Calcula indicadores
        indicators = await tech_calculator.calculate_all(hist, "PETR4")
        
        print(f"✅ Indicadores calculados com sucesso!")
        print(f"   RSI: {indicators['rsi']:.1f}")
        print(f"   MACD: {indicators['macd']['macd']:.4f}")
        print(f"   Tendência: {indicators['trend']}")
        print(f"   Sinal agregado: {indicators['signals']['aggregate']}")
        
        if indicators['signals']['oversold']:
            print("   🟢 Ativo em região de SOBREVENDIDO (RSI < 30)")
        elif indicators['signals']['overbought']:
            print("   🔴 Ativo em região de SOBRECOMPRADO (RSI > 70)")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao calcular indicadores: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_redis_cache():
    """Testa cache Redis."""
    print("\n" + "="*50)
    print("TESTE 5: Cache Redis")
    print("="*50)
    
    try:
        await cache.connect()
        
        if not cache.enabled:
            print("⚠️  Redis desabilitado ou não disponível")
            return True
        
        # Testa set/get
        test_data = {"ticker": "PETR4", "preco": 31.85}
        await cache.set_cotacao("PETR4", test_data)
        
        cached_data = await cache.get_cotacao("PETR4")
        
        if cached_data and cached_data['preco'] == 31.85:
            print("✅ Cache funcionando corretamente!")
            
            stats = await cache.get_stats()
            print(f"   Enabled: {stats.get('enabled')}")
            print(f"   Hit rate: {stats.get('hit_rate', 0):.1f}%")
        else:
            print("❌ Cache não retornou dados esperados")
            return False
        
        await cache.disconnect()
        return True
        
    except Exception as e:
        print(f"⚠️  Erro ao testar cache (Redis pode não estar rodando): {e}")
        return True  # Não falha o teste se Redis não estiver disponível


async def test_volume_opcoes():
    """Testa busca de volume de opções."""
    print("\n" + "="*50)
    print("TESTE 6: Volume de Opções")
    print("="*50)
    
    data_fetcher = B3RealData()
    
    try:
        volume_data = await data_fetcher.get_volume_opcoes("PETR4")
        print(f"✅ Volume obtido com sucesso!")
        print(f"   Volume Calls: {volume_data['volume_calls']:,}")
        print(f"   Volume Puts: {volume_data['volume_puts']:,}")
        print(f"   Put/Call Ratio: {volume_data['ratio_put_call']:.2f}")
        
        if volume_data['ratio_put_call'] > 1.0:
            print("   📊 Mais puts sendo negociadas (sentimento baixista)")
        elif volume_data['ratio_put_call'] < 1.0:
            print("   📊 Mais calls sendo negociadas (sentimento altista)")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao buscar volume: {e}")
        return False


async def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("🚀 TESTE DE INTEGRAÇÃO - DADOS REAIS B3")
    print("="*60)
    print("\nTestando integração com:")
    print("  - Yahoo Finance (cotações e histórico)")
    print("  - StatusInvest (cadeia de opções)")
    print("  - Redis (cache)")
    print("  - PandasTA (indicadores técnicos)")
    
    results = []
    
    # Executa testes
    results.append(("Cotação", await test_cotacao()))
    results.append(("Cadeia de Opções", await test_cadeia_opcoes()))
    results.append(("Histórico", await test_historico()))
    results.append(("Indicadores Técnicos", await test_technicals()))
    results.append(("Cache Redis", await test_redis_cache()))
    results.append(("Volume de Opções", await test_volume_opcoes()))
    
    # Resumo
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nResultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para usar dados reais.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} teste(s) falharam. Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
