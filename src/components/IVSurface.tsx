'use client';

import { useEffect, useRef } from 'react';

export interface IVDataPoint {
  strike: number;
  expiry: string;
  iv: number;
  tipo: 'CALL' | 'PUT';
}

export default function IVSurface({ data }: { data: IVDataPoint[] }) {
  const divRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = divRef.current;
    if (!el || !data.length) return;

    let cancelled = false;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    import('plotly.js-dist-min').then((mod: any) => {
      if (cancelled || !el) return;
      const Plotly = mod.default ?? mod;

      const calls = data.filter((d) => d.tipo === 'CALL');
      const puts = data.filter((d) => d.tipo === 'PUT');

      const traces = [
        {
          type: 'scatter3d',
          mode: 'markers',
          name: 'CALL',
          x: calls.map((d) => d.strike),
          y: calls.map((d) => d.expiry),
          z: calls.map((d) => d.iv),
          marker: { size: 5, color: '#3B82F6', opacity: 0.85 },
        },
        {
          type: 'scatter3d',
          mode: 'markers',
          name: 'PUT',
          x: puts.map((d) => d.strike),
          y: puts.map((d) => d.expiry),
          z: puts.map((d) => d.iv),
          marker: { size: 5, color: '#EF4444', opacity: 0.85 },
        },
      ];

      const layout = {
        paper_bgcolor: 'transparent',
        legend: { x: 0.75, y: 0.95, bgcolor: 'rgba(255,255,255,0.8)', bordercolor: '#e5e7eb', borderwidth: 1 },
        scene: {
          xaxis: { title: 'Strike (R$)', gridcolor: '#e5e7eb', showbackground: false },
          yaxis: { title: 'Vencimento', gridcolor: '#e5e7eb', showbackground: false },
          zaxis: { title: 'IV Hist %', gridcolor: '#e5e7eb', showbackground: false },
          bgcolor: 'rgba(249,250,251,0.4)',
        },
        margin: { t: 10, b: 10, l: 10, r: 10 },
      };

      Plotly.newPlot(el, traces, layout, { responsive: true, displayModeBar: false });
    });

    return () => {
      cancelled = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      import('plotly.js-dist-min').then((mod: any) => {
        const Plotly = mod.default ?? mod;
        if (el) Plotly.purge(el);
      });
    };
  }, [data]);

  return (
    <div ref={divRef} style={{ height: 420, width: '100%' }} />
  );
}
