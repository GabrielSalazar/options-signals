/**
 * Formatters compartilhados — pt-BR.
 * Hoisted no nível do módulo para evitar reconstrução de Intl.NumberFormat
 * a cada render (era um gargalo em componentes que renderizam charts).
 *
 * Assinatura aceita `number | string` para casar com a tipagem do recharts
 * Tooltip `formatter` prop (que pode passar non-number em alguns casos).
 */

const BRL_FMT = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const NUM_FMT = new Intl.NumberFormat('pt-BR');

export function fmtCcy(val: number | string | undefined): string {
    if (typeof val !== 'number' || !isFinite(val)) return val == null ? '—' : String(val);
    return BRL_FMT.format(val);
}

export function fmtNum(val: number | string | undefined): string {
    if (typeof val !== 'number' || !isFinite(val)) return val == null ? '—' : String(val);
    return NUM_FMT.format(Math.round(val));
}

export function fmtPct(val: number | string | undefined, decimals = 2): string {
    if (typeof val !== 'number' || !isFinite(val)) return val == null ? '—' : String(val);
    return `${val.toFixed(decimals)}%`;
}
