import { describe, it, expect } from 'vitest';
import { SECTORS, ALL_B3_TICKERS } from '../tickers';

describe('tickers (fonte única)', () => {
    it('ALL_B3_TICKERS deriva de SECTORS sem o pseudo-setor "Todos"', () => {
        const esperado = Object.entries(SECTORS)
            .filter(([s]) => s !== 'Todos')
            .flatMap(([, a]) => a.map((x) => x.ticker));
        expect(ALL_B3_TICKERS).toEqual(esperado);
    });

    it('não tem tickers duplicados', () => {
        expect(new Set(ALL_B3_TICKERS).size).toBe(ALL_B3_TICKERS.length);
    });

    it('não contém tickers deslistados/renomeados', () => {
        const deslistados = ['RRRP3', 'SOMA3', 'SULA11', 'AMER3', 'VIIA3', 'OIBR3'];
        for (const t of deslistados) {
            expect(ALL_B3_TICKERS).not.toContain(t);
        }
    });

    it('contém os renomeados corretos', () => {
        for (const t of ['BRAV3', 'AZZA3', 'BHIA3']) {
            expect(ALL_B3_TICKERS).toContain(t);
        }
    });
});
