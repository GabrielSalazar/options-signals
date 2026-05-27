# Links e Configuração de Produção — B3 Options Signals v2

## 🌐 Plataformas de Deployment Recomendadas

### Frontend (Next.js 16)
| Plataforma | Recomendação | Link |
|------------|--------------|------|
| **Vercel** | ⭐ Recomendado (oficial Next.js) | [vercel.com](https://vercel.com) |
| Netlify | Boa alternativa | [netlify.com](https://netlify.com) |
| GitHub Pages | Básico | [github.com/pages](https://pages.github.com) |

### Backend (FastAPI)
| Plataforma | Performance | Preço | Link |
|------------|-------------|-------|------|
| **Railway** | Melhor + PostgreSQL | $5-20/mês | [railway.app](https://railway.app) |
| **Render** | Bom + PostgreSQL free | Grátis (com limitações) | [render.com](https://render.com) |
| Fly.io | Excelente + escalável | $0-40/mês | [fly.io](https://fly.io) |
| AWS Lambda | Escalável serverless | Variável | [aws.amazon.com](https://aws.amazon.com) |

### Banco de Dados (Novo!)
| Plataforma | Recomendação | Link |
|------------|--------------|------|
| **Supabase** | ⭐ PostgreSQL + Auth | [supabase.com](https://supabase.com) |
| Render Postgres | Incluído no plano | [render.com](https://render.com) |
| Railway Postgres | Melhor performance | [railway.app](https://railway.app) |

---

## 📋 Passo-a-Passo: Deploy Completo (Gratuito)

### 1️⃣ Frontend no Vercel (Grátis)

```
1. Vá em https://vercel.com → Sign Up
2. Connect GitHub (autorize)
3. Import Repository → Selecione "options-signals"
4. Configure:
   - Framework: Next.js
   - Root Directory: b3-options-signals-web
   - Environment Variables:
     NEXT_PUBLIC_API_URL=https://seu-backend.onrender.com
5. Deploy!
```

**Seu URL ficará:**
```
https://seu-usuario.vercel.app
```

### 2️⃣ Backend no Render (Grátis)

```
1. Vá em https://render.com → Sign Up
2. Connect GitHub
3. New Web Service
4. Configure:
   - Name: b3-options-backend
   - Root Directory: b3-options-signals-py
   - Runtime: Docker
   - Instance: Free
   - Environment:
     ALLOWED_ORIGINS=https://seu-usuario.vercel.app
     REDIS_ENABLED=false
5. Deploy!
```

**Seu URL ficará:**
```
https://b3-options-backend.onrender.com
```

### 3️⃣ Conectar Frontend ↔ Backend

```
1. Volte ao Vercel
2. Settings → Environment Variables
3. Mude: NEXT_PUBLIC_API_URL=https://b3-options-backend.onrender.com
4. Redeploy (git push ou manual)
5. Pronto!
```

---

## 🔗 Links Importantes

### Repositório e Documentação

| Item | Link |
|------|------|
| **GitHub Repository** | https://github.com/GabrielSalazar/options-signals |
| **Setup Supabase** | [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) |
| **API & DB Integration** | [API_AND_DB_INTEGRATION.md](./API_AND_DB_INTEGRATION.md) |
| **Arquitetura Produção** | [ARQUITETURA_PRODUCAO.md](./ARQUITETURA_PRODUCAO.md) |
| **Vercel Setup** | [VERCEL_ONLY_SETUP.md](./VERCEL_ONLY_SETUP.md) |

### Ferramentas e APIs

| Ferramenta | Uso | Link |
|-----------|-----|------|
| **Vercel** | Deploy Frontend Next.js | https://vercel.com |
| **Supabase** | PostgreSQL + Auth + Realtime | https://supabase.com |
| **Railway** | Deploy Backend + PostgreSQL | https://railway.app |
| **Render** | Deploy Backend alternativa | https://render.com |
| **GitHub** | Controle de Versão | https://github.com |
| **Docker** | Containerização | https://docker.com |
| **Telegram Bot** | Notificações de sinais | https://t.me/BotFather |

### Dados Reais e APIs

| Fonte | Dados | Link |
|-------|-------|------|
| **Yahoo Finance** | Preços históricos | https://finance.yahoo.com |
| **StatusInvest** | Dados B3 brasileiros | https://www.statusinvest.com.br |
| **B3 Official** | Info de opções | https://www.b3.com.br |
| **ANBIMA** | Índices | https://www.anbima.com.br |

---

## 🔐 Variáveis de Ambiente Necessárias

### Frontend (Vercel)

```env
# ✅ OBRIGATÓRIO
NEXT_PUBLIC_API_URL=https://seu-backend.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ⭐ OPCIONAL
NEXT_PUBLIC_APP_NAME=B3 Options Signals
```

### Backend (Railway/Render)

```env
# ✅ OBRIGATÓRIO
ALLOWED_ORIGINS=https://seu-frontend.vercel.app
PORT=8000
DATABASE_URL=postgresql://user:pass@localhost/dbname

# ✅ RECOMENDADO
REDIS_ENABLED=true
REDIS_URL=redis://localhost:6379

# ⭐ OPCIONAL - Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID=-1234567890
```

> **Como obter `TELEGRAM_BOT_TOKEN`:**
> 1. Abra Telegram
> 2. Procure por `@BotFather`
> 3. Envie `/newbot`
> 4. Siga as instruções
> 5. Copie o token gerado

---

## 📊 URLs de Produção (Exemplo)

Após completar o deploy, seus URLs serão:

```
🌐 Frontend (Vercel):
   https://seu-usuario.vercel.app
   
🔌 API Backend (Render):
   https://b3-options-backend.onrender.com
   
📚 API Docs (Swagger):
   https://b3-options-backend.onrender.com/docs
   
🏥 Health Check:
   https://b3-options-backend.onrender.com/health
```

---

## ⚙️ Configuração Local para Desenvolvimento

### Setup Rápido (Com Docker)

```bash
# Clone o repositório
git clone https://github.com/GabrielSalazar/options-signals.git
cd options-signals

# Configure variáveis de ambiente
cp .env.example .env.local

# Inicie com Docker
docker-compose up --build

# Acesse
# Frontend: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Supabase Studio: http://localhost:54323
```

### Setup Manual (Sem Docker)

**Terminal 1 — Frontend (Next.js):**
```bash
cd b3-options-signals-web
npm install
npm run dev
# Acessa http://localhost:3000
```

**Terminal 2 — Backend (FastAPI):**
```bash
cd b3-options-signals-py
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Acessa http://localhost:8000
```

**Terminal 3 — Supabase (Docker):**
```bash
# Se usando localmente
docker run --name supabase -p 54323:54323 supabase/supabase:latest
```

---

## 🧪 Endpoints Principais

### Frontend (Next.js API Routes)

```bash
# Health Check
curl http://localhost:3000/api/health

# Listar Sinais
curl http://localhost:3000/api/signals?limit=50

# Escanear Ticker
curl -X POST http://localhost:3000/api/signals/scan \
  -H "Content-Type: application/json" \
  -d '{"ticker": "PETR4"}'

# Estratégias
curl http://localhost:3000/api/strategies

# Listar sinais do banco (Supabase)
curl http://localhost:3000/api/db/signals?ticker=PETR4
```

### Backend Python (FastAPI)

```bash
# Dados reais de opções
curl -X POST http://localhost:8000/signals/scan/PETR4

# Estratégias
curl http://localhost:8000/signals/strategies

# Analytics
curl http://localhost:8000/signals/analytics/PETR4

# Backtest
curl -X POST http://localhost:8000/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "PETR4",
    "strategy_name": "Reversão por IFR (RSI)",
    "days": 252,
    "initial_capital": 10000
  }'
```

---

## 🚨 Problemas Comuns e Soluções

### Erro: "Cannot connect to backend"

**Problema:** Frontend não consegue acessar backend

**Soluções:**
1. Verifique se `NEXT_PUBLIC_API_URL` está sem `/` no final
   ```
   ❌ https://api.com/
   ✅ https://api.com
   ```

2. Verifique se `ALLOWED_ORIGINS` no backend inclui seu frontend:
   ```
   ❌ ALLOWED_ORIGINS=https://seu-site.vercel.app/
   ✅ ALLOWED_ORIGINS=https://seu-site.vercel.app
   ```

3. Teste a saúde do backend:
   ```bash
   curl https://seu-backend.onrender.com/health
   ```

### Render: "Free instance sleeping"

**Problema:** Servidor dorme após inatividade

**Solução:** Normal no plano gratuito. Faça um request para acordar:
```bash
curl https://seu-backend.onrender.com/health
# Aguarde ~50s na primeira requisição
```

### Vercel: "Deployment failed"

**Soluções:**
1. Verifique logs em **Settings** → **Deployments**
2. Certifique-se que `Root Directory` está correto:
   ```
   ✅ b3-options-signals-web
   ❌ /b3-options-signals-web
   ```

3. Verifique se `package.json` existe em:
   ```
   b3-options-signals-web/package.json
   ```

---

## 📱 Monitoramento em Produção

### Health Checks Automáticos

Configure health checks nos seus provedores:

**Vercel:** Automático (monitora builds)

**Render:** Automático (monitora logs)

**Manual (cron job):**
```bash
# Adicione ao seu crontab para acordar o servidor a cada 30 min
*/30 * * * * curl https://seu-backend.onrender.com/health > /dev/null 2>&1
```

---

## 💾 Backup e Dados

### Importante

⚠️ Este projeto usa:
- **Yahoo Finance** para dados históricos (cache local)
- **StatusInvest** para dados B3 (cache Redis)
- **Redis** para cache em memória (não persistente no Render free)

**Dados não são permanentes no Render free.** Para produção real, use:
- Railway ou Fly.io (Redis persistente)
- PostgreSQL/Supabase (dados estruturados)

---

## 🔄 CI/CD Automático

O repositório já tem GitHub Actions configurado:

```
.github/workflows/
├── backend.yml      # Testa e deploya backend
├── frontend.yml     # Testa e deploya frontend
└── docker.yml       # Build e publica imagens
```

Commits em `main` disparam deployment automático!

---

## 📞 Suporte

| Item | Link |
|------|------|
| **Issues** | https://github.com/GabrielSalazar/options-signals/issues |
| **Discussions** | https://github.com/GabrielSalazar/options-signals/discussions |
| **LinkedIn** | https://linkedin.com/in/gabrielsalazar |
| **Email** | gsalazar93@gmail.com |

---

## ✅ Checklist Final de Deploy

Antes de ir para produção:

**Setup Local:**
- [ ] Repository clonado
- [ ] `.env.local` configurado com credenciais
- [ ] `npm install` executado no frontend
- [ ] `pip install -r requirements.txt` no backend
- [ ] Tudo funcionando em localhost

**Supabase:**
- [ ] Conta Supabase criada em [supabase.com](https://supabase.com)
- [ ] Projeto "options-signals-v2" criado
- [ ] Tabelas criadas (signals, strategies, backtest_results)
- [ ] `NEXT_PUBLIC_SUPABASE_URL` copiada
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` copiada
- [ ] RLS policies configuradas

**Backend:**
- [ ] Conta Railway ou Render criada
- [ ] `Dockerfile` presente no diretório raiz
- [ ] `docker-compose.yml` testado localmente
- [ ] Backend deployado
- [ ] Variáveis de ambiente configuradas no servidor
- [ ] Health check respondendo

**Frontend:**
- [ ] Conta Vercel criada
- [ ] GitHub conectado ao Vercel
- [ ] Root directory: `b3-options-signals-web`
- [ ] Environment variables configuradas:
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Frontend deployado
- [ ] `npm run build` passando sem erros

**Testes:**
- [ ] Health check respondendo em produção
- [ ] Login/Registrar funcionando com Supabase
- [ ] Pelo menos 1 sinal escaneado e salvo
- [ ] Telegram bot integrado (opcional)
- [ ] Documentação lida e compreendida

---

## 🎯 Próximos Passos

1. **Imediato:** Preencher `.env.local` com credenciais reais
2. **Setup Supabase:** Seguir [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)
3. **Deploy:** Vercel (frontend) + Railway (backend)
4. **Integração:** Ler [ARQUITETURA_PRODUCAO.md](./ARQUITETURA_PRODUCAO.md)
5. **Customização:** Ajustar estratégias e parâmetros conforme necessário

---

---

## 📚 Documentação Relacionada

Leia esses arquivos para entender melhor:

1. **[SUPABASE_SETUP.md](./SUPABASE_SETUP.md)** — Como configurar PostgreSQL no Supabase
2. **[API_AND_DB_INTEGRATION.md](./API_AND_DB_INTEGRATION.md)** — Detalhes técnicos das API routes
3. **[ARQUITETURA_PRODUCAO.md](./ARQUITETURA_PRODUCAO.md)** — Integração da lógica Python com frontend
4. **[VERCEL_ONLY_SETUP.md](./VERCEL_ONLY_SETUP.md)** — Deploy apenas frontend no Vercel

---

**Última atualização:** 25 de maio de 2026  
**Status:** Pronto para Deploy  
**Stack:** Next.js 16 + FastAPI + Supabase PostgreSQL  
**Autor:** Gabriel Salazar
