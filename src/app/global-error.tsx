'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service if available
    console.error('Global Error Boundary caught:', error);
  }, [error]);

  return (
    <html lang="pt-BR">
      <body className="antialiased min-h-screen flex flex-col items-center justify-center p-4">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-lg w-full text-center shadow-lg">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Erro Crítico do Sistema</h2>
          <p className="text-sm text-gray-600 mb-6">
            Ocorreu um erro inesperado no sistema. A equipe técnica foi notificada.
          </p>
          <div className="bg-red-50 text-red-800 text-xs text-left p-4 rounded mb-6 font-mono overflow-auto max-h-32">
            {error.message || 'Erro interno desconhecido'}
          </div>
          <button
            onClick={() => reset()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </body>
    </html>
  );
}
