import { getSupabase } from './supabase';
import type { User, Session } from '@supabase/supabase-js';

export interface AuthResponse {
  user: User | null;
  session: Session | null;
  error: string | null;
}

export async function signUpWithEmail(
  email: string,
  password: string,
  fullName?: string
): Promise<AuthResponse> {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });

    if (error) return { user: null, session: null, error: error.message };
    return { user: data.user, session: data.session, error: null };
  } catch (error) {
    return { user: null, session: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function signInWithEmail(
  email: string,
  password: string
): Promise<AuthResponse> {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) return { user: null, session: null, error: error.message };
    return { user: data.user, session: data.session, error: null };
  } catch (error) {
    return { user: null, session: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function signOut() {
  try {
    const supabase = getSupabase();
    const { error } = await supabase.auth.signOut();
    return { error: error?.message || null };
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function getCurrentUser() {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase.auth.getUser();
    return { user: data.user, error: error?.message || null };
  } catch (error) {
    return { user: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}

export async function updateUserPassword(newPassword: string) {
  try {
    const supabase = getSupabase();
    const { data, error } = await supabase.auth.updateUser({ password: newPassword });

    if (error) return { user: null, error: error.message };
    return { user: data.user, error: null };
  } catch (error) {
    return { user: null, error: error instanceof Error ? error.message : 'Unknown error' };
  }
}
