# Segurança — Escopo Revisado

**Data:** 2026-08-15  
**Status:** 🔄 Removendo itens out-of-scope

---

## ❌ Removidos do Escopo

### 1. Autenticação (Completa)
- ❌ Autenticação de usuários (JWT, API keys, Supabase Auth)
- ❌ Rate limiting por usuário/endpoint
- ❌ Autorização de roles
- ❌ Session management

**Motivo:** Out of scope — projeto é interno/pessoal

---

### 2. Telegram (Completa)
- ❌ Integração de alertas Telegram
- ❌ Config de TELEGRAM_TOKEN
- ❌ Bot management
- ❌ Mensageria

**Motivo:** Out of scope — integração externa removida

---

## ✅ Mantém-se no Escopo de Segurança

### 1. Dependências Seguras
- ✅ Pin requirements.txt (versões específicas)
- ✅ pip-audit no CI (detectar CVE)
- ✅ GitHub Dependabot ativado

### 2. Secrets Management
- ✅ Nenhum secret commitado (.gitignore validação)
- ✅ .env.example sem valores reais
- ✅ detect-secrets no CI

### 3. Data Protection
- ✅ Sem exposição de paths em erros (sanitizar `detail`)
- ✅ Sem logging de dados sensíveis (preços, configs)
- ✅ Backup seguro + encryption at rest

### 4. Code Security
- ✅ Validação de input (Pydantic whitelisting)
- ✅ SQL injection prevention (via Supabase ORM)
- ✅ Sem hardcoded values

### 5. Audit & Logging
- ✅ Logs estruturados (não console.log em produção)
- ✅ Sem exposição de stack traces
- ✅ Versionamento de mudanças críticas (migrations)

---

## Recomendações Reduzidas (Sem Auth + Telegram)

### F0 (Rede de Proteção) — Adicionar:
1. ✅ `pip freeze > requirements.txt` + pip-audit CI
2. ✅ detect-secrets no CI (bloqueia commits com .env)
3. ✅ .env.example audit (sem valores sensíveis)

### F1-F8:
- ✅ Pydantic Enum para `tipo_sinal` (whitelisting)
- ✅ CONFIG imutável (`MappingProxyType`) — F4
- ✅ Sanitizar HTTP errors (não expor `detail`)
- ✅ Audit log de mudanças críticas (migrations, config)

### F7 (Observabilidade):
- ✅ Structured logging (JSON, sem secrets)
- ✅ Zero console.log em produção
- ✅ Error sanitization

---

## Matriz Revisada (Sem Auth + Telegram)

| Gap | Severity | Escopo? | Status |
|-----|----------|---------|--------|
| Dependencies não pinadas | 🔴 | ✅ **SIM** | Implementar F0 |
| Secrets commitados | 🔴 | ✅ **SIM** | CI check F0 |
| Error exposure | 🟠 | ✅ **SIM** | Sanitizar F1 |
| Input validation fraca | 🟠 | ✅ **SIM** | Pydantic F1 |
| Audit logging ausente | 🟠 | ✅ **SIM** | F7 + F8 |
| Sem autenticação | ❌ | **NÃO** | Out of scope |
| Telegram inseguro | ❌ | **NÃO** | Out of scope |

---

**Escopo revisado:** Segurança = Dependências + Secrets + Data Protection + Código limpo  
**Out of scope:** Auth, Telegram, Rate limiting por usuário

