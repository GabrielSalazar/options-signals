# Repository Structure

## ✅ Correct Structure (This is what we want)

```
https://github.com/GabrielSalazar/options-signals/tree/main
│
├── README.md (English)
├── README.pt-BR.md (Portuguese)
├── README_REWRITE_SUMMARY.md
├── REWRITE_ANALYSIS.md
├── STRUCTURE.txt
├── .github-structure.txt
│
├── backend/ (Python Backend)
│   ├── api/
│   │   ├── routers/
│   │   └── main.py
│   ├── core/
│   │   ├── cache.py
│   │   └── config.py
│   ├── domain/
│   │   ├── greeks.py
│   │   ├── indicators.py
│   │   ├── options_math.py
│   │   └── scoring.py
│   ├── services/
│   │   ├── backtest.py
│   │   ├── backtest_recalibracao.py
│   │   ├── core_engine.py
│   │   └── data_providers.py
│   └── requirements.txt
│
├── src/ (Next.js Frontend)
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── context/
│   ├── hooks/
│   └── types/
│
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.mjs
├── Dockerfile
├── docker-compose.yml
│
├── docs/ (Documentation)
│   ├── ESTADO_ATUAL.md
│   ├── REPORT_COMPLETO.md
│   ├── ARQUITETURA_PRODUCAO.md
│   ├── QUICKSTART.md
│   ├── ESTRATEGIAS_OPCOES_B3.md
│   ├── MONTAGEM_DE_SINAL_B3.md
│   ├── SUPABASE_SETUP.md
│   └── CHANGELOG.md
│
├── gregas/ (Strategies)
│   ├── RESUMO_EXECUTIVO.md
│   ├── fase2_estrategias_detalhado.md
│   └── plano_desenvolvimento_gregas.md
│
├── public/ (Assets)
│   └── [static files]
│
├── supabase/ (Config)
│   └── [Supabase configuration]
│
└── node_modules/ (Dependencies)
```

## ❌ Wrong Structure (What we DON'T want)

```
https://github.com/GabrielSalazar/options-signals/tree/main/options-signals
│
└── [All files duplicated here]
```

## Status

✅ All files are at the root level
✅ No nested options-signals/ folder
✅ Clean repository structure
✅ Ready for production
