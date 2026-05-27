import { supabase } from './supabase';

export interface DatabaseSignal {
  id?: string;
  user_id?: string;
  ticker: string;
  option_symbol: string;
  strategy: string;
  signal_type: string;
  spot_price: number;
  strike?: number;
  price?: number;
  entry_price?: number;
  confidence_score?: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNLIMITED';
  reason: string;
  timestamp?: string;
  recommendation?: string;
  created_at?: string;
  updated_at?: string;
}

export async function getSignalsByTicker(ticker: string, limit: number = 50) {
  try {
    const { data, error } = await supabase
      .from('signals')
      .select('*')
      .eq('ticker', ticker.toUpperCase())
      .order('timestamp', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function getAllSignals(limit: number = 50, offset: number = 0) {
  try {
    const { data, error, count } = await supabase
      .from('signals')
      .select('*', { count: 'exact' })
      .order('timestamp', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;
    return { data, count, error: null };
  } catch (error) {
    return {
      data: null,
      count: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function saveSignal(signal: DatabaseSignal) {
  try {
    const { data, error } = await supabase
      .from('signals')
      .insert([signal])
      .select();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function updateSignal(id: string, updates: Partial<DatabaseSignal>) {
  try {
    const { data, error } = await supabase
      .from('signals')
      .update(updates)
      .eq('id', id)
      .select();

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function deleteSignal(id: string) {
  try {
    const { error } = await supabase.from('signals').delete().eq('id', id);

    if (error) throw error;
    return { error: null };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function getSignalsByStrategy(strategy: string, limit: number = 50) {
  try {
    const { data, error } = await supabase
      .from('signals')
      .select('*')
      .eq('strategy', strategy)
      .order('timestamp', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

export async function getUserSignals(userId: string, limit: number = 50) {
  try {
    const { data, error } = await supabase
      .from('signals')
      .select('*')
      .eq('user_id', userId)
      .order('timestamp', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return { data, error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
