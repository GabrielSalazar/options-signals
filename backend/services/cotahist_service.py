"""Carrega e filtra prêmios reais de opções do arquivo COTAHIST da B3.

Separa o download (rede) do filtro (puro, testável) para permitir testes sem rede
e reuso no backtest (validação de hit-rate contra prêmios que ocorreram).

ATENÇÃO (verificado em 2026-07-03): o pacote "rb3" publicado no PyPI (versão 1.8,
https://pypi.org/project/rb3/) NÃO é o parser de COTAHIST da B3 — é uma lib não
relacionada chamada "redis blaster" (módulo `rb`, cliente sharded para Redis). O
pacote real de dados da B3 chamado "rb3" (por wilsonfreitas) é um pacote do R/CRAN,
sem port oficial para Python no PyPI sob esse nome.

Também não foi encontrado no PyPI nenhum pacote Python ativamente mantido e
com suporte a registros de opção do COTAHIST — candidatos avaliados (bovespa,
b3parser, bovespaparser, pybov) estão obsoletos/genéricos e nenhum confirma
tratar os registros TIPREG=1 com TIPO_MERCADO de opção (70/80).

Por isso `carregar_cotahist_diario` abaixo é um stub deliberado: não faz
nenhum import de dependência externa (nem `rb3`, nem outro pacote), apenas
loga um aviso e retorna um DataFrame vazio. A implementação real precisará de
um parser posicional (fixed-width) próprio, escrito à mão, para o arquivo
COTAHIST_A{YYYY}.ZIP publicado pela B3 (download em
https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/
market-data/historico/mercado-a-vista/cotacoes-historicas/).

Referência de layout conhecida (arquivo texto de largura fixa, codificação
ISO-8859-1; layout oficial "Histórico de Cotações — Leiaute" publicado pela
B3 junto com o ZIP anual):
  - TIPREG (posições 0-2): tipo de registro (variável de referência p/ pular
    cabeçalho/rodapé).
  - DATA_PREGAO (2-10): data do pregão.
  - TIPO_MERCADO (10-12): "70" = opção de compra, "80" = opção de venda.
  - CODNEG (12-24): código de negociação (ticker da série de opção).
  - PREULT (~94-105): preço/prêmio de fechamento, casas decimais implícitas
    (últimos 2 dígitos são centavos).
  - PREEXE (~188-200): preço de exercício (strike), mesma convenção decimal.
  - DATVEN (~202-210): data de vencimento da série.
As posições acima são aproximadas e devem ser conferidas contra o PDF de
layout oficial da B3 antes de implementar o parser real.

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

    STUB DELIBERADO (ver docstring do módulo): não existe hoje, no PyPI, um
    parser Python confiável para os registros de opção do COTAHIST — não há
    import de nenhuma dependência externa aqui. Esta função apenas loga um
    aviso e retorna um DataFrame vazio até que um parser posicional próprio
    seja implementado (fixed-width, ISO-8859-1, arquivo COTAHIST_A{YYYY}.ZIP
    da B3).

    data_ref: 'YYYY-MM-DD'.
    """
    logger.warning(
        f"COTAHIST indisponível para {data_ref}: download/parse ainda não "
        "implementado (nenhum pacote PyPI viável encontrado; requer parser "
        "fixed-width próprio — ver docstring do módulo)."
    )
    return pd.DataFrame()
