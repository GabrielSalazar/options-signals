import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Smoke test que valida o pipeline jsdom + React Testing Library + jest-dom.
describe('RTL setup', () => {
  it('renders a React element into jsdom', () => {
    render(<button>Comprar</button>);
    expect(screen.getByRole('button', { name: 'Comprar' })).toBeInTheDocument();
  });
});
