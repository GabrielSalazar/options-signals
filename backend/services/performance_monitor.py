"""Monitor de performance em tempo real — P&L, attribution, slippage."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np


@dataclass
class PerformanceMetrics:
    """Métricas de performance do portfólio."""
    total_pnl: float  # P&L total
    pnl_percent: float  # P&L em %
    daily_pnl: float  # P&L do dia
    daily_pnl_percent: float  # % do dia
    win_rate: float  # Taxa de trades vencedores
    profit_factor: float  # Lucro total / Perda total
    sharpe_ratio: float  # Índice de Sharpe
    sortino_ratio: float  # Índice de Sortino
    max_loss_trade: float  # Maior perda em um trade
    max_gain_trade: float  # Maior ganho em um trade
    avg_loss_trade: float  # Perda média
    avg_gain_trade: float  # Ganho médio


class PerformanceMonitor:
    """Monitor de performance e P&L attribution.

    Rastreia performance em tempo real, calcula Sharpe/Sortino, atribui P&L.
    """

    def __init__(self, starting_capital: float = 100000.0):
        """Inicializa monitor.

        Args:
            starting_capital: Capital inicial
        """
        self.starting_capital = starting_capital
        self.current_value = starting_capital
        self.trades: list[dict] = []  # Histórico de trades
        self.daily_pnls: list[float] = []  # P&L diários

    def record_trade(
        self,
        entry_price: float,
        exit_price: float,
        quantity: float,
        entry_time: datetime,
        exit_time: datetime,
        commission: float = 0.0
    ) -> dict:
        """Registra um trade concluído.

        Args:
            entry_price: Preço de entrada
            exit_price: Preço de saída
            quantity: Quantidade
            entry_time: Hora de entrada
            exit_time: Hora de saída
            commission: Comissão

        Returns:
            Dict com detalhes do trade
        """
        pnl = (exit_price - entry_price) * quantity - commission
        pnl_percent = pnl / (entry_price * quantity) if entry_price > 0 else 0
        duration_minutes = (exit_time - entry_time).total_seconds() / 60

        trade = {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "commission": commission,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "duration_minutes": duration_minutes,
            "is_win": pnl > 0
        }

        self.trades.append(trade)
        self.current_value += pnl
        return trade

    def calculate_win_rate(self) -> float:
        """Calcula taxa de trades vencedores.

        Returns:
            Win rate (0.0-1.0)
        """
        if not self.trades:
            return 0.0

        wins = sum(1 for t in self.trades if t["is_win"])
        return wins / len(self.trades)

    def calculate_profit_factor(self) -> float:
        """Calcula profit factor (total ganhos / total perdas).

        Returns:
            Profit factor
        """
        if not self.trades:
            return 0.0

        gains = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        losses = abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0))

        if losses == 0:
            return float('inf') if gains > 0 else 0.0
        return gains / losses

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calcula Índice de Sharpe.

        Args:
            risk_free_rate: Taxa livre de risco anual

        Returns:
            Índice de Sharpe
        """
        if len(self.daily_pnls) < 2:
            return 0.0

        daily_pnls = np.array(self.daily_pnls)
        mean_return = np.mean(daily_pnls)
        std_dev = np.std(daily_pnls)

        if std_dev == 0:
            return 0.0

        # Annualize (252 trading days)
        annual_return = mean_return * 252
        annual_vol = std_dev * np.sqrt(252)

        sharpe = (annual_return - risk_free_rate) / annual_vol if annual_vol > 0 else 0.0
        return sharpe

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Calcula Índice de Sortino (só penaliza downside).

        Args:
            risk_free_rate: Taxa livre de risco anual

        Returns:
            Índice de Sortino
        """
        if len(self.daily_pnls) < 2:
            return 0.0

        daily_pnls = np.array(self.daily_pnls)
        mean_return = np.mean(daily_pnls)

        # Downside deviation (só dias negativos)
        downside_pnls = daily_pnls[daily_pnls < 0]
        downside_std = np.std(downside_pnls) if len(downside_pnls) > 0 else 0.0

        if downside_std == 0:
            return 0.0

        # Annualize
        annual_return = mean_return * 252
        annual_downside_vol = downside_std * np.sqrt(252)

        sortino = (annual_return - risk_free_rate) / annual_downside_vol if annual_downside_vol > 0 else 0.0
        return sortino

    def compute_performance_metrics(self) -> PerformanceMetrics:
        """Computa métricas de performance.

        Returns:
            PerformanceMetrics com análise completa
        """
        total_pnl = self.current_value - self.starting_capital
        total_pnl_percent = total_pnl / self.starting_capital if self.starting_capital > 0 else 0

        daily_pnl = sum(self.daily_pnls[-1:]) if self.daily_pnls else 0.0
        daily_pnl_percent = daily_pnl / self.starting_capital if self.starting_capital > 0 else 0

        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()
        sharpe = self.calculate_sharpe_ratio()
        sortino = self.calculate_sortino_ratio()

        # Maiores gains/losses
        max_loss = min((t["pnl"] for t in self.trades), default=0)
        max_gain = max((t["pnl"] for t in self.trades), default=0)
        avg_loss = np.mean([t["pnl"] for t in self.trades if t["pnl"] < 0]) if any(t["pnl"] < 0 for t in self.trades) else 0
        avg_gain = np.mean([t["pnl"] for t in self.trades if t["pnl"] > 0]) if any(t["pnl"] > 0 for t in self.trades) else 0

        return PerformanceMetrics(
            total_pnl=total_pnl,
            pnl_percent=total_pnl_percent,
            daily_pnl=daily_pnl,
            daily_pnl_percent=daily_pnl_percent,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_loss_trade=max_loss,
            max_gain_trade=max_gain,
            avg_loss_trade=avg_loss,
            avg_gain_trade=avg_gain
        )
