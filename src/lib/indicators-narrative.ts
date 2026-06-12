import type { IndicatorsPayload, VolRead } from '@/lib/types/indicators';

export function momentoLabel(p: IndicatorsPayload): string {
  if (p.rsi14 < 30) return 'sobrevendido';
  if (p.rsi14 > 70) return 'sobrecomprado';
  return 'neutro';
}

export function tendenciaLabel(p: IndicatorsPayload): string {
  const abaixoCurtas = p.preco_atual < p.ma20 && p.preco_atual < p.ma50;
  const acimaCurtas = p.preco_atual > p.ma20 && p.preco_atual > p.ma50;
  const forte = p.adx >= 25;
  if (abaixoCurtas) return forte ? 'baixa forte' : 'baixa';
  if (acimaCurtas) return forte ? 'alta forte' : 'alta';
  return 'lateral';
}

export function tecnicaLabel(p: IndicatorsPayload): string {
  const tend = tendenciaLabel(p);
  const mom = momentoLabel(p);
  if (tend === 'baixa forte' && mom === 'sobrevendido') return 'faca caindo';
  if (tend === 'alta forte' && mom === 'sobrecomprado') return 'esticado';
  if (tend.startsWith('alta')) return 'compradora';
  if (tend.startsWith('baixa')) return 'vendedora';
  return 'indefinida';
}

export function volReadLabel(v: VolRead): string {
  switch (v) {
    case 'premio_gordo': return 'IV elevada — favorece vender prêmio';
    case 'premio_barato': return 'IV baixa — favorece comprar prêmio';
    case 'neutro': return 'IV em linha com a histórica';
    default: return 'IV indisponível — leitura baseada em HV';
  }
}

export function resumo(p: IndicatorsPayload): string {
  const mom = momentoLabel(p);
  const tend = tendenciaLabel(p);
  const vol = volReadLabel(p.vol_read);
  const reversao = (mom === 'sobrevendido' && tend.includes('baixa'))
    || (mom === 'sobrecomprado' && tend.includes('alta')) ? ' — sinal de reversão prematuro' : '';
  return `${cap(mom)} em tendência de ${tend}${reversao}. ${vol}.`;
}

function cap(s: string): string { return s.charAt(0).toUpperCase() + s.slice(1); }
