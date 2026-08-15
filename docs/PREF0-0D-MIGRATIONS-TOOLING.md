# PRÉ-F0.0-D Migrations Tooling — Supabase

**Data:** 2026-08-15  
**Status:** ✅ Documentação + Tooling Setup  
**Infraestrutura:** Supabase PostgreSQL

---

## 📊 Inventário de Migrations Existentes

```
supabase/migrations/
├── 001_performance.sql           (Índices, tuning)
├── 002_score_tecnico_bonus_sessao.sql
├── 003_telegram_config.sql
├── 004_camada1_iv_signals.sql
├── 005_iv_history.sql
├── 006_camada2_motor_score.sql
├── 008_enable_rls.sql
├── 010_constraints_integridade.sql
├── 011_signals_schema_completo.sql
├── 012_fix_signal_id_uuid.sql    ← Crítica: signal_id UUID migration
├── 013_option_liquidity.sql
├── 014_calendar_events.sql
├── 015_signals_liquidity_columns.sql
├── 016_signals_puck_columns.sql
├── 017_signals_v2_puck_telemetry.sql
└── (18+ TBD)
```

**Total:** 17 migrations aplicadas  
**Sequência:** 001 → 017 (com gaps em 007, 009)

---

## 🔧 Tooling Strategy

### Option: Supabase CLI (Recomendado)

**Instalação:**
```bash
npm install -g supabase@latest
supabase --version
```

**Commands:**
```bash
# Listar migrations aplicadas
supabase db status

# Criar nova migration
supabase migration new <name>  # cria supabase/migrations/<timestamp>_<name>.sql

# Aplicar migrations
supabase db push

# Rollback último (se possível)
supabase db reset
```

**Vantagens:**
- ✅ Integrado com Supabase cloud
- ✅ Type-safe migrations (com TypeScript schema)
- ✅ Versionamento automático (timestamps)
- ✅ Rollback automático em caso de erro

---

## 🔄 Reversibility & Rollback (Crítico)

### Boa Prática: Migrations Reversíveis

**Padrão:**
```sql
-- 018_example_reversible.sql

-- UP
BEGIN;
  ALTER TABLE signals ADD COLUMN new_field VARCHAR(255);
  CREATE INDEX idx_signals_new ON signals(new_field);
COMMIT;

-- DOWN (comentado, mas documentado)
-- BEGIN;
--   DROP INDEX idx_signals_new;
--   ALTER TABLE signals DROP COLUMN new_field;
-- COMMIT;
```

**Porquê:**
- Refactoring pode quebrar dados
- Precisa de rollback rápido
- Production reliability

### Índices (PRÉ-F0.0-D)

**PRÉ-REQUISITO CRÍTICO:** Índice em trigger_outcomes.signal_id

```sql
-- 018_add_signal_id_index.sql
BEGIN;
  CREATE INDEX idx_trigger_outcomes_signal_id 
    ON trigger_outcomes(signal_id);
COMMIT;
```

**Por quê?**
- Queries que joinam signals ↔ trigger_outcomes precisam deste índice
- Sem índice: N+1 queries, lentidão
- Com índice: Busca O(log N), rápido

---

## 💾 Backup Strategy

### External Backup (Crítico para Produção)

**Setup:**
```bash
# 1. AWS S3 bucket
aws s3 mb s3://b3-options-signals-backups

# 2. Automated backup script
# scripts/backup_database.sh
```

**Script de Backup:**
```bash
#!/bin/bash

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="supabase_${BACKUP_DATE}.sql.gz"
S3_PATH="s3://b3-options-signals-backups/${BACKUP_FILE}"

# 1. Dump database (via Supabase)
supabase db dump > /tmp/${BACKUP_FILE}

# 2. Upload to S3
aws s3 cp /tmp/${BACKUP_FILE} ${S3_PATH}

# 3. Verify upload
aws s3 ls ${S3_PATH}

# 4. Cleanup local
rm /tmp/${BACKUP_FILE}

echo "Backup completo: ${S3_PATH}"
```

**Frequência:**
- Daily (cron: 2 AM)
- Weekly full backup
- Monthly archive (Glacier)

---

## ✅ Restore Test (Crítico)

**Processo de Validação:**

```bash
# 1. List available backups
aws s3 ls s3://b3-options-signals-backups/

# 2. Download latest
aws s3 cp s3://b3-options-signals-backups/supabase_20260815_020000.sql.gz .

# 3. Restore to staging (NOT production)
gunzip < supabase_20260815_020000.sql.gz | psql $STAGING_DB_URL

# 4. Run sanity checks
psql $STAGING_DB_URL -c "SELECT COUNT(*) FROM signals;"
psql $STAGING_DB_URL -c "SELECT COUNT(*) FROM trigger_outcomes;"
psql $STAGING_DB_URL -c "SELECT MAX(created_at) FROM signals;"

# 5. Verify integrity
# - Check row counts match
# - Check latest dates
# - Check no NULL critical fields
# - Run sample queries

echo "Restore test passed" || echo "Restore test FAILED"
```

---

## 📋 PRÉ-F0.0-D Implementation Checklist

### Task 1: Add Critical Index (TODAY)

- [x] Identify missing index (trigger_outcomes.signal_id)
- [ ] Create migration file `018_add_trigger_outcomes_index.sql`
- [ ] Test locally (if possible)
- [ ] Apply to staging first
- [ ] Verify query performance improved

**SQL:**
```sql
-- supabase/migrations/018_add_trigger_outcomes_index.sql
BEGIN;
  CREATE INDEX CONCURRENTLY idx_trigger_outcomes_signal_id 
    ON trigger_outcomes(signal_id);
  ANALYZE trigger_outcomes;
COMMIT;
```

### Task 2: Backup Script (TODAY)

- [ ] Create `scripts/backup_database.sh`
- [ ] Test backup locally (if access)
- [ ] Verify S3 connectivity
- [ ] Schedule with cron-job.org (until Railway)

### Task 3: Restore Test (TODAY)

- [ ] Document restore procedure
- [ ] Run test restore from latest backup
- [ ] Verify data integrity
- [ ] Document results

### Task 4: Migrations Tooling (F0)

- [ ] Install Supabase CLI
- [ ] Test `supabase migration new`
- [ ] Document workflow in GIT-STRATEGY
- [ ] Setup pre-commit hook to validate SQL

---

## 🔐 Data Integrity

### Constraints to Validate

```sql
-- Check all migrations applied
SELECT * FROM pg_stat_user_tables;

-- Check indexes
SELECT * FROM pg_stat_user_indexes;

-- Check foreign keys
SELECT constraint_name FROM information_schema.key_column_usage
WHERE table_name = 'trigger_outcomes';

-- Check row counts
SELECT COUNT(*) as signal_count FROM signals;
SELECT COUNT(*) as outcome_count FROM trigger_outcomes;
SELECT COUNT(*) as sinal_count FROM signals_v2;
```

---

## 📝 Migration Workflow (Padrão F0+)

**Para cada mudança de schema:**

```bash
# 1. Create migration
supabase migration new add_new_column

# 2. Edit migration file (up + down sections)
vim supabase/migrations/<timestamp>_add_new_column.sql

# 3. Test on staging
supabase db push  # (with --linked to staging DB)

# 4. Commit
git add supabase/migrations/<timestamp>_add_new_column.sql
git commit -m "feat: add new column to signals table"

# 5. Deploy to production (via CI/CD or manual)
```

---

## ✅ Status PRÉ-F0.0-D

| Item | Status | By When |
|------|--------|---------|
| Index added (trigger_outcomes) | 🟡 Pending | TODAY |
| Backup script created | 🟡 Pending | TODAY |
| Restore test documented | 🟡 Pending | TODAY |
| Supabase CLI installed | 🟡 Pending | F0 |
| CI integration | 🟡 Pending | F0 |

---

**Status:** 📋 Documentação Completa  
**Próximo:** Implementar index + backup script + restore test

