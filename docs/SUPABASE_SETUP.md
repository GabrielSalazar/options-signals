# Supabase Setup Guide

## 1. Criar Projeto Supabase

1. Acesse [supabase.com](https://supabase.com)
2. Faça login ou crie uma conta
3. Clique em "New Project"
4. Preencha:
   - **Name**: `options-signals-v2`
   - **Database Password**: (salvar em lugar seguro)
   - **Region**: Selecione a mais próxima
5. Aguarde ~3-5 minutos para provisionar

## 2. Copiar Credenciais

1. Vá para **Settings** → **API**
2. Copie:
   - `Project URL` → `NEXT_PUBLIC_SUPABASE_URL`
   - `anon public` key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY` (server-side only)

## 3. Criar Tabelas

### Tabela: `signals`

```sql
CREATE TABLE signals (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ticker VARCHAR(10) NOT NULL,
  option_symbol VARCHAR(50) NOT NULL,
  strategy VARCHAR(100) NOT NULL,
  signal_type VARCHAR(20) NOT NULL,
  spot_price DECIMAL(10, 2) NOT NULL,
  strike DECIMAL(10, 2),
  price DECIMAL(10, 2),
  entry_price DECIMAL(10, 2),
  confidence_score DECIMAL(3, 2),
  risk_level VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
  reason TEXT,
  recommendation TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  timestamp TIMESTAMP WITH TIME ZONE
);

-- Index for performance
CREATE INDEX idx_signals_ticker ON signals(ticker);
CREATE INDEX idx_signals_strategy ON signals(strategy);
CREATE INDEX idx_signals_user_id ON signals(user_id);
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
```

### Tabela: `strategies`

```sql
CREATE TABLE strategies (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  parameters JSONB,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_strategies_user_id ON strategies(user_id);
```

### Tabela: `backtest_results`

```sql
CREATE TABLE backtest_results (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  strategy_name VARCHAR(100) NOT NULL,
  ticker VARCHAR(10) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  initial_capital DECIMAL(12, 2) NOT NULL,
  final_capital DECIMAL(12, 2) NOT NULL,
  total_return DECIMAL(10, 2),
  win_rate DECIMAL(5, 2),
  max_drawdown DECIMAL(5, 2),
  sharpe_ratio DECIMAL(5, 2),
  trades_count INT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_backtest_user_id ON backtest_results(user_id);
```

## 4. Configurar Variáveis de Ambiente

Crie ou atualize `.env.local`:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 5. Habilitar RLS (Row Level Security)

1. Vá para **SQL Editor** no Supabase Dashboard
2. Execute:

```sql
-- Enable RLS
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE backtest_results ENABLE ROW LEVEL SECURITY;

-- Policies para signals
CREATE POLICY "Users can view their own signals"
  ON signals FOR SELECT
  USING (auth.uid() = user_id OR user_id IS NULL);

CREATE POLICY "Users can insert their own signals"
  ON signals FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own signals"
  ON signals FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own signals"
  ON signals FOR DELETE
  USING (auth.uid() = user_id);

-- Similar policies para strategies e backtest_results
```

## 6. Testar Conexão

```bash
npm run dev
# Acesse http://localhost:3000
# Tente fazer login ou registrar
```

## Próximos Passos

- [ ] Atualizar componentes de Login/Register para usar Supabase Auth
- [ ] Sincronizar sinais do backend Python com Supabase
- [ ] Implementar histórico de backtests
- [ ] Adicionar dashboard de analytics com dados do Supabase
