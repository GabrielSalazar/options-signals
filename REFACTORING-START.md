# 🚀 Refatoração B3 Options Signals — Quick Start

**Data:** 2026-08-14  
**Status:** ✅ Tudo configurado. Pronto para começar a Fase 0.

---

## 📋 O que foi entregue

### 1. **Plano de Refatoração Completo**
- **9 fases** detalhadas (F0-F8)
- **34 dias úteis** de trabalho (24 dias com paralelização)
- Risco/mitigação mapeado para cada fase
- Timeline com dependências

**Arquivo:** `docs/superpowers/plans/2026-08-14-refactoring-plan-complete.md`

### 2. **5 Ferramentas Complementares**
Instaladas globalmente em `~/.gemini/tools`:
- **ruflo** — Automação de workflows
- **agency-agents** — Orquestração de agentes paralelos
- **ecc** — Linting e validação de código
- **gstack** — Scaffolding e geração de boilerplate
- **claude-mem** — Memória persistente e state tracking

**Arquivo:** `docs/superpowers/plans/TOOLS-INTEGRATION.md`

### 3. **Configuração Global**
- `~/.gemini/tools-config.json` — Mapa de ferramentas
- `~/.gemini/.env` — Variáveis de ambiente
- `~/.gemini/setup-tools.ps1` — Script de setup (já executado)

---

## 🎯 Começar a Executar o Plano

### **Passo 1: Leitura Rápida do Plano**
```
5 minutos: Leia o Sumário Executivo (acima do arquivo principal)
10 minutos: Revise a Timeline e Matriz de Priorização
```

### **Passo 2: Fase 0 — Rede de Proteção (3 dias)**

Esta é a fase crítica que "tranca" toda refatoração posterior com verificação mecanizada.

**Tasks:**
- [ ] Criar 12 fixtures de OHLCV (casos de borda: empate, volume baixo, veto, cooldown)
- [ ] Implementar golden master (teste que sinal não muda)
- [ ] Pinar dependências Python (requirements.txt com `==`)
- [ ] Adicionar cobertura gate (80% backend, 60% frontend)
- [ ] Adicionar `tsc --noEmit` ao CI

**Usando as ferramentas:**
```bash
# Automação com ruflo
cd ~/.gemini/tools/ruflo
npm install  # Se ainda não fez
ruflo run golden-master-setup

# Rastrear estado com claude-mem
cd ~/.gemini/tools/claude-mem
npm install  # Se ainda não fez
claude-mem snapshot F0-baseline
```

### **Passo 3: Fase 1 — Contrato Tipado (5 dias)**
- [ ] Criar modelo Pydantic `Signal`
- [ ] Gerador automático de tipos TS
- [ ] Validação de contrato (modelo × SQL × TS)
- [ ] Fechar 14 campos em drift

**Usando as ferramentas:**
```bash
# Scaffolding com gstack
cd ~/.gemini/tools/gstack
gstack scaffold pydantic-model Signal

# Paralelização com agency-agents
cd ~/.gemini/tools/agency-agents
agency-agents run --task="generate-ts-types" --parallel
```

### **Passo 4: Continuar as Próximas Fases**
Seguir o mesmo padrão:
1. Ler o objetivo da fase no arquivo do plano
2. Usar as ferramentas para automatizar/paralelizar
3. Validar com `claude-mem compare-golden-master`
4. Registrar snapshot com `claude-mem`

---

## 🔄 Fluxo de Trabalho Recomendado

### **Por Dia:**

```
09:00 - Revisar plan (5 min) + status anterior (5 min)
09:10 - Executar tarefa principal com ferramentas
11:30 - Coffee break + validação com golden master
12:00 - Merge se verde, ou investigar divergência
14:00 - Próxima tarefa (fases paralelas se aplicável)
17:30 - Snapshot com claude-mem + commit de progresso
```

### **Por Fase:**

```
Início:  Ler objective da fase
Meio:    Usar ruflo/agency-agents/gstack conforme aplicável
Fim:     Validar com golden master + tsc + ecc audit
Commit:  git commit com checkpoint da fase
Snapshot: claude-mem save-phase-{N}
```

---

## 📊 Checklist de Início

**Antes de começar F0:**

- [ ] Ler este arquivo
- [ ] Ler Sumário Executivo do plano principal
- [ ] Verificar que as ferramentas estão acessíveis:
  ```bash
  Get-Content ~/.gemini/tools/INDEX.json | ConvertFrom-Json
  ```
- [ ] Entender a regra de ouro: **golden master valida tudo**
- [ ] Confirmar que `pytest`, `npm`, `tsc` funcionam no projeto

**Primeiros 15 minutos de F0:**

```bash
cd C:\Users\salazarg\.gemini\antigravity-ide\scratch\options-signals

# 1. Pinar requirements.txt
pip freeze > requirements-freeze.txt
# Revisar e copiar para requirements.txt com ==

# 2. Adicionar tsc --noEmit ao CI
# Editar .github/workflows/ci.yml

# 3. Criar fixture de teste
mkdir -p tests/fixtures/ohlcv
# (colocar 1-2 dados reais como CSV para começar)
```

---

## ⚠️ Regras Importantes

### **1. Golden Master é Lei**
Toda fase **intermediária** precisa ser verde no golden master. Se falhar, rollback imediato:
```bash
git revert HEAD  # Voltar commit anterior
```

### **2. Uma Fase = Um PR**
Não misturar fases em um único PR. Isso mantém reversibilidade e clareza.

### **3. Commit Frequentemente**
Extrações mecânicas = um commit por extração.
Mudanças de comportamento = commit separado.

### **4. Nenhuma Regressão de Sinal**
Se o motor emitir um sinal diferente, é bloqueador. Não mergeiar.

### **5. Usar as Ferramentas Consistentemente**
- **ruflo**: pipeline principal
- **agency-agents**: paralelizar quando possível
- **claude-mem**: snapshots ao fim de cada fase
- **ecc**: validação antes de commit
- **gstack**: boilerplate conforme necessário

---

## 📞 Suporte Rápido

### **O golden master falha — o que faço?**
1. Rodar em verbose: `pytest tests/test_golden_master_motor.py -vv`
2. Se o sinal mudou: não é bug, é regressão — não mergear
3. Se o sinal não mudou mas test falha: bug no teste — corrigir
4. Em dúvida: `git diff` e comparar byte-a-byte

### **Uma ferramenta não funciona — o que faço?**
```bash
# Reinstalar dependências
cd ~/.gemini/tools/{ferramenta}
npm install

# Verificar versão
{ferramenta} --version
```

### **Quero sair da Fase N e voltar para N-1**
```bash
git reset --hard origin/main  # Volta tudo
# (ou)
git revert HEAD~N  # Se já foi mergeado
```

---

## 🎓 Exemplo: Primeiro Dia (F0 Início)

```bash
# 09:00 — Setup
cd C:\Users\salazarg\.gemini\antigravity-ide\scratch\options-signals
git checkout -b f0-rede-protecao

# 09:15 — Criar fixtures
mkdir -p tests/fixtures/ohlcv
# Copiar 3-4 casos reais em CSV

# 09:45 — Criar golden master
# Editar tests/test_golden_master_motor.py
# Rodar primeira vez (vai falhar — criar baseline)
pytest tests/test_golden_master_motor.py --basepath=tests/fixtures

# 11:30 — Validar
pytest  # Todos os testes devem passar

# 12:00 — Commit
git add .
git commit -m "f0: golden master com 3 fixtures"

# 12:15 — Próxima tarefa (pin de deps)
# Editar requirements.txt

# 17:30 — Snapshot
claude-mem snapshot f0-day1
git commit -m "f0: snapshot de progresso"
```

---

## 📚 Arquivos Principais a Acompanhar

| Arquivo | Descrição | Atualizar a cada |
|---------|-----------|------------------|
| `docs/superpowers/plans/2026-08-14-refactoring-plan-complete.md` | Plano completo | 1 semana (para feedback) |
| `docs/superpowers/plans/TOOLS-INTEGRATION.md` | Guia de ferramentas | Conforme adiciona ferramenta |
| `.github/workflows/ci.yml` | Pipeline CI | Toda fase (adiciona gate novo) |
| `pyproject.toml` | Config pytest/ruff | F0 e F7 |
| `vitest.config.ts` | Config cobertura TS | F0 e F6 |

---

## 🎯 Próximo Passo Exato

1. **Agora:** Ler este arquivo + Sumário Executivo
2. **Hoje:** Começar F0 com passo 1 (criar fixtures)
3. **Amanhã:** Golden master + cobertura gate
4. **Dia 3:** Finalizar F0 e validar que tudo está verde

**Então:** Primeira extração da Fase 1 (modelo Pydantic).

---

**Bom trabalho! 🚀**
