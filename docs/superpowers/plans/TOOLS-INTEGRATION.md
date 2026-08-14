# Integração de Ferramentas Complementares ao Plano de Refatoração

**Data:** 2026-08-14  
**Status:** ✅ Ferramentas Instaladas Globalmente

---

## 📦 Ferramentas Instaladas

| Ferramenta | Caminho | Função | Fase do Plano |
|-----------|---------|--------|--------------|
| **ruflo** | `~/.gemini/tools/ruflo` | Automação e orquestração de workflows | F0-F8 |
| **agency-agents** | `~/.gemini/tools/agency-agents` | Coordenação de agentes paralelos | F2, F5, F6 |
| **ecc** | `~/.gemini/tools/ecc` | Enterprise Code Compliance (linting, auditorias) | F7, F8 |
| **gstack** | `~/.gemini/tools/gstack` | Scaffolding e geração de código boilerplate | F1, F3, F5 |
| **claude-mem** | `~/.gemini/tools/claude-mem` | Memória persistente e state management | Todas |

---

## 🎯 Utilização por Fase

### **FASE 0 — Rede de Proteção**
**Ferramentas:** ruflo + claude-mem

```bash
# Automação de fixture generation
ruflo run golden-master-setup

# Salvar estado de cobertura baseline
claude-mem save-baseline --coverage=backend,frontend
```

**Objetivo:** Automatizar criação de fixtures OHLCV e gate de cobertura.

---

### **FASE 1 — Contrato Tipado**
**Ferramentas:** gstack + agency-agents + claude-mem

```bash
# Gerar boilerplate de modelo Pydantic
gstack scaffold pydantic-model Signal --path=backend/domain

# Gerar tipos TS em paralelo
agency-agents run --task="generate-ts-types" --parallel=true

# Registrar evolução do contrato
claude-mem track-schema --before=migration_010 --after=migration_011
```

**Objetivo:** Codificar uma fonte única de verdade para o sinal com geração automática de tipos.

---

### **FASE 2 — Decomposição do core_engine**
**Ferramentas:** ruflo + agency-agents + claude-mem

```bash
# Orquestrar extração mecânica das 7 etapas
ruflo pipeline extract-modules \
  --source=backend/services/core_engine.py \
  --stages=7 \
  --test-after-each=true

# Paralelizar decomposição de diferentes módulos
agency-agents run --task="extract-triggers" --parallel \
                  --task="extract-puck-filters" --parallel \
                  --task="extract-option-structure" --parallel

# Validar que regressão não ocorreu
claude-mem compare-golden-master --phase=F2
```

**Objetivo:** Quebrar 959 linhas em módulos testáveis, preservando comportamento.

---

### **FASE 3 — Roteadores Magros**
**Ferramentas:** gstack + ecc

```bash
# Gerar serviço de market analysis
gstack scaffold service MarketAnalysis --path=backend/services

# Validar que imports estão corretos (sem _self)
ecc audit imports --path=backend/api/routers/market.py
```

**Objetivo:** Extrair lógica de handlers, eliminar `_self`.

---

### **FASE 4 — Estado Global**
**Ferramentas:** gstack + agency-agents

```bash
# Gerar CooldownRepository com duas implementações
gstack scaffold repository Cooldown \
  --impl=InMemory,Redis \
  --path=backend/services

# Testar concorrência com 2 instâncias
agency-agents simulate --instances=2 \
  --test=test_cooldown_distributed.py \
  --backend=redis
```

**Objetivo:** Eliminar mutação global, preparar para scale-out.

---

### **FASE 5 — Dados Frontend Único**
**Ferramentas:** gstack + agency-agents + claude-mem

```bash
# Gerar camada de API tipada com SWR
gstack scaffold api-client TypeScript \
  --framework=swr \
  --schema=backend/domain/signal.py

# Remover 4 caminhos de dados em paralelo
agency-agents run --task="migrate-to-swr" \
                  --task="extract-use-sse" \
                  --task="remove-cached-fetch" --parallel

# Rastrear remoção de `console.*`
ecc audit logs --path=src --remove=true
```

**Objetivo:** Um caminho de dados com SWR, sem cache caseiro.

---

### **FASE 6 — UI e CSS**
**Ferramentas:** gstack + ecc + claude-mem

```bash
# Gerar componentes e extrair lógica
agency-agents run --task="split-signal-card" \
                  --task="split-strategies-builder" \
                  --task="split-asset-analyzer" --parallel

# Validar tamanho e cobertura
ecc audit components \
  --max-lines=250 \
  --min-coverage=80

# Testar visualmente com screenshots
claude-mem screenshot-baseline --routes=8
```

**Objetivo:** Componentes coesos, cobertura 80%.

---

### **FASE 7 — Erros e Observabilidade**
**Ferramentas:** ecc + ruflo

```bash
# Auditar todos os except genéricos
ecc audit exceptions --path=backend --fix=true

# Validar lint BLE/S110
ecc lint --enable=BLE,S110 --path=backend

# Registrar métricas baseline
ruflo metrics save-baseline --path=/metrics
```

**Objetivo:** Zero falhas invisíveis, 6 métricas expostas.

---

### **FASE 8 — Higiene**
**Ferramentas:** ecc + gstack

```bash
# Remover código morto
ecc cleanup dead-code --path=. --remove=true

# Atualizar documentação
gstack docs generate --path=docs --schema=backend

# Validar .env.example
ecc audit env-vars --generate=.env.example
```

**Objetivo:** Fechar débito residual.

---

## 🔧 Configuração Global

**Variáveis de ambiente (salvas em `~/.gemini/.env`):**
```bash
TOOLS_PATH=C:\Users\salazarg\.gemini\tools
CLAUDE_MEM_PATH=$TOOLS_PATH\claude-mem
RUFLO_PATH=$TOOLS_PATH\ruflo
AGENCY_AGENTS_PATH=$TOOLS_PATH\agency-agents
ECC_RULES=$TOOLS_PATH\ecc\rules
```

**Adicionar ao `.claude/settings.json`:**
```json
{
  "toolsPath": "C:\\Users\\salazarg\\.gemini\\tools",
  "integrations": {
    "ruflo": {
      "enabled": true,
      "pipelines": "C:\\Users\\salazarg\\.gemini\\tools\\ruflo\\pipelines"
    },
    "ecc": {
      "rules": "C:\\Users\\salazarg\\.claude\\rules\\ecc"
    }
  }
}
```

---

## 🚀 Começar a Usar

### 1. Instalar dependências (opcional)
```bash
cd ~/.gemini/tools/ruflo && npm install
cd ~/.gemini/tools/agency-agents && npm install
cd ~/.gemini/tools/claude-mem && npm install
```

### 2. Verificar instalação
```bash
# Listar ferramentas
Get-Content ~/.gemini/tools/INDEX.json | ConvertFrom-Json

# Testar integração
ruflo version
agency-agents --help
ecc --version
```

### 3. Integrar ao projeto
```bash
# Dentro do projeto options-signals
cd C:\Users\salazarg\.gemini\antigravity-ide\scratch\options-signals

# Criar arquivo de configuração local
Copy-Item ~/.gemini/tools-config.json .claude/tools-config.json
```

---

## 📊 Métricas de Uso

**Esperado durante o plano:**
- **ruflo:** 8-10 pipelines (uma por fase)
- **agency-agents:** 15-20 tarefas paralelas (fases 2, 5, 6)
- **claude-mem:** 50+ snapshots (state de cada etapa)
- **ecc:** 200+ auditorias (linting contínuo)
- **gstack:** 10-15 scaffolds (boilerplate gerado)

---

## ⚠️ Notas Importantes

1. **Prioridade ao plano:** Essas ferramentas **auxiliam**, não substituem o julgamento manual
2. **Golden master é crítico:** Sempre validar com `claude-mem compare-golden-master` após mudanças
3. **Reversão rápida:** Todas as ferramentas geram logs auditáveis para rollback
4. **Documentação:** Manter `docs/superpowers/plans/` atualizado com snapshots de `claude-mem`

---

## 📌 Próximas Ações

- [ ] Instalar dependências npm das ferramentas
- [ ] Integrar ao `.claude/settings.json`
- [ ] Validar permissões (ruflo precisa de write em `/metrics`)
- [ ] Criar primeiro snapshot com `claude-mem` (F0 baseline)
- [ ] Começar F0 com automação via ruflo

**Status:** ✅ Instalação completa, pronto para iniciar Fase 0
