import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Garante DOM limpo entre testes de componente (RTL).
afterEach(() => {
  cleanup();
});
