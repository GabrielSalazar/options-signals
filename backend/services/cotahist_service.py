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

IMPORTANTE — já existe um parser fixed-width do COTAHIST no repositório,
testado contra arquivo real: `_parse_cotahist_zip` em
`backend/services/liquidity_service.py` (usado por `coletar_liquidity_diaria`
para extrair bid/ask de fechamento por opção). Antes de escrever um parser do
zero, ver esse código — ele já resolve download do ZIP diário (COTAHIST_DDMMAAAA.ZIP,
`COTAHIST_BASE_URL`), leitura linha a linha em latin-1, e filtro por TPMERC.
Os offsets REAIS usados lá (conferidos em produção, diferentes dos que uma
leitura do leiaute oficial sugeriria à primeira vista) são:
  - TPMERC (posição 2:5, string de 3 chars): "070" = opção de compra,
    "080" = opção de venda — outros tipos (ex.: "010" = ação) são ignorados.
  - ESPECS/ticker da série (posição 36:40): 4 primeiros chars = raiz do ativo
    (ex.: "PETRG360" → raiz "PETR").
  - PREOFC (posição 82:95): preço ofertado de compra (ask no parser, right-aligned,
    vírgula decimal).
  - PREOFV (posição 95:108): preço ofertado de venda (bid no parser).

Esse parser é específico para bid/ask agregados por raiz de ativo (não guarda
strike nem data de vencimento por linha — o dict de saída é
`{ticker_base: {"bid", "ask", "spread_pct"}}`), então NÃO generaliza
diretamente para o caso desta task (prêmio de fechamento por série individual,
com strike/vencimento, para validação de hit-rate no backtest). Por isso
`carregar_cotahist_diario` abaixo permanece um stub deliberado — mas qualquer
parser real que vier a substituí-lo deve reusar os offsets acima (já
verificados) em vez de re-derivar posições do leiaute oficial da B3.

`carregar_cotahist_diario` não faz nenhum import de dependência externa (nem
`rb3`, nem outro pacote), apenas loga um aviso e retorna um DataFrame vazio
até que um parser posicional (fixed-width) específico para registros de
opção completos (com PREULT/PREEXE/DATVEN) seja implementado, para o arquivo
COTAHIST_A{YYYY}.ZIP publicado pela B3 (download em
https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/
market-data/historico/mercado-a-vista/cotacoes-historicas/).

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
    import de nenhuma dependência externa aqui. Já existe um parser fixed-width
    testado em produção para bid/ask (`_parse_cotahist_zip` em
    `backend/services/liquidity_service.py`), mas ele não guarda strike/vencimento
    por série, então não serve diretamente aqui — ver docstring do módulo para
    os offsets reais já verificados. Esta função apenas loga um aviso e retorna
    um DataFrame vazio até que um parser posicional próprio para registros de
    opção completos seja implementado (fixed-width, ISO-8859-1, arquivo
    COTAHIST_A{YYYY}.ZIP da B3).

    data_ref: 'YYYY-MM-DD'.
    """
    logger.warning(
        f"COTAHIST indisponível para {data_ref}: download/parse ainda não "
        "implementado (nenhum pacote PyPI viável encontrado; requer parser "
        "fixed-width próprio — ver docstring do módulo)."
    )
    return pd.DataFrame()
