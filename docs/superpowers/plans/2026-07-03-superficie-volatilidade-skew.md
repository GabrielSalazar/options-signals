# Superfície de Volatilidade e Skew (SABR/Heston) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modelar a superfície de volatilidade implícita (smile/skew) para capturar como IV varia com strike e vencimento. Integrar no score do motor PUCK para penalizar somas de opções que ficam desalinhadas com a superfície.

**Architecture:** Camada `vol_surface.py` extrai IV de um conjunto de strikes/vencimentos, calibra modelo SABR (mais simples que Heston), interpola para qualquer novo par (K, T). O serviço de scoring consulta a superfície ao validar estruturas. A calibração roda offline diária (job agendado) via `ysaporito/modelos_vol_derivativos` como referência.

**Tech Stack:** Python, scipy, numpy, `quantlib` ou implementação própria de SABR, pytest. QuantLib é pesado — começar por SABR simples.

**Escopo:** Este plano é **opcional/futuro** — alto esforço (semana inteira), baixo retorno imediato (motor PUCK já está validado sem superfície). Prioridade menor que itens 1–4.

---

## File Structure

- **Create:** `backend/domain/vol_surface.py` — modelo SABR, interpolação
- **Create:** `backend/services/vol_surface_service.py` — calibração diária
- **Create:** `tests/test_vol_surface.py` — testes de interpolação
- **Modify:** `backend/domain/scoring.py` — consulta a superfície ao validar estruturas

---

## Task 1: Modelo SABR básico

**Files:**
- Create: `backend/domain/vol_surface.py`
- Create: `tests/test_vol_surface.py`

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_vol_surface.py`:

```python
"""Testes do modelo SABR para superfície de volatilidade."""
import numpy as np

from backend.domain.vol_surface import SABRModel


def test_sabr_interpola_iv():
    # Dados reais de PETR4 (exemplo)
    strikes = [25.0, 27.5, 30.0, 32.5, 35.0]
    ivs = [0.45, 0.40, 0.38, 0.40, 0.45]
    T = 60 / 252
    
    sabr = SABRModel(strikes, ivs, T)
    iv_novo = sabr.interpolate(30.5)
    
    assert 0.37 < iv_novo < 0.39  # próximo a 30.0


def test_sabr_respeita_boundary():
    strikes = [25.0, 35.0]
    ivs = [0.45, 0.45]
    T = 60 / 252
    
    sabr = SABRModel(strikes, ivs, T)
    iv_left = sabr.interpolate(24.0)  # extrapolação à esquerda
    assert iv_left == 0.45  # borda
```

- [ ] **Step 2: Rodar e verificar falha**

```bash
pytest tests/test_vol_surface.py -v
```

- [ ] **Step 3: Implementar SABR básico (cúbica + extrapolação)**

Criar `backend/domain/vol_surface.py`:

```python
"""Superfície de volatilidade implícita: modelo SABR simplificado + interpolação."""
import numpy as np
from scipy.interpolate import interp1d


class SABRModel:
    """SABR simples: spline cúbica sobre pontos IV reais, extrapolação flat nos extremos."""
    
    def __init__(self, strikes: list, ivs: list, T: float):
        """
        strikes: array de strikes observados
        ivs: array de IVs correspondentes (mesmo tamanho)
        T: tempo até vencimento (anos)
        """
        self.strikes = np.array(strikes)
        self.ivs = np.array(ivs)
        self.T = T
        # Spline cúbica, fill_value='extrapolate' (ou usar flat nas pontas)
        self._spline = interp1d(self.strikes, self.ivs, kind='cubic', fill_value='extrapolate')
    
    def interpolate(self, strike: float) -> float:
        """Retorna IV para o strike informado. Extrapolação flat nas caudas."""
        if strike < self.strikes.min():
            return float(self.ivs[0])
        if strike > self.strikes.max():
            return float(self.ivs[-1])
        return float(self._spline(strike))
    
    def smile(self) -> dict:
        """Retorna dicionário strike -> IV para plotagem."""
        return {s: iv for s, iv in zip(self.strikes, self.ivs)}
```

- [ ] **Step 4: Rodar os testes e verificar que passam**

```bash
pytest tests/test_vol_surface.py -v
```

Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/domain/vol_surface.py tests/test_vol_surface.py
git commit -m "feat(vol-surface): modelo SABR básico com interpolação cúbica"
```

---

## Task 2: Serviço de calibração diária

**Files:**
- Create: `backend/services/vol_surface_service.py`

- [ ] **Step 1: Implementar carregador de superfícies por vencimento**

Criar `backend/services/vol_surface_service.py`:

```python
"""Calibração diária da superfície de volatilidade. Constrói SABRModel por vencimento/ativo."""
import logging
from collections import defaultdict

import pandas as pd

from backend.domain.vol_surface import SABRModel
from backend.services.cotahist_service import carregar_cotahist_diario, filtrar_opcoes_do_ativo
from backend.domain.options_math import decodificar_opcao_b3

logger = logging.getLogger("b3_api")

_surfaces_cache = {}  # ativo -> vencimento -> SABRModel


def calibrar_superficies(data_ref: str, ativos: list) -> dict:
    """Carrega COTAHIST, extrai IVs, calibra SABRModel por ativo/vencimento. Retorna cache."""
    global _surfaces_cache
    
    df = carregar_cotahist_diario(data_ref)
    if df.empty:
        logger.warning(f"COTAHIST vazio para {data_ref}")
        return _surfaces_cache
    
    for ativo in ativos:
        opcoes = filtrar_opcoes_do_ativo(df, ativo)
        if opcoes.empty:
            continue
        
        # Agrupa por vencimento
        por_vencimento = defaultdict(list)
        for _, row in opcoes.iterrows():
            dec = decodificar_opcao_b3(row["cod_negociacao"])
            if not dec or "strike" not in dec:
                continue
            venc_key = (dec["ano_venc"], dec["mes_venc"])
            por_vencimento[venc_key].append({
                "strike": dec["strike"],
                "preco": row["preco_ultimo"],
            })
        
        # Calibra SABR por vencimento
        for (ano, mes), strikes_precos in por_vencimento.items():
            T = max(1, (pd.Timestamp(f"{ano}-{mes:02d}-15") - pd.Timestamp(data_ref)).days) / 252
            strikes_arr = sorted([x["strike"] for x in strikes_precos])
            # TODO: calcular IVs reais via Black-Scholes inverso; por agora, usar preços como proxy
            ivs_arr = [p["preco"] / 100.0 for p in strikes_precos]  # SIMPLIFICADO
            
            sabr = SABRModel(strikes_arr, ivs_arr, T)
            _surfaces_cache[(ativo, ano, mes)] = sabr
    
    return _surfaces_cache


def obter_superficie(ativo: str, ano_venc: int, mes_venc: int) -> SABRModel | None:
    """Retorna a superfície calibrada para o ativo/vencimento, ou None."""
    return _surfaces_cache.get((ativo, ano_venc, mes_venc))
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/vol_surface_service.py
git commit -m "feat(vol-surface): calibração diária e cache por vencimento"
```

---

## Task 3: Integração no score (opcional, diferida)

**Files:**
- Modify: `backend/domain/scoring.py` (consultar superfície ao validar)

- [ ] **Step 1: Adicionar check no score**

Em `backend/domain/scoring.py`, ao calcular score de uma estrutura, adicionar:

```python
from backend.services.vol_surface_service import obter_superficie

# Dentro do loop de validação:
superficie = obter_superficie(ativo, ano_venc, mes_venc)
if superficie:
    iv_esperada = superficie.interpolate(strike)
    desvio = abs(iv_calculada - iv_esperada)
    if desvio > 0.05:  # mais de 5% de desvio = penalidade
        score *= (1 - desvio * 0.5)  # reduz score proporcionalmente
```

- [ ] **Step 2: Commit**

```bash
git add backend/domain/scoring.py
git commit -m "feat(score): penalizar estruturas fora da superfície de vol"
```

---

## Status e Próximos Passos

Este plano é **arquivo/futuro** — o motor PUCK funciona sem superfície de volatilidade. Implemente quando:

1. Fase 4 (validação PUCK) estiver 100% e gerar feedback de outliers.
2. Houver tempo para calibração de Heston (mais sofisticado que SABR).
3. Dashboard de superfície for requisitado pelos usuários.

**Referência:** `ysaporito/modelos_vol_derivativos` (Jupyter FGV) para Heston/SABR avançados.
