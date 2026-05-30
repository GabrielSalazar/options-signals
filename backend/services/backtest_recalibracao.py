"""
Backtest comparativo: alvos antigos vs nova calibração v4.0.

Roda os mesmos ativos com cada conjunto de multiplicadores e tabula:
- nº de sinais
- win rate (atingiu Alvo 1)
- retorno máximo médio

Uso:
    python backtest_recalibracao.py
"""
import logging
from backend.core.config import CONFIG
from backend.services.backtest import rodar_backtest

logging.basicConfig(level=logging.WARNING)

ATIVOS_TESTE = [
    ("PETR4.SA", "Petrobras"),
    ("VALE3.SA", "Vale"),
    ("ITUB4.SA", "Itaú"),
    ("BBAS3.SA", "Banco do Brasil"),
    ("MGLU3.SA", "Magalu"),
]

PERIODOS = {"start": "2025-06-01", "end": "2026-05-01"}

ANTIGO = {"stop_pct": -0.42, "alvo1_pct": 0.25, "alvo2_pct": 1.50, "alvo_final_pct": 4.00, "buy_band_pct": 0.10}
NOVO   = {"stop_pct": -0.43, "alvo1_pct": 0.25, "alvo2_pct": 2.50, "alvo_final_pct": 7.00, "buy_band_pct": 0.035}


def _aplica(cfg: dict):
    for k, v in cfg.items():
        CONFIG[k] = v


def _roda_cenario(label: str, cfg: dict) -> dict:
    _aplica(cfg)
    total, wins, ret_sum, sinais = 0, 0, 0.0, 0
    for tk, nome in ATIVOS_TESTE:
        ss = rodar_backtest(tk, nome, PERIODOS["start"], PERIODOS["end"])
        for s in ss:
            sinais += 1
            total += 1
            if s.get("hit_alvo1"):
                wins += 1
            ret_sum += s.get("max_return", 0.0)
    return {
        "label": label,
        "sinais": sinais,
        "win_rate": (wins / total * 100) if total else 0.0,
        "ret_medio_max_pct": (ret_sum / total * 100) if total else 0.0,
    }


def main():
    print("\n>>> Rodando cenário ANTIGO (v2.x) ...")
    r_antigo = _roda_cenario("antigo", ANTIGO)
    print("\n>>> Rodando cenário NOVO  (v4.0) ...")
    r_novo = _roda_cenario("novo", NOVO)

    print("\n" + "=" * 60)
    print(f"{'Cenário':<10}{'Sinais':>10}{'WinRate':>14}{'RetMedio':>14}")
    print("-" * 60)
    for r in (r_antigo, r_novo):
        print(f"{r['label']:<10}{r['sinais']:>10}{r['win_rate']:>13.1f}%{r['ret_medio_max_pct']:>13.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    main()
