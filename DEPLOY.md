# 🚀 Guia de Deploy em Produção

Este guia descreve opções para colocar o **B3 Options Signals** no ar.

---

## 🛠️ Opção 1: Render (Recomendado - Grátis)

O **Render** possui um plano gratuito ("Free Instance") que suporta Docker e Python, ideal para testes sem cartão de crédito.

### 1. Backend (Python) no Render:

1.  Crie conta em [render.com](https://render.com).
2.  Clique **New +** -> **Web Service**.
3.  Conecte seu GitHub e selecione o repositório `options-signals`.
4.  Configure:
    *   **Name**: `b3-backend`
    *   **Root Directory**: `b3-options-signals-py` (⚠️ IMPORTANTE)
    *   **Runtime**: **Docker** (Ele usará o Dockerfile que criamos)
    *   **Free Instance Type**: Selecione a opção Free.
5.  **Environment Variables** (Advanced):
    *   `PORT`: `8000`
    *   `ALLOWED_ORIGINS`: `https://seu-frontend.vercel.app` (Preencha depois de criar o frontend)
    *   `TELEGRAM_BOT_TOKEN`: `...`
6.  Clique em **Create Web Service**.

> *Nota: O plano free do Render "dorme" após inatividade. O primeiro request pode levar 50s para acordar.*

---

## 🚂 Opção 2: Railway (Melhor Performance)

Se você preferir o Railway (que deu erro de *Railpack*), o problema é a **pasta raiz**. Como temos backend e frontend no mesmo repositório, precisamos indicar onde está o código.

### Correção do Erro "Fail to create build plan":

1.  No seu projeto Railway, clique no serviço `options-signals`.
2.  Vá em **Settings**.
3.  Procure por **Root Directory**.
4.  Mude de `/` para `/b3-options-signals-py`.
5.  O Railway vai disparar um novo deploy automaticamente e deve funcionar!

---

## 🎨 Frontend (Vercel)

O Frontend deve ser hospedado na **Vercel** (Melhor opção para Next.js).

1.  Crie conta em [vercel.com](https://vercel.com).
2.  **Add New Project** -> Importe `options-signals`.
3.  **Framework Preset**: Next.js.
4.  **Root Directory**: Clique em Edit e selecione `b3-options-signals-web`.
5.  **Environment Variables**:
    *   `NEXT_PUBLIC_API_URL`: A URL do seu backend (ex: `https://b3-backend.onrender.com` ou Railway URL).
6.  Clique em **Deploy**.

---

## 🔄 Resumo das Variáveis

| Serviço | Variável | Valor |
| :--- | :--- | :--- |
| **Backend** | `ALLOWED_ORIGINS` | URL do Frontend (sem a barra final `/`) |
| **Backend** | `TELEGRAM_BOT_TOKEN` | Seu token do BotFather |
| **Frontend** | `NEXT_PUBLIC_API_URL` | URL do Backend (ex: `https://...`) |

---

## ⚠️ Troubleshooting Comum

1.  **Erro de CORS (Bloqueio no navegador)**:
    *   Acesse os logs do Backend. Se vir algo como "Origin ... not allowed", adicione a URL exata do frontend na variável `ALLOWED_ORIGINS` do backend.

2.  **Frontend Quebrado (404/500)**:
    *   Verifique se `NEXT_PUBLIC_API_URL` não tem uma barra `/` no final.
    *   Certo: `https://api.com`
    *   Errado: `https://api.com/`

3.  **Render lento**:
    *   No plano free, o servidor desliga se ninguém usar. Mande um comando `/start` no Telegram para "acordar" ele antes de usar o site.
