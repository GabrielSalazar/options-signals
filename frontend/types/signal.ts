/**
 * Signal types and validators
 *
 * GENERATED: Do not edit manually. Run: python scripts/generate_ts_types.py
 * Last updated: "2026-08-15T21:24:24.742873"
 */

import { z } from 'zod';

// Signal type enum (matches Python SignalType)
export enum SignalType {
  CALL_ALTA = 'CALL_ALTA',
  CALL_REVERSAO = 'CALL_REVERSAO',
  CALL_SIDEWAYS = 'CALL_SIDEWAYS',
  PUT_ALTA = 'PUT_ALTA',
  PUT_REVERSAO = 'PUT_REVERSAO',
  PUT_SIDEWAYS = 'PUT_SIDEWAYS',
}

// Zod validators (matching Pydantic validators)
export const SignalSchema = z.object({
  ticker: z.string()
    .min(4, "Ticker must be at least 4 characters")
    .max(10, "Ticker must be at most 10 characters")
    .transform(v => v.toUpperCase()),
  tipo_sinal: z.nativeEnum(SignalType),
  alvo1: z.number()
    .positive("alvo1 must be positive"),
  alvo2: z.number()
    .positive("alvo2 must be positive")
    .optional(),
  alvo3: z.number()
    .positive("alvo3 must be positive")
    .optional(),
  stop_loss: z.number()
    .positive("stop_loss must be positive"),
  score_ponderado: z.number()
    .int("score_ponderado must be an integer")
    .min(0, "score_ponderado must be >= 0")
    .max(100, "score_ponderado must be <= 100"),
  data_sinal: z.string().datetime("data_sinal must be a valid datetime"),
  confianca: z.number()
    .min(0.0, "confianca must be >= 0.0")
    .max(1.0, "confianca must be <= 1.0")
    .optional(),
}).strict()
  .refine(
    (data) => data.alvo1 !== data.stop_loss,
    {
      message: "alvo1 (target price) cannot equal stop_loss — must differ",
      path: ["alvo1"],
    }
  )
  .refine(
    (data) => {
      // For CALL signals: alvo1 < alvo2 < alvo3
      // For PUT signals: alvo1 > alvo2 > alvo3
      const isCall = data.tipo_sinal.includes("CALL");

      if (data.alvo2 === undefined) return true;

      if (isCall) {
        return data.alvo1 < data.alvo2;
      } else {
        return data.alvo1 > data.alvo2;
      }
    },
    {
      message: "alvo2 ordering must match signal type (CALL ascending, PUT descending)",
      path: ["alvo2"],
    }
  )
  .refine(
    (data) => {
      const isCall = data.tipo_sinal.includes("CALL");
      const compareAgainst = data.alvo2 ?? data.alvo1;

      if (data.alvo3 === undefined) return true;

      if (isCall) {
        return data.alvo3 > compareAgainst;
      } else {
        return data.alvo3 < compareAgainst;
      }
    },
    {
      message: "alvo3 ordering must match signal type (CALL ascending, PUT descending)",
      path: ["alvo3"],
    }
  );

// TypeScript type (inferred from zod schema)
export type Signal = z.infer<typeof SignalSchema>;

// Helper to validate signal data
export function validateSignal(data: unknown): Signal {
  return SignalSchema.parse(data);
}

// Helper to validate signal data (safe version, returns errors)
export function tryValidateSignal(
  data: unknown
): { success: true; data: Signal } | { success: false; errors: string[] } {
  const result = SignalSchema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return {
    success: false,
    errors: result.error.errors.map((e) => `${e.path.join(".")}: ${e.message}`),
  };
}