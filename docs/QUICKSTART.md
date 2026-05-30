# QuickStart — Como Executar o Projeto B3 Options Signals

## 🚀 Execução Local (Desenvolvimento)

### Pré-requisitos
- **Docker & Docker Compose** (Recomendado — mais fácil)
- OU **Python 3.10+** + **Node.js 18+** (Manual)

---

## Opção 1: Via Docker (⭐ Recomendado)

### 1️⃣ Clone o repositório
```bash
git clone https://github.com/GabrielSalazar/options-signals.git
cd options-signals
```

### 2️⃣ Inicie todos os serviços
```bash
docker-compose up --build
```

Isso iniciará:
- **Backend (FastAPI)** em http://localhost:8000
- **Frontend (Next.js)** em http://localhost:3000
- **Redis Cache** em localhost:6379

### 3️⃣ Acesse a aplicação
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs (Swagger interativo)
- **Health Check:** http://localhost:8000/health

### 4️⃣ Pare os serviços
```bash
docker-compose down
```

---

## Opção 2: Manual (Python + Node.js)

### Backend (Python)

```bash
cd backend

# Crie ambiente virtual
python -m venv venv

# Ative ambiente
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt

# Inicie servidor FastAPI
uvicorn api.main:app --reload --port 8000
```

Backend estará em: **http://localhost:8000**

### Frontend (Next.js)

Em outro terminal na raiz do projeto (`options-signals`):

```bash
# Instale dependências
npm install

# Inicie dev server
npm run dev
```

Frontend estará em: **http://localhost:3000**

---

## 📋 Variáveis de Ambiente

### Backend (.env)

Crie arquivo `.env` em `backend/`:

```env
# API
ALLOWED_ORIGINS=http://localhost:3000
PORT=8000

# Redis (opcional, para cache)
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true

# Telegram (opcional, para notificações)
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui
```

### Frontend (.env.local)

Crie arquivo `.env.local` na raiz do projeto (`options-signals`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🧪 Testando a API

### Health Check
```bash
curl http://localhost:8000/health
```

Response esperado:
```json
{
  "status": "healthy",
  "data_source": "real",
  "sources": {
    "yahoo": "ok",
    "statusinvest": "ok",
    "redis": "ok"
  }
}
```

### Scanner de Sinais
```bash
curl -X POST http://localhost:8000/signals/scan/PETR4
```

Response: Lista de sinais encontrados para PETR4

### API Docs Interativa
Abra no navegador: **http://localhost:8000/docs**
- Teste endpoints diretamente
- Veja schemas de request/response

---

## 🌐 Deploy em Produção

### Frontend (Vercel) ⭐ Recomendado

1. **Conecte o repositório:**
   - Vá em [vercel.com](https://vercel.com)
   - Clique "Add New Project"
   - Selecione repositório `options-signals`

2. **Configure:**
   - **Framework Preset:** Next.js
   - **Root Directory:** `b3-options-signals-web`
   - **Environment Variables:**
     ```
     NEXT_PUBLIC_API_URL=https://seu-backend.com
     ```

3. **Deploy:**
   - Clique em "Deploy"
   - Vercel gera URL automática

**Link do Vercel (seu projeto):**
```
https://seu-nome.vercel.app
```

---

### Backend (Render ou Railway)

#### Opção A: Render (Grátis, com limitações)

1. Vá em [render.com](https://render.com)
2. **New +** → **Web Service**
3. Conecte GitHub
4. Configure:
   - **Name:** `b3-options-backend`
   - **Root Directory:** `b3-options-signals-py`
   - **Runtime:** Docker
   - **Instance Type:** Free
5. **Environment Variables:**
   ```
   ALLOWED_ORIGINS=https://seu-vercel-app.vercel.app
   REDIS_ENABLED=false
   ```
6. **Deploy**

**Link do Render:**
```
https://b3-options-backend.onrender.com
```

> ⚠️ Plano free dorme após inatividade (primeiro request pode levar 50s)

#### Opção B: Railway (Melhor performance)

1. Vá em [railway.app](https://railway.app)
2. **New Project** → Import from GitHub
3. Selecione `options-signals`
4. Configure **Root Directory:** `b3-options-signals-py`
5. **Environment Variables:**
   ```
   ALLOWED_ORIGINS=https://seu-vercel-app.vercel.app
   ```
6. **Deploy**

**Link do Railway:**
```
https://seu-projeto.railway.app
```

---

## 🔗 Conectar Frontend com Backend

Após fazer deploy do backend, **atualize** a variável no frontend:

### Vercel

1. Vá em **Settings** do seu projeto Vercel
2. **Environment Variables**
3. Mude `NEXT_PUBLIC_API_URL` para a URL do backend (ex: `https://b3-options-backend.onrender.com`)
4. Redeploy (commit ou manual)

---

## 📊 Estrutura de Pastas (para referência)

```
options-signals/
├── backend/                         # Backend (FastAPI)
│   ├── api/                         # Endpoints REST e App FastAPI
│   ├── core/                        # Configuração e Cache
│   ├── domain/                      # Regras de Negócio e Opções
│   ├── services/                    # Motor de análise principal
│   ├── requirements.txt
│   └── .env.example
│
├── src/                             # Frontend (Next.js)
│   ├── app/                         # Páginas
│   ├── components/                  # Componentes
│   └── lib/                         # Utilitários
├── package.json
├── Dockerfile
├── .env.local.example
└── docker-compose.yml               # Orquestração
```

---

## 🛠️ Comandos Úteis

### Docker

```bash
# Inicia todos os serviços
docker-compose up

# Inicia em background
docker-compose up -d

# Para os serviços
docker-compose down

# Rebuild das imagens
docker-compose up --build

# Logs do backend
docker-compose logs backend

# Logs do frontend
docker-compose logs frontend

# Acesso ao shell do container
docker-compose exec backend bash
```

### Backend (Python)

```bash
# Testes
cd b3-options-signals-py
pytest tests/

# Verificação de saúde
python test_real_data.py

# Rodar estratégias
python test_strategies.py
```

### Frontend (Node.js)

```bash
cd b3-options-signals-web

# Build de produção
npm run build

# Rodar build localmente
npm run start

# Linter/Formatter
npm run lint
npm run format
```

---

## ⚠️ Troubleshooting

### Erro: "CORS: Origin not allowed"
**Solução:** Verifique `ALLOWED_ORIGINS` no backend (deve incluir URL do frontend)

### Erro: "Cannot connect to backend"
**Solução:** Verifique se `NEXT_PUBLIC_API_URL` está correto (sem `/` no final)

### Redis não inicia
**Solução:** Se usando Docker, verifique se porta 6379 não está em uso:
```bash
lsof -i :6379  # macOS/Linux
netstat -ano | findstr :6379  # Windows
```

### Vercel: "Build failed"
**Solução:** Verifique logs em Vercel Dashboard → Deployments → últimas tentativas

### Render: "Free instance sleeping"
**Solução:** Normal no plano gratuito. Faça um request para "acordar" o servidor

---

## 📚 Próximos Passos

1. **Entender o algoritmo:**
   - Leia [MONTAGEM_DE_SINAL_B3.md](./MONTAGEM_DE_SINAL_B3.md)
   - Leia [ESTRATEGIAS_OPCOES_B3.md](./ESTRATEGIAS_OPCOES_B3.md)

2. **Explorar a API:**
   - Acesse http://localhost:8000/docs
   - Teste endpoints interativamente

3. **Customizar:**
   - Modifique parâmetros em `app/core/models.py`
   - Ajuste thresholds em `config.py`

4. **Deploy em produção:**
   - Siga passos de Vercel + Render/Railway acima

---

## 🆘 Suporte

- **Documentação técnica:** Veja `DOCUMENTACAO_scanner_opcoes_b3_v3.md`
- **Integração em produção:** Veja `ARQUITETURA_PRODUCAO.md`
- **Issues:** Abra em [GitHub Issues](https://github.com/GabrielSalazar/options-signals/issues)

---

**Versão:** 3.0+ com Stack Profissional  
**Última atualização:** 25 de maio de 2026  
**Status:** Pronto para Desenvolvimento e Produção
