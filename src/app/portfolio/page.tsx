import PortfolioDashboard from '@/components/PortfolioDashboard';
import { Briefcase } from 'lucide-react';

export default function PortfolioPage() {
  return (
    <div className="main-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="label mb-2 flex items-center gap-2">
            <Briefcase className="w-4 h-4" />
            Risk Management
          </div>
          <h1 className="font-serif">Portfolio Risk Dashboard</h1>
          <p className="mt-2 text-dw-ink-light text-base max-w-2xl">
            Visão consolidada e agregada de risco (Gregas) em múltiplas posições e ativos.
            Faça simulações, balanceie o seu Delta e entenda a exposição do seu book.
          </p>
        </div>
      </div>

      <PortfolioDashboard />
    </div>
  );
}
