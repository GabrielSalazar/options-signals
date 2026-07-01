# Relatório de Auditoria de Correção e Arquitetura - Backend & Frontend

Este documento consolida as melhorias e correções identificadas na auditoria das camadas de backend (API, services, core, domain) e frontend do sistema de sinais e opções.

---

## 1. Backend

### CRÍTICO

#### 🔴 [CRÍTICO] `backend/api/routers/config.py:15-22` — Endpoints sem nenhuma autenticação; sequestro do bot Telegram
* **Problema:** Nenhuma rota da API exige autenticação (não há dependência de API key/JWT em lugar algum). `POST /config/telegram` aceita `token`/`chat_id` arbitrários, muta `CONFIG` e persiste no Supabase via *service role*.
* **Cenário de falha:** Qualquer pessoa com a URL pública faz POST `/config/telegram` com o próprio `chat_id` e passa a receber todos os sinais do usuário (ou zera `token`/`chat_id` e silencia as notificações — o `set_telegram` grava até string vazia). Endpoints de scan também podem ser disparados por terceiros (ver DoS abaixo).
* **Correção:** Criar middleware/dependency de API key (via Header) ao menos para as rotas mutantes (`/config/*`, `/signals/scan/*`, `/backtest/run`); validar payloads com Pydantic em vez de dicts crus.

#### 🔴 [CRÍTICO] `backend/services/core_engine.py:484-530` + `backend/core/config.py:119-146` — Race TOCTOU no cooldown `_historico_sinais` (dict global, sem lock)
* **Problema:** `is_reentrada_valida` (check, linha 484) e `registrar_sinal` (act, linha 530) rodam separados por dezenas de chamadas de rede (chain de opções, IV rank via Supabase) dentro de `analisar_ativo`, executado por `ThreadPoolExecutor` com 8-10 workers e por múltiplos scans concorrentes. O `_historico_sinais` é um dicionário global mutado sem lock (`config.py:117-122`).
* **Cenário de falha:** O scan agendado (`run_scan`) e um scan manual (`/signals/scan/stream` ou `scan_batch`) analisam o mesmo ticker simultaneamente; ambos passam no `is_reentrada_valida` antes de qualquer um deles registrar o cooldown → sinal duplicado persistido e notificado duas vezes no Telegram. O GIL evita a corrupção do dict na memória, mas não a janela check-then-act de vários segundos.
* **Correção:** Proteger a verificação e o registro com um `threading.Lock` único (com uma estratégia de "reserva" rápida antes da parte custosa do processamento, executando rollback caso o sinal seja rejeitado) ou mover a restrição de deduplicação para o banco de dados (constraint/upsert por ticker, direção e janela de tempo).

---

### ALTO

#### 🟠 [ALTO] `backend/services/signal_service.py:64-70 + 277` — Broadcast SSE de alertas nunca funciona (feature morta silenciosa)
* **Problema:** O método `_maybe_broadcast` só agenda o broadcast se houver um event loop ativo rodando na thread atual. Porém, `run_scan` roda em thread secundária do APScheduler e `scan_single`/`scan_batch` rodam no threadpool do anyio (rotas sync). Em nenhum desses casos há um event loop na thread atual → o `RuntimeError` é capturado de forma genérica no `except` e silenciado, descartando o alerta.
* **Cenário de falha:** O cliente conectado em `/signals/alerts/stream` nunca recebe nenhum evento em tempo real em produção; além disso, a fila `_alert_queues` cresce indefinidamente na memória.
* **Correção:** Capturar a referência do event loop principal no lifespan do FastAPI e utilizar `asyncio.run_coroutine_threadsafe(broadcast_alert(s), main_loop)` para postar a corrotina. Adicionalmente, definir um `maxsize` para as filas em `_alert_queues` para evitar vazamento de memória se algum consumidor SSE ficar lento.

#### 🟠 [ALTO] `backend/api/routers/scan.py:114-128` — Scans completos concorrentes e sem exclusão mútua com o scheduler (DoS trivial)
* **Problema:** A configuração `max_instances=1` do APScheduler só se aplica ao job agendado de forma interna. Os endpoints `POST /signals/scan/all` e `/all-b3` são rotas síncronas bloqueantes que executam o `run_scan` completo (levando minutos e efetuando centenas de chamadas HTTP para mais de 150 tickers) e podem rodar concorrentemente entre si e com o scheduler. A falta de autenticação e o rate limit alto do FastAPI não impedem múltiplos scans concomitantes.
* **Cenário de falha:** Disparo simultâneo de requisições manuais e execução do scan agendado → gera mais de 450 análises concorrentes, estourando o rate limit de APIs como Yahoo Finance/BRAPI, esgotando o threadpool do servidor (causando timeout em outras requisições) e duplicando sinais devido à race condition do cooldown.
* **Correção:** Implementar um `threading.Lock` ou flag de estado "scan em andamento" no `signal_service` para retornar HTTP 409 (Conflict) se já houver um scan rodando. Avaliar o disparo assíncrono das tarefas (background tasks) em vez de bloquear a requisição HTTP principal.

#### 🟠 [ALTO] `backend/services/backtest.py:46` + `core_engine.py:278-306` — Backtest usa a chain de opções e o vencimento de hoje para sinais históricos (Look-Ahead / resultados inválidos)
* **Problema:** A função `analisar_ativo` com `df_provided` (usada no backtest) ainda chama `_montar_estrutura_opcao`, que por sua vez faz requisições a `get_real_options_from_opcoes_net` (trazendo preços atuais de tela) e `mes_vencimento_ideal()` (calculando DTE baseado no `datetime.now()`) para cada barra de preço histórico. Além disso, em `backtest.py:66-70` o cálculo de retorno é feito sobre `premio_est`, mas os alvos e stops podem ter sido baseados no `preco_tela` atual da opção real, misturando referências temporais distintas.
* **Cenário de falha:** Um backtest executado sobre dados de 2024 utiliza prêmios e DTE das opções reais cotadas hoje (ex: vencimento em 2026), invalidando as métricas de win-rate e a curva de equity, o que invalida também o processo de recalibração automática de parâmetros (`backtest_recalibracao.py`).
* **Correção:** Quando o sistema estiver rodando em modo backtest (`df_provided is not None`), pular a pesquisa por opções reais do dia, estimar os preços exclusivamente via modelo (usando `premio_est`) e calcular os dias para vencimento (DTE) a partir da data de cada barra histórica.

#### 🟠 [ALTO] `backend/services/outcome_service.py:62` — Janela fixa de 6 meses vs. parâmetro days até 365: desfechos incorretos persistidos em `trigger_outcomes`
* **Problema:** O método `_precos_desde` busca sempre uma janela fixa de 6 meses (`6mo`), porém a rota `/signals/outcomes?days=365` permite avaliar sinais ocorridos em até 1 ano. Para sinais com mais de ~120 dias de idade, o preço de abertura indexado em `precos[0]` deixa de ser o preço do dia da entrada do sinal e passa a ser o preço inicial da janela de 6 meses (meses após a entrada), distorcendo os cálculos baseados na fórmula de precificação Black-Scholes.
* **Cenário de falha:** Um sinal antigo é classificado erroneamente como atingindo stop ou alvo baseado em um histórico de preços que começa em data deslocada; o upsert no banco grava um desfecho permanente incorreto na tabela `trigger_outcomes`.
* **Correção:** Dimensionar dinamicamente o parâmetro de range temporal baixado (ex.: `1y` se `days=365`) e validar de forma estrita que a primeira data disponível no histórico seja menor ou igual à data de disparo do sinal. Caso contrário, pular o processamento para evitar corrupção de dados.

#### 🟠 [ALTO] `backend/services/supabase_client.py:12-26` + `core_engine.py:496` — Cliente Supabase recriado a cada chamada + N+1 de `iv_rank` por ticker no scan
* **Problema:** A função `get_supabase()` instancia um novo `create_client` a cada invocação, abrindo novas sessões HTTP e handshakes. Além disso, no decorrer do scan, a função `obter_iv_rank(ticker_base)` (em `core_engine.py:496` → `iv_history_service.py:75-89`) executa uma consulta individual no banco de dados para cada ticker analisado, a partir de threads concorrentes, usando essas novas instâncias do cliente.
* **Cenário de falha:** Um scan completo de 150 ativos dispara mais de 150 conexões e queries sequenciais ao Supabase apenas para consultar o IV Rank, estourando os limites de conexão do plano gratuito do Supabase, o que resulta em falhas silenciosas (`iv_rank=None`) e desativação involuntária dos filtros de IV.
* **Correção:** Memoizar a instância do cliente Supabase (Padrão Singleton protegido por lock) e otimizar a coleta do IV Rank buscando os dados históricos dos últimos 252 dias de todos os ativos participantes do scan em uma única query inicial (ou usar cache com TTL de horas, visto que o IV Rank se altera apenas uma vez ao dia).

---

### MÉDIO

#### 🟡 [MÉDIO] `backend/api/main.py:67-74` — CORS `allow_origins=["*"]` com `allow_credentials=True`
* **Problema:** A configuração padrão de CORS permite qualquer origem (`*`) simultaneamente com o envio de cookies e cabeçalhos de credenciais. O Starlette (FastAPI), ao se deparar com esse cenário, ecoa dinamicamente a origem da requisição, anulando a segurança de restrição de domínio.
* **Cenário de falha:** Qualquer página web externa maliciosa aberta pelo usuário consegue efetuar requisições autenticadas para disparar varreduras ou alterar configurações do bot do Telegram.
* **Correção:** Remover o wildcard `*` em ambientes de produção (forçar definição de origens explícitas nas variáveis de ambiente) ou definir `allow_credentials=False` quando o wildcard for necessário.

#### 🟡 [MÉDIO] `backend/services/core_engine.py:50-55` — Resposta vazia do yfinance não é retentada; rate-limit vira "sem dados" silencioso
* **Problema:** O método auxiliar `_baixar_yfinance` retorna `None` imediatamente quando o DataFrame retornado está vazio. Os decoradores de retry e backoff do código cobrem apenas o disparo de exceções. No entanto, o Yahoo Finance responde aos bloqueios de rate-limit devolvendo DataFrames vazios em vez de disparar erros HTTP de rede.
* **Cenário de falha:** Quando o limite de requisições do Yahoo é atingido, cada ticker passa a retornar dados vazios na primeira tentativa e é silenciosamente ignorado. O scan é dado como concluído com sucesso com zero sinais detectados, ocultando a falha sistêmica.
* **Correção:** Tratar explicitamente DataFrames vazios como falhas de rede elegíveis para retry e logar uma métrica consolidada de ativos sem dados após o término do scan.

#### 🟡 [MÉDIO] `backend/services/signal_service.py:135-139` + `core_engine.py:529-530` — Falha de persistência após registrar o cooldown: sinal perdido por 3 dias
* **Problema:** A função `registrar_sinal` roda de forma concorrente em `analisar_ativo` populando o cooldown na memória, mas o método `persist_signals` (que de fato insere no Supabase) roda posteriormente e captura de forma genérica qualquer exceção com um `logger.error`.
* **Cenário de falha:** Se o Supabase estiver fora do ar temporariamente durante o salvamento em lote, a gravação falha e o erro é engolido. O cooldown já foi marcado na memória do servidor e a notificação do Telegram foi enviada. Como o banco de dados não salvou os sinais, eles não aparecem no painel web, e a restrição de cooldown impede o motor de emitir o mesmo sinal nos próximos 3 dias, gerando inconsistência de estado irremediável.
* **Correção:** Implementar uma estratégia de retry com backoff no insert do banco (ou uma fila de persistência offline a ser processada em background) e apenas atualizar o cooldown de memória após a confirmação de escrita bem-sucedida no Supabase.

#### 🟡 [MÉDIO] `backend/core/cache.py:39-44` — `_mem` (fallback de cache) mutado por 10 threads concorrentes sem lock
* **Problema:** A função `_mem_set` itera sobre `_mem.items()` para realizar a limpeza (pruning) de registros expirados ao mesmo tempo que as threads de análise estão inserindo ou removendo dados do mesmo dicionário global sem o uso de locks de exclusão mútua.
* **Cenário de falha:** Sob carga concorrente do scan, ocorre um erro `RuntimeError: dictionary changed size during iteration` dentro de `cache_set_df`. A exceção se propaga até `_carregar_ohlcv` e faz com que a análise daquele ticker seja completamente descartada pelo bloco `except` genérico, causando perda intermitente de sinais.
* **Correção:** Proteger as operações de leitura e escrita do dicionário `_mem` com um `threading.Lock` ou realizar a conversão para lista (`list(_mem.items())`) antes de iterar para prune.

#### 🟡 [MÉDIO] `backend/services/signal_service.py:175` + `config.py:121-137` — Mistura de datetimes naive UTC vs. naive local no cooldown
* **Problema:** O método `rebuild_historico_sinais` normaliza os timestamps convertendo-os para UTC naive (`.replace(tzinfo=None)` sobre timestamp UTC do Supabase), enquanto as funções `registrar_sinal` e `is_reentrada_valida` realizam cálculos usando `datetime.now()` (timezone naive local).
* **Cenário de falha:** Se o servidor estiver operando no fuso horário `America/Sao_Paulo` (UTC-3), os registros reconstruídos parecerão estar 3 horas "no futuro" em relação ao relógio local, distorcendo o cálculo da diferença de dias e afetando o controle da janela de reentrada perto do limite de 3 dias.
* **Correção:** Padronizar todas as datas do sistema como datetime timezone-aware utilizando o padrão UTC nas duas pontas.

#### 🟡 [MÉDIO] `backend/services/telegram_service.py:104-107` — Resposta do Telegram nunca é verificada; falhas de envio são dadas como sucesso
* **Problema:** O código efetua `requests.post(...)` sem invocar `raise_for_status()`. Erros como 400 Bad Request (ex: sintaxe inválida de Markdown em tickers ou nomes de empresas contendo caracteres reservados) ou 429 Too Many Requests são erroneamente logados como "enviado com sucesso".
* **Cenário de falha:** Nomes de ativos da B3 que possuem caracteres especiais como sublinhados (`_`) quebram a renderização do parser do Telegram, impedindo a entrega da mensagem sem gerar nenhum alerta no log de erro.
* **Correção:** Invocar `raise_for_status()` para capturar falhas HTTP, escapar strings dinâmicas de forma adequada, logar os detalhes da resposta da API em caso de erro, e considerar a migração do parser para `HTML` aplicando escape nativo.

#### 🟡 [MÉDIO] `backend/services/ticker_loader.py:77-84` — Falha no filtro de volume colapsa o universo silenciosamente e fica cacheada por 1 hora
* **Problema:** Se o método `filtrar_por_volume` falhar para todas as requisições de volume de lote devido a rate limit da API do Yahoo, o dicionário de ativos aprovados retorna vazio (`aprovados={}`). Com isso, o universo de busca se reduz apenas aos ativos curados fixos. Esse array degradado é gravado em cache por 3600 segundos.
* **Cenário de falha:** O scanner varre apenas ~50 tickers em vez dos 150 pretendidos nas 2 execuções subsequentes do scanner (durante 1 hora), sem que nenhum aviso claro apareça nos logs do sistema.
* **Correção:** Evitar o salvamento do cache quando o retorno de volumes for vazio, reduzindo o TTL em cenários de erro e gerando log de aviso (`Warning`) com a contagem de ativos.

#### 🟡 [MÉDIO] `backend/api/routers/scan.py:114-118` — `scan_all` lê `last_scan_signals()` global após rodar o scan (leitura de estado compartilhado sem isolamento)
* **Problema:** A função `run_scan` não retorna a lista de sinais gerados diretamente na sua chamada. A rota exposta lê a variável global `_last_scan_sinais` após sua execução. No entanto, essa variável global pode ser sobrescrita a qualquer momento por outros fluxos concorrentes.
* **Cenário de falha:** Um usuário inicia um scan completo via `/scan/all` concorrentemente com a finalização de um scan via SSE; o retorno de um dos fluxos trará as informações pertencentes ao outro.
* **Correção:** Alterar o método `run_scan` para que ele retorne a coleção de sinais gerados e usá-los diretamente para compor a resposta da API.

---

### BAIXO

#### 🟢 [BAIXO] `backend/domain/options_math.py:73` — Condicional inútil em `_proximo_vencimento_b3`
* **Problema:** A expressão `dias_adiante_inicio = 1 if hoje.weekday() == 4 else 1` atribui o valor `1` em ambas as condições de execução. O comentário explicativo indica que o retorno de fallback deveria ser `0` nos outros dias de semana.
* **Cenário de falha:** Caso ocorra uma sexta-feira de vencimento onde o `dte_minimo` permitiria DTE tempo de zero, o vencimento da data atual nunca será considerado.
* **Correção:** Corrigir para `0` o valor do bloco `else` ou remover a verificação mantendo a documentação do comportamento.

#### 🟢 [BAIXO] `backend/api/routers/market.py:113, 189, 367` — Parâmetros de rota (Path Params) sem validação de máscara/padrão
* **Problema:** Diferente de `scan.py` que usa validação regex por parâmetro, os endpoints `/market/opcoes/chain/{ticker}`, `/market/analysis/{ticker}` e `/market/indicators/{ticker}` aceitam qualquer string genérica para interpolação nas queries de APIs de terceiros.
* **Cenário de falha:** A passagem de strings arbitrariamente longas pode gerar requisições de consulta inválidas ou expor o servidor a gargalos de rede por digitação errada.
* **Correção:** Aplicar a validação padrão de rota via Pydantic/FastAPI, ex: `Path(pattern=r"^[A-Za-z0-9]{4,8}$")`.

#### 🟢 [BAIXO] `backend/services/telegram_service.py:18, 77-80` — Credenciais do Telegram salvas em texto limpo no diretório de execução da aplicação
* **Problema:** Em caso de indisponibilidade de variáveis de ambiente, o sistema grava o token do bot em um arquivo local `telegram_config.json` dentro da pasta ativa da aplicação.
* **Cenário de falha:** Risco de commit acidental do arquivo no repositório Git ou exposição do token para acessos indevidos na imagem Docker.
* **Correção:** Garantir que o token seja lido apenas de variáveis de ambiente do sistema ou secrets seguras do Supabase; incluir `telegram_config.json` no arquivo `.gitignore` e `.dockerignore`.

---
---

## 2. Frontend

### CRÍTICO

#### 🔴 [CRÍTICO] `src/app/api/db/signals/route.ts:65-91` — POST insere dados arbitrários usando chave administrativa (*service role*)
* **Problema:** A validação `requireAuth` apenas atesta que o token JWT pertence a um usuário autenticado. Após essa validação, o corpo da requisição é inserido sem tratamento direto na tabela `signals` usando `getSupabaseAdmin()` (chave de privilégio de serviço que ignora políticas RLS), sem verificar se o ID pertence ao usuário autenticado ou aplicar whitelist de parâmetros.
* **Cenário de falha:** Qualquer usuário autenticado consegue disparar requisições POST para `/api/db/signals` informando o UUID de outro usuário no campo `user_id` e injetar dados de sinais arbitrários ou corromper métricas históricas de terceiros.
* **Correção sugerida:** Utilizar validação de schema (ex: Zod) com whitelist estrita de propriedades aceitáveis no banco de dados e forçar `user_id` correspondente ao retornado pelo token JWT decodificado (`auth.userId`).

---

### ALTO

#### 🟠 [ALTO] `src/app/analytics/page.tsx:273,278` — Falta de checagem contra lista vazia em `Math.max` → Exibição de `-Infinity` no painel GEX
* **Problema:** Os indicadores "Max Call GEX Strike" e "Max Put GEX Strike" realizam operações matemáticas `Math.max`/`Math.min` sobre o resultado do filtro `signals.filter(...)` sem verificar se há elementos no array gerado. Apenas a verificação pai (`signals.length > 0`) está presente.
* **Cenário de falha:** Ao abrir um ativo que possui apenas histórico de opções de tipo PUT, a operação sobre as CALLs vazias gera `Math.max(...[]) = -Infinity`, exibindo "R$ -Infinity" na interface.
* **Correção sugerida:** Criar uma função de proteção que retorne "—" se o array filtrado estiver vazio antes de calcular a métrica.

#### 🟠 [ALTO] `src/app/scanner/page.tsx:163-201` e `206-208` — Parâmetros de filtragem da interface de usuário ignorados na requisição
* **Problema:** Os filtros `minVolume` e `minConfidence` são capturados nos estados da UI (linhas 54, 57), mas nunca são repassados aos endpoints de varredura. No scan de ticker individual, apenas os limites de DTE e Delta são passados; na varredura B3 via SSE (linha 168), nenhum parâmetro de query string é repassado ao backend.
* **Cenário de falha:** O usuário define uma confiança mínima de 90% e executa o scanner completo da B3, mas o sistema retorna sinais com baixa confiança (ex.: 40%) porque as restrições não foram trafegadas até a API de execução.
* **Correção sugerida:** Adicionar os filtros de volume e confiança na montagem da query string do endpoint SSE e na requisição de fetch individual, ou remover as opções visualmente caso o motor de backend não ofereça suporte.

#### 🟠 [ALTO] `src/components/OptionAnalyzer.tsx:109-126` — Propagação do cálculo divergente de `normalCDF` para métricas de tela
* **Problema:** O erro na função `normalCDF` afeta diretamente o cálculo de volatilidade implícita (`impliedVol`), preço justo Black-Scholes e os rótulos de precificação (Option Cara/Barata) em `OptionAnalyzer.tsx`. O erro também se propaga nos componentes `GreeksCalculator` (gregas), `StrategiesBuilder` (P&L T+0), `PortfolioDashboard` e no simulador de Monte Carlo.
* **Cenário de falha:** O sistema sugere que uma opção está "barata" induzindo o operador a uma transação com base em métricas matemáticas incorretas exibidas nos widgets.
* **Correção sugerida:** Corrigir a função `normalCDF` no diretório de bibliotecas matemáticas do frontend (utilizando a aproximação através da função de erro `erf(x/√2)`) para normalizar os resultados em todos os componentes.

#### 🟠 [ALTO] `src/components/TickerBar.tsx:50` — TickerBar exibindo dados de mercado simulados fixos em produção
* **Problema:** A rota `/signals` do backend retorna a estrutura `{data: [...]}`. O frontend tenta ler os sinais em `data?.signals ?? []`, que resulta em nulo. Adicionalmente, o método `buildFromSignals` espera propriedades como `price` e `change_pct` que não correspondem aos atributos do modelo `Signal` do backend (`preco_acao`).
* **Cenário de falha:** O painel de cotações permanece travado nos valores estáticos definidos como fallback no código (ex: PETR4 a R$ 36,88 e VALE3 a R$ 68,50), passando a falsa impressão de cotações ao vivo.
* **Correção sugerida:** Ajustar a desestruturação do JSON do backend (`data?.data`), fazer o mapeamento correto do atributo `preco_acao` e exibir um aviso indicativo de dados salvos/fallback em caso de erro de rede.

---

### MÉDIO

#### 🟡 [MÉDIO] `src/app/alerts/page.tsx:146` — Reinicialização de formulário de alertas usando escala numérica inválida
* **Problema:** O slider de score mínimo é configurado com a escala de 1 a 10 (padrão inicial 6). Porém, após submeter a criação de um novo alerta, a rotina de reset reinicia a configuração para o valor `min_score: 60`.
* **Cenário de falha:** Se o usuário cadastrar uma segunda regra logo em seguida sem reajustar manualmente o slider, a regra será persistida no banco exigindo score mínimo de 60. Como o score máximo possível é 10, esse alerta nunca disparará.
* **Correção sugerida:** Ajustar o reset de estado do formulário de alertas para atribuir o valor padrão original de 6.

#### 🟡 [MÉDIO] `src/app/signals/page.tsx:287` — Métrica de performance com taxa de acerto estática (*hardcoded*)
* **Problema:** A taxa de acerto de 82% e o total de 22 operações estão fixados diretamente no HTML do grid de indicadores, simulando serem calculados dinamicamente com os dados do painel.
* **Cenário de falha:** O operador visualiza e baseia sua análise de acertos em métricas ilustrativas, sem notar que o dado não condiz com as estatísticas em tempo real do motor de sinais.
* **Correção sugerida:** Fazer requisição à rota `/signals/performance` para coletar os dados reais consolidados de acerto ou rotular visualmente o indicador como informativo histórico.

#### 🟡 [MÉDIO] `src/app/backtest/page.tsx:28,35` — Seletor de estratégias meramente visual no backtest
* **Problema:** A função `runBacktest` envia em seu payload apenas o ativo e as datas. A estratégia escolhida no dropdown não é transmitida à rota do backend, mas a tela exibe o título formatado como se a estratégia selecionada estivesse rodando.
* **Cenário de falha:** O usuário roda testes comparando "Covered Call" com "Iron Condor" para o mesmo ativo e período e obtém resultados idênticos, sem perceber que o motor rodou a mesma rotina padrão por trás.
* **Correção sugerida:** Enviar o parâmetro da estratégia na requisição do backtest e popular o dropdown dinamicamente consumindo `/backtest/strategies`.

#### 🟡 [MÉDIO] `src/components/SignalCard.tsx:77` — Valor de stop fixo em 43%
* **Problema:** A porcentagem limite de perda em operações de Stop está fixada de forma estática em `-43%`, independente das cotações de stop e prêmio estimado calculados para o sinal.
* **Cenário de falha:** Operações com limites reais de perda muito maiores ou menores são exibidas com o mesmo percentual visual de 43%, induzindo o operador a uma avaliação equivocada do risco da operação.
* **Correção sugerida:** Calcular o percentual real dinamicamente via fórmula `((stop - premio_est) / premio_est * 100)` com tratamento para nulos.

#### 🟡 [MÉDIO] Constante da taxa Selic duplicada com valores conflitantes
* **Problema:** A constante de taxa de juros livre de risco (Selic) está duplicada em 4 componentes com valores diferentes:
  * `OptionAnalyzer.tsx:7` ➔ `10.75%` (`0.1075`)
  * `GreeksCalculator.tsx:55` ➔ `13.5%`
  * `StrategiesBuilder.tsx:30` ➔ `14.75%`
  * `PortfolioDashboard.tsx:34` ➔ `10.75%`
* **Cenário de falha:** O cálculo do preço justo de uma mesma opção apresenta divergências na aba de Análise e no Construtor de Estratégias.
* **Correção sugerida:** Centralizar a variável Selic em `src/lib/config.ts` (ou preferencialmente requisitar dinamicamente da API do backend) e importar este valor nos respectivos componentes.

#### 🟡 [MÉDIO] `src/components/LiveFeed.tsx:12-35,67` — Falta de tratamento de erro na conexão SSE do LiveFeed
* **Problema:** A instância de `EventSource` não possui uma função `onerror` implementada. O esqueleto de carregamento (Skeleton loader) é inacessível na interface devido a uma condição errônea e o indicador visual exibe "Auto-refresh: 5s", contradizendo a mecânica baseada em eventos real-time (SSE).
* **Cenário de falha:** Caso a API do Render hiberne ou a rede caia, o navegador entra em loop silencioso de reconexão. O usuário vê a mensagem "Aguardando novos sinais..." indefinidamente sem qualquer sinalização visual de queda na conexão.
* **Correção sugerida:** Implementar controle de reconexão com backoff e tratamento visual de erro no `onerror`; reestruturar a condicional do esqueleto de carregamento para refletir o estado de busca inicial.

#### 🟡 [MÉDIO] `src/hooks/useSignals.ts:59` — Inscrição do canal SSE ativada apenas uma vez no mount do componente
* **Problema:** A validação `isB3MarketOpen()` que restringe inscrições em tempo real fora do horário de pregão é executada apenas uma única vez na montagem do hook.
* **Cenário de falha:** Se o usuário abre a página antes da abertura do mercado (ex: 09:50 BRT), a conexão não é aberta e não é reagendada para quando o mercado abrir, fazendo os dados de tela permanecerem estáticos.
* **Correção sugerida:** Utilizar um intervalo de tempo recorrente para verificar o status de funcionamento do pregão e gerenciar dinamicamente a ativação e desativação do canal SSE.

#### 🟡 [MÉDIO] `src/app/scanner/page.tsx:411,415,434,438` — Valor `NaN` exibido nos filtros ao limpar campos numéricos
* **Problema:** Apagar o valor de campos numéricos (como DTE ou Delta) resulta em `parseInt('') = NaN` armazenado nos estados.
* **Cenário de falha:** O usuário apaga o número do campo para alterar a entrada, clica no botão de varredura e o sistema dispara requisições contendo parâmetros inválidos como `min_dte=NaN`, recebendo erro HTTP 422 da API.
* **Correção sugerida:** Tratar a entrada impedindo o armazenamento de `NaN` (ex: `setMinDTE(Number.isNaN(v) ? 0 : v)`) ou manter valores como strings vazias no estado e validá-los no momento do submit.

#### 🟡 [MÉDIO] `src/components/GreeksCalculator.tsx:152-155` — Valores iniciais extrapolando os limites dos seletores (sliders)
* **Problema:** Ativos com cotação baixa (ex: MGLU3 a R$ 9,85) semeiam valores de preço e strike nas variáveis `S` e `K`, mas os limites mínimo e máximo dos seletores estão travados fixamente entre 50 e 200.
* **Cenário de falha:** Ao tentar ajustar as gregas para esses ativos, as barras saltam instantaneamente para o limite mínimo de 50, distorcendo o cálculo do gráfico.
* **Correção sugerida:** Alterar as propriedades `min`/`max` dos sliders para serem computadas de forma dinâmica tendo como referência o preço atual do ativo (ex: `S * 0.5` a `S * 1.5`).

#### 🟡 [MÉDIO] `src/lib/supabase-db.ts:63-112` — Funções de mutação expostas no client-side utilizando chave anônima
* **Problema:** Os métodos helper `saveSignal`, `updateSignal` e `deleteSignal` realizam chamadas diretas de escrita no banco de dados através da instância anônima do Supabase client, embora não possuam locais de chamada ativos no código.
* **Cenário de falha:** Se as políticas de RLS da tabela `signals` forem flexibilizadas indevidamente no banco, um usuário consegue apagar ou editar registros diretamente via console do navegador utilizando as funções disponíveis no bundle.
* **Correção sugerida:** Remover as funções utilitárias de escrita do código cliente e garantir a restrição explícita de escrita para chaves públicas (anon) nas políticas RLS do Supabase.

---

### BAIXO

#### 🟢 [BAIXO] `src/components/AssetAnalyzer.tsx:221-222` — Inconsistência de cor e rótulo para Z-Score
* **Problema:** A indicação visual de alerta passa a ser vermelha se o Z-Score for maior que `0`, mas a mensagem textual "Acima da média" exige que o valor seja superior a `1`.
* **Cenário de falha:** Um Z-Score de `0.5` é exibido em vermelho com o texto "(Próximo da média)", confundindo a gravidade do indicador.
* **Correção sugerida:** Unificar os critérios de exibição e alteração cromática a partir do limiar de Z-Score superior a `1`.

#### 🟢 [BAIXO] `src/components/OptionAnalyzer.tsx:287` — Falta do estado visual ATM (At The Money) no indicador de Moneyness
* **Problema:** A condicional avalia apenas `moneynessRaw >= 0 ? 'ITM' : 'OTM'`, marcando opções na linha do dinheiro como ITM.
* **Cenário de falha:** Uma opção exatamente ATM é exibida na interface sob a denominação "ITM 0.0%".
* **Correção sugerida:** Adicionar uma margem de tolerância (ex: de ±0.5% ou preço exato) para classificar o ativo sob a etiqueta "ATM".

#### 🟢 [BAIXO] `src/app/alerts/page.tsx:197` — Contador de sinais do dia exibindo volumetria errada
* **Problema:** O contador de ocorrências utiliza as regras ativas de cruzamento para contar as ocorrências de toda a lista de sinais paginada em memória (que cobre até os últimos 30 dias), embora o rótulo da interface informe "Sinais hoje".
* **Correção sugerida:** Filtrar os itens do cálculo de contagem baseando-se estritamente na data atual antes de exibir o total consolidado.

#### 🟢 [BAIXO] `src/components/SignalCard.tsx:133` — Exibição de `NaN%` no indicador de probabilidade de lucro
* **Problema:** O encadeamento opcional de renderização está posicionado de forma a proteger apenas a operação final de formatação de decimais: `(signal.greeks.prob_profit * 100)?.toFixed(0)`.
* **Cenário de falha:** Se o atributo `prob_profit` for indefinido, a multiplicação retorna `NaN`, gerando a exibição de `NaN%` no cartão do sinal.
* **Correção sugerida:** Adicionar proteção explícita, ex.: `signal.greeks.prob_profit != null ? ... : '—'`.

#### 🟢 [BAIXO] `src/lib/api.ts:3` e `src/lib/config.ts:1` — Variável de ambiente `process.env.API_URL` indisponível no cliente
* **Problema:** Variáveis de ambiente que não possuem o prefixo `NEXT_PUBLIC_` são indefinidas no carregamento pelo bundle do cliente.
* **Cenário de falha:** Se a variável `API_URL` for preenchida no lado do servidor, o processo SSR e o cliente apontarão para endereços de backend distintos, causando erros de execução nas requisições do front.
* **Correção sugerida:** Utilizar a variável com prefixo de visibilidade pública `NEXT_PUBLIC_API_URL` nos arquivos cliente.

#### 🟢 [BAIXO] `src/components/MarketWidget.tsx:127-130` — Evento de atualização manual disparando requisições duplicadas
* **Problema:** Chamar `setOpcoesAttempted(false)` no botão de recarga dispara novamente a busca do useEffect ao mesmo tempo que o manipulador de clique já executa a chamada de recarga.
* **Correção sugerida:** Apenas redefinir o estado indicador da tentativa, deixando a responsabilidade da atualização a cargo do fluxo de efeitos correspondente.

---
---

## 3. Revisão Geral da Arquitetura do Frontend

Identificou-se arquivos com extensão excessiva (acima de 300 linhas) concentrando lógica de dados, gerenciamento de estados, integrações SSE e renderização visual em um único módulo:

1. **`src/app/scanner/page.tsx` (494 linhas):** Acopla o controle de inicialização do backend, SSE, formulários de entrada e exibição.
   * *Correção:* Decompor o arquivo extraindo hooks customizados para a lógica, ex: `useBackendHealth()` e `useBatchScanSSE()`.
2. **`src/app/alerts/page.tsx` (488 linhas):** Contém a manipulação do armazenamento de regras em localStorage, paginação, importação/exportação de CSV e montagem da tabela.
   * *Correção:* Separar as lógicas extraindo o hook `useAlertRules()` e exportar os parsers de CSV para uma função utilitária na pasta `lib`.
3. **`src/app/analytics/page.tsx` (402 linhas):** Acumula rotinas de agregação de curvas de volatilidade implícita, sorrisos de volatilidade e exposição GEX.
   * *Correção:* Mover a agregação e tratamento de dados de smile, surface e GEX para funções puras e testáveis isoladas.

---

## 4. Síntese do Diagnóstico de Concorrência e Próximos Passos

Os dois eixos estruturais que requerem atenção prioritária são:

1. **Segurança de Acesso e Escrita:** Restrição no acesso a rotas sensíveis do backend por meio de tokens de API e contenção de injeção de dados via service role no frontend, garantindo integridade das regras RLS do Supabase.
2. **Isolamento de Estado em Processos Concorrentes:** Correção do gerenciamento de cache, logs, e cooldowns do motor de backend (`_historico_sinais`, `_mem`, etc.) com exclusão mútua por locks para evitar duplicidade de mensagens de alerta no Telegram e na persistência de banco de dados.
