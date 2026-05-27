'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Error Boundary caught:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-6 bg-red-50 rounded-xl border border-red-100 m-4">
      <h2 className="text-lg font-bold text-red-900 mb-2">Algo deu errado!</h2>
      <p className="text-sm text-red-700 mb-4 text-center max-w-md">
        Não foi possível renderizar este componente. Isso pode ser uma falha temporária ou um problema de conexão.
      </p>
      <div className="bg-white text-red-800 text-xs p-3 rounded border border-red-200 mb-6 font-mono max-w-full overflow-x-auto">
        {error.message}
      </div>
      <button
        onClick={() => reset()}
        className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 transition-colors"
      >
        Tentar novamente
      </button>
    </div>
  );
}
