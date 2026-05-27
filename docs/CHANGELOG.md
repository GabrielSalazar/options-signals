# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2026-05-27

### Added
- **17 Novas Estratégias de Opções:** Adicionado suporte nativo no simulador (frontend) para posições puras, estratégias com ação, spreads, volatilidade e estruturas complexas. 
- **Integração de Preço da Ação-Objeto:** Motor de payoff agora suporta cálculo de Covered Call e Protective Put modelando o PL das ações (`stockOffset`).
- **Cards Dinâmicos:** Interface da página de estratégias reescrita usando um layout de cards responsivo dividido em 5 categorias, com labels inteligentes por strike.
- **Cache Redis no Backend:** Adicionado suporte a `REDIS_URL` para fazer cache dos retornos das APIs do `yfinance` e `opcoes.net.br`.
- **Parallel Scraping:** Endpoint `/market/opcoes` e processos de varredura refatorados para utilizar `ThreadPoolExecutor`, baixando o tempo de latência de varredura das opções.

### Changed
- Refatorado `strategies.ts` exportando metadados completos (`STRATEGY_META`) para serem facilmente consumidos pela UI.
- Otimizada inicialização (`lifespan`) do FastAPI para testar a conectividade do Redis logo no startup.
- Documentação limpa e movida para centralização em `docs/` e `README.md`.

### Fixed
- Corrigido `CORS` configurando corretamente as variáveis de ambiente em produção (Render e Vercel).
- Correção de timezone e timestamps no uso da biblioteca de options pricing.

## [2.0.0] - 2026-05-26

- Lançamento inicial da versão web com Next.js, FastAPI e Supabase.
- Motor com 19 gatilhos técnicos.
- Scanner em tempo real com SSE (Server-Sent Events).
