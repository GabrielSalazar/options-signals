"""Carrega e filtra prêmios reais de opções do arquivo COTAHIST da B3.

Separa o download (rede) do filtro (puro, testável) para permitir testes sem rede
e reuso no backtest (validação de hit-rate contra prêmios que ocorreram).

ATENÇÃO (verificado em 2026-07-03): o pacote "rb3" publicado no PyPI (versão 1.8,
https://pypi.org/project/rb3/) NÃO é o parser de COTAHIST da B3 — é uma lib não
relacionada chamada "redis blaster" (módulo `rb`, cliente sharded para Redis). O
pacote real de dados da B3 chamado "rb3" (por wilsonfreitas) é um pacote do R/CRAN,
sem port oficial para Python no PyPI sob esse nome.

Por isso `carregar_cotahist_diario` abaixo faz um import tardio de `rb3` apenas
para manter a assinatura pedida pelo plano; na prática esse import falha
(ModuleNotFoundError) e a função degrada com segurança para um DataFrame vazio,
logando um aviso. Antes de usar essa função em produção é necessário substituir
sua implementação por um parser real de COTAHIST (ex.: download do arquivo
zipado em https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/
market-data/historico/mercado-a-vista/cotacoes-historicas/ e parse do layout
posicional, ou uma ponte via rpy2 para o pacote R rb3).

A peça estável e testada desta task é `filtrar_opcoes_do_ativo`.
"""
import logging

import pandas as pd

logger = logging.getLogger("b3_api")

# Tipos de mercado B3 no COTAHIST: 70 = opção de compra, 80 = opção de venda.
_TIPOS_OPCAO = (70, 80)


def filtrar_opcoes_do_ativo(df: pd.DataFrame, ativo_base: str) -> pd.DataFrame:
    """Filtra o DataFrame COTAHIST para as séries de opção do ativo informado."""
    if df.empty:
        return df
    base = ativo_base.upper().strip()
    mask = (
        df["tipo_mercado"].isin(_TIPOS_OPCAO)
        & df["cod_negociacao"].str.upper().str.startswith(base)
    )
    return df.loc[mask].reset_index(drop=True)


def carregar_cotahist_diario(data_ref: str) -> pd.DataFrame:
    """Baixa o COTAHIST diário e retorna DataFrame padronizado.

    data_ref: 'YYYY-MM-DD'. Requer rede/parser real; qualquer falha (incluindo a
    ausência de um parser real de COTAHIST hoje — ver docstring do módulo) retorna
    DataFrame vazio e loga um aviso, sem propagar exceção.
    """
    try:
        import rb3  # import tardio: dep pesada, só quando há download real

        raw = rb3.cotahist(data_ref)  # nome/assinatura ainda a confirmar com parser real
        return pd.DataFrame(raw)
    except Exception as e:
        logger.warning(f"COTAHIST indisponível para {data_ref}: {e}")
        return pd.DataFrame()
