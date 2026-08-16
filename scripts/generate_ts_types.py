#!/usr/bin/env python3
"""Generate TypeScript types and validators from Python Pydantic models.

This script generates:
1. TypeScript type definitions (signal.ts)
2. zod validators matching Pydantic validators
3. Keeps frontend and backend type contracts in sync

Usage:
    python scripts/generate_ts_types.py

Output:
    - frontend/types/signal.ts (TypeScript types + zod validators)
"""
import json
import logging
import sys
from pathlib import Path

import jinja2

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.models.signal import SignalType

logger = logging.getLogger("ts_generator")

# Template for TypeScript types and zod validators
TS_TEMPLATE = '''/**
 * Signal types and validators
 *
 * GENERATED: Do not edit manually. Run: python scripts/generate_ts_types.py
 * Last updated: {{ generated_at }}
 */

import { z } from 'zod';

// Signal type enum (matches Python SignalType)
export enum SignalType {
{%- for tipo in signal_types %}
  {{ tipo.name }} = '{{ tipo.value }}',
{%- endfor %}
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
'''


def generate_ts_types(output_path: str = "frontend/types/signal.ts"):
    """Generate TypeScript types from Signal model.

    Args:
        output_path: Output file path (relative to project root)
    """
    try:
        # Get project root
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        output_file = project_root / output_path

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Get Signal type enum values
        signal_types = [
            {"name": member.name, "value": member.value}
            for member in SignalType
        ]

        # Render template
        template = jinja2.Template(TS_TEMPLATE)
        rendered = template.render(
            signal_types=signal_types,
            generated_at=json.dumps(__import__("datetime").datetime.now().isoformat()),
        )

        # Write output
        with open(output_file, "w") as f:
            f.write(rendered)

        logger.info(f"✅ Generated TypeScript types: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to generate TypeScript types: {e}")
        return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    success = generate_ts_types()
    sys.exit(0 if success else 1)
