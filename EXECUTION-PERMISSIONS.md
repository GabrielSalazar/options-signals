# Permissões de Execução — Plano de Refatoração v3

**Data:** 2026-08-15  
**Autorizado por:** Usuário (gsalazar93)  
**Escopo:** Execução autônoma do PLANO-FINAL-v3-PRONTO-PARA-EXECUCAO.md  
**Modo:** /goal-loop com permissões amplas

---

## ✅ PERMITIDO

### Operações de Arquivo
- ✅ Criar pastas e estruturas de diretório
- ✅ Criar novos arquivos (.py, .ts, .md, .json, .yml)
- ✅ Editar arquivos existentes
- ✅ Mover/renomear arquivos
- ✅ Deletar arquivos obsoletos/mortos

### Comandos de Desenvolvimento
- ✅ `pip install` / `pip freeze` (dependências Python)
- ✅ `npm install` / `npm run` (frontend)
- ✅ `pytest` (testes backend)
- ✅ `npm test` / `vitest` (testes frontend)
- ✅ `git add` / `git commit` (commits estruturados)
- ✅ `git branch` / `git checkout` (criar branches)
- ✅ `python -m` (rodar módulos)
- ✅ `node scripts/` (scripts customizados)

### Operações de Banco de Dados
- ✅ `alembic upgrade` / `alembic downgrade` (migrations)
- ✅ Criar arquivos de migração `.sql`
- ✅ Validar schema (sem destruir dados)

### CI/CD
- ✅ Modificar `.github/workflows/*.yml`
- ✅ Adicionar linters/checkers no CI
- ✅ Criar GitHub Actions novos

### Documentação
- ✅ Criar/editar arquivos `.md`
- ✅ Gerar codemaps
- ✅ Atualizar READMEs

---

## 🔴 NÃO PERMITIDO (Comandos Perigosos)

### ⛔ Destruição de Dados
- ❌ `git reset --hard`
- ❌ `git push --force` (força push to main/master)
- ❌ `rm -rf` (deleção recursiva sem backup)
- ❌ Dropar tabelas/databases sem backup prévio
- ❌ Limpar `.env` / secrets sem backup

### ⛔ Operações de Infraestrutura Destrutivas
- ❌ Deletar branches remotas
- ❌ Resetar secrets/credenciais sem rotação
- ❌ Modificar deployment pipelines (Render, Railway) sem validação
- ❌ Limpar cloud buckets/storage

### ⛔ Bypass de Segurança
- ❌ `git commit --no-verify` (pular hooks)
- ❌ Hardcoded secrets/credentials
- ❌ Desabilitar linters/type-checking
- ❌ `--force-all` ou `--dangerously-skip` flags

### ⛔ Mudanças em Configuração Crítica
- ❌ Modificar `pyproject.toml` versão principal sem aprovação
- ❌ Alterar `package.json` sem análise de incompatibilidade
- ❌ Mudar database schema sem migration

---

## 🟡 REQUER CONFIRMAÇÃO

Estes comandos são permitidos mas requerem log/checkpoint antes:

| Comando | Checkpoint |
|---------|------------|
| `git push` | Log do que foi commitado |
| Migração de dados | Backup antes + restore test |
| Alteração schema principal | Migração reversível + rollback test |
| Deployment (Render→Railway) | Dry-run + health check |

---

## 📋 Checklist de Segurança (Pré-Commit)

Antes de cada commit, validar:

- [ ] Nenhum `.env` ou credencial foi adicionado
- [ ] Nenhum `console.log` em produção
- [ ] Nenhuma senha em strings
- [ ] `git diff` revisto antes de push
- [ ] Tests passando (backend + frontend)
- [ ] Type-checking passando (`tsc --noEmit`)

---

## 🎯 Escopo de Execução

### Fase Atual (TODAY + TOMORROW)
1. ✅ Criar 3 ECC docs (GIT-STRATEGY, QUALITY-GATES, AGENT-ORCHESTRATION)
2. ✅ Investigar golden master snapshots
3. ✅ Add linter para silent exceptions
4. ✅ Medir coverage baseline

### Fases Próximas (PRÉ-F0 em paralelo)
1. ✅ PRÉ-F0.0-S: Pin deps + detect-secrets (1d)
2. ✅ PRÉ-F0.0-D: Migrations tooling (1d)
3. ✅ PRÉ-F0.0-I: Railway migration (2d)

### Retomar Conforme Necessário
- F0: Golden Master full setup
- F1-F8: Refactoring phases (28 dias)

---

## 📍 Pontos de Verificação

Após cada dia de execução:

1. ✅ Commit logs revisados
2. ✅ Tests ainda passam
3. ✅ Git status limpo
4. ✅ Nenhum arquivo sensível modificado
5. ✅ Documentação atualizada

---

## 🔐 Autorização Formal

**Usuário:** gsalazar93  
**Data:** 2026-08-15  
**Modo:** Autonomous /goal-loop  
**Válido até:** Até conclusão de v3 (ou até cancelamento explícito)

**Para cancelar/restringir:** Diga "pausar" ou "restrições"

---

**Status:** ✅ Permissões de execução ATIVAS  
**Próxima ação:** Iniciar /goal-loop com plano de implementação

