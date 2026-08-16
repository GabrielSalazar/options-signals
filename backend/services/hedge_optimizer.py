"""Otimizador de hedge — rebalanceamento delta-neutro automático."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class HedgeRecommendation:
    """Recomendação de hedge."""
    target_delta: float  # Delta alvo (geralmente 0 para neutro)
    current_delta: float  # Delta atual
    delta_gap: float  # Diferença a hedge
    hedge_instrument: str  # Instrumento recomendado (call/put/stock)
    hedge_quantity: float  # Quantidade a comprar/vender
    estimated_cost: float  # Custo estimado do hedge
    rebalance_needed: bool  # Se rebalanceamento necessário


class HedgeOptimizer:
    """Otimizador de hedge para manter neutralidade.

    Recomenda rebalanceamentos para manter delta neutro ou dentro de limites.
    Suporta hedging via calls, puts, e stock direto.
    """

    def __init__(
        self,
        target_delta: float = 0.0,
        delta_threshold: float = 0.1,
        rebalance_cost_threshold: float = 100.0
    ):
        """Inicializa otimizador.

        Args:
            target_delta: Delta alvo (default 0 = neutro)
            delta_threshold: Tolerância de delta (rebalance se > isso)
            rebalance_cost_threshold: Custo mínimo para rebalancear
        """
        self.target_delta = target_delta
        self.delta_threshold = delta_threshold
        self.rebalance_cost_threshold = rebalance_cost_threshold
        self.rebalance_history: list[dict] = []

    def recommend_hedge(
        self,
        current_delta: float,
        spot_price: float,
        call_delta: float = 0.5,
        put_delta: float = -0.5,
        stock_delta: float = 1.0
    ) -> HedgeRecommendation:
        """Recomenda hedge para neutralizar delta.

        Args:
            current_delta: Delta atual do portfólio
            spot_price: Preço atual do ativo
            call_delta: Delta de 1 call ATM
            put_delta: Delta de 1 put ATM
            stock_delta: Delta de 1 share (sempre 1.0)

        Returns:
            HedgeRecommendation com detalhes
        """
        delta_gap = current_delta - self.target_delta
        rebalance_needed = abs(delta_gap) > self.delta_threshold

        # Escolhe instrumento de hedge (menos custoso)
        # Para delta positivo: vender calls ou comprar puts
        # Para delta negativo: comprar calls ou vender puts

        if delta_gap > 0:
            # Portfólio long demais, precisa vender delta
            # Opção 1: Vender calls (delta negativo)
            hedge_instrument = "sell_calls"
            hedge_quantity = abs(delta_gap) / abs(call_delta) if call_delta != 0 else 0
            estimated_cost = hedge_quantity * spot_price * 0.01  # 1% de custo
        else:
            # Portfólio short demais, precisa comprar delta
            # Opção 1: Comprar calls (delta positivo)
            hedge_instrument = "buy_calls"
            hedge_quantity = abs(delta_gap) / call_delta if call_delta != 0 else 0
            estimated_cost = hedge_quantity * spot_price * 0.01

        # Verifica se custa demais para rebalancear
        if estimated_cost < self.rebalance_cost_threshold:
            rebalance_needed = False

        return HedgeRecommendation(
            target_delta=self.target_delta,
            current_delta=current_delta,
            delta_gap=delta_gap,
            hedge_instrument=hedge_instrument,
            hedge_quantity=hedge_quantity,
            estimated_cost=estimated_cost,
            rebalance_needed=rebalance_needed
        )

    def record_rebalance(
        self,
        instrument: str,
        quantity: float,
        price: float,
        reason: str
    ) -> dict:
        """Registra um rebalanceamento realizado.

        Args:
            instrument: Instrumento (call/put/stock)
            quantity: Quantidade
            price: Preço
            reason: Motivo do rebalance

        Returns:
            Dict com detalhes do rebalance
        """
        cost = quantity * price
        rebalance = {
            "instrument": instrument,
            "quantity": quantity,
            "price": price,
            "cost": cost,
            "reason": reason
        }
        self.rebalance_history.append(rebalance)
        return rebalance

    def get_rebalance_frequency(self, window_days: int = 30) -> float:
        """Calcula frequência de rebalanceamentos.

        Args:
            window_days: Janela de tempo (default 30 dias)

        Returns:
            Rebalances por dia
        """
        if not self.rebalance_history:
            return 0.0

        return len(self.rebalance_history) / max(window_days, 1)

    def get_total_hedge_cost(self) -> float:
        """Calcula custo total de hedging.

        Returns:
            Custo acumulado em rebalances
        """
        return sum(r["cost"] for r in self.rebalance_history)

    def analyze_hedge_efficiency(self) -> dict:
        """Analisa eficiência do hedging (rebalances vs effectiveness).

        Returns:
            Dict com análise
        """
        if not self.rebalance_history:
            return {
                "total_rebalances": 0,
                "total_cost": 0.0,
                "average_cost": 0.0,
                "efficiency_score": 0.0
            }

        total_rebalances = len(self.rebalance_history)
        total_cost = self.get_total_hedge_cost()
        average_cost = total_cost / total_rebalances if total_rebalances > 0 else 0

        # Efficiency: quanto menor custo por rebalance, melhor
        # Score: 1.0 - (avg_cost / threshold)
        efficiency_score = max(
            0.0,
            1.0 - (average_cost / self.rebalance_cost_threshold)
        )

        return {
            "total_rebalances": total_rebalances,
            "total_cost": total_cost,
            "average_cost": average_cost,
            "efficiency_score": efficiency_score
        }
