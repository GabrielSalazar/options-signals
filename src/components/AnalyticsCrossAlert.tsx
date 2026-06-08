import type { AssetVerdict, OptionVerdict } from '@/lib/types/analytics';

interface Props {
  assetVerdict: AssetVerdict | null;
  optionVerdict: OptionVerdict | null;
}

export function AnalyticsCrossAlert({ assetVerdict, optionVerdict }: Props) {
  if (assetVerdict !== 'barato' || optionVerdict !== 'barata') return null;

  return (
    <div className="flex items-start gap-3 rounded-xl border border-emerald-700 bg-emerald-900/30 px-4 py-3">
      <span className="text-emerald-400 text-lg leading-none mt-0.5">✦</span>
      <div>
        <p className="text-sm font-semibold text-emerald-300">Ponto de entrada identificado</p>
        <p className="text-xs text-emerald-400/80 mt-0.5">
          Ativo subavaliado com IV baixa — custo de compra de call reduzido em relação ao prêmio histórico.
        </p>
      </div>
    </div>
  );
}
