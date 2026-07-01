"""
Teste de paridade Black-Scholes entre as implementacoes Python e TypeScript.

Contexto: o projeto tem duas implementacoes independentes da formula de
Black-Scholes (backend/domain/greeks.py em Python e src/lib/black-scholes.ts
em TypeScript), usadas em fluxos diferentes (calculo server-side vs.
GreeksCalculator.tsx no client). Este teste roda os dois lados com os
mesmos parametros via subprocess (scripts/bs_parity_cli.ts, executado com
`npx tsx`) e compara o preco resultante, para detectar divergencia futura
entre as duas formulas.
"""
import json
import subprocess

import pytest

from backend.domain.greeks import bs_call_price, bs_put_price

CASOS = [
    {"s": 100.0, "k": 105.0, "t": 0.5, "r": 0.1065, "sigma": 0.30, "type": "call"},
    {"s": 100.0, "k": 95.0, "t": 0.25, "r": 0.1065, "sigma": 0.45, "type": "put"},
    {"s": 50.0, "k": 50.0, "t": 0.0833, "r": 0.1065, "sigma": 0.60, "type": "call"},
]


def _rodar_ts(caso: dict) -> dict:
    import os
    proc = subprocess.run(
        ["npx", "tsx", "scripts/bs_parity_cli.ts"],
        input=json.dumps(caso),
        capture_output=True,
        text=True,
        timeout=30,
        shell=(os.name == "nt"),
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.parametrize("caso", CASOS)
def test_preco_bs_paridade_python_typescript(caso):
    if caso["type"] == "call":
        preco_py = bs_call_price(caso["s"], caso["k"], caso["t"], caso["r"], caso["sigma"])
    else:
        preco_py = bs_put_price(caso["s"], caso["k"], caso["t"], caso["r"], caso["sigma"])
    resultado_ts = _rodar_ts(caso)
    assert preco_py == pytest.approx(resultado_ts["price"], rel=1e-3)
