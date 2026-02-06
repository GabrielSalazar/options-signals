# 🚀 Guia de Deploy em Produção

Este guia descreve o passo-a-passo para colocar o **B3 Options Signals** no ar (Live) utilizando serviços modernos de nuvem.

---

## 🏗️ 1. Backend (Railway)

O Backend será hospedado no **Railway**, que oferece suporte nativo a FastAPI, Docker e Redis.

### Passos:

1.  Crie uma conta em [railway.app](https://railway.app).
2.  Clique em **"New Project"** -> **"Deploy from GitHub repo"**.
3.  Selecione o repositório `options-signals`.
4.  O Railway detectará automaticamente o `Dockerfile` na pasta `b3-options-signals-py`.
    *   *Nota*: Se ele não detectar a pasta raiz, configure o **Root Directory** nas configurações do serviço para `/b3-options-signals-py`.

### Variáveis de Ambiente (Railway):

Configure as seguintes variáveis na aba **Variables**:

| Variável | Valor Exemplo | Descrição |
| :--- | :--- | :--- |
| `PORT` | `8000` | Porta interna do container |
| `ALLOWED_ORIGINS` | `https://seu-frontend.vercel.app` | URL do frontend (após deploy) |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` | Seu token do BotFather |
| `TELEGRAM_CHAT_ID` | `-100123456789` | ID do canal/grupo de alertas |
| `REDIS_ENABLED` | `true` | Ativar cache |

> **Dica**: Adicione um serviço **Redis** no mesmo projeto do Railway. O Railway injetará automaticamente a variável `REDIS_URL`.

---

## 🎨 2. Frontend (Vercel)

O Frontend será hospedado na **Vercel**, otimizada para Next.js.

### Passos:

1.  Crie uma conta em [vercel.com](https://vercel.com).
2.  Clique em **"Add New..."** -> **"Project"**.
3.  Importe o repositório `options-signals`.
4.  Nas configurações de **Build & Output Settings**:
    *   **Root Directory**: Selecione `b3-options-signals-web` (clique em Edit).
    *   **Framework Preset**: Next.js (automático).

### Variáveis de Ambiente (Vercel):

| Variável | Valor | Descrição |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://web-production-xxxx.up.railway.app` | URL do seu backend no Railway |

> **Importante**: O deploy do Backend deve ser feito **antes** para que você tenha a URL para colocar aqui.

---

## 🔄 3. Fluxo de Atualização (CI/CD)

Como o projeto está conectado ao GitHub:

1.  Qualquer **push** para a branch `main` disparará automaticamente um novo deploy no Railway e na Vercel.
2.  Você pode monitorar os logs de build diretamente nos painéis de controle de cada serviço.

---

## 🩺 4. Verificação Pós-Deploy

Após o deploy, teste se tudo está funcionando:

1.  **Backend Health**: Acesse `https://seu-backend.up.railway.app/health`
    *   Deve retornar `{"status": "healthy", ...}`.
2.  **Frontend**: Acesse `https://seu-frontend.vercel.app`
    *   Verifique se o badge **"DADOS REAIS B3"** aparece.
    *   Teste o **Scanner** com o ticker `PETR4`.

---

## ⚠️ Troubleshooting

*   **Erro de CORS**: Verifique se a variável `ALLOWED_ORIGINS` no Backend contém EXATAMENTE a URL do Frontend (sem barra no final).
*   **Erro de Build no Vercel**: Verifique se o comando de build está rodando `npm install` e `npm run build` corretamente na pasta certa.
*   **Telegram não envia**: Verifique se o bot foi iniciado (`/start`) e se o `CHAT_ID` está correto e o bot é administrador do canal.
