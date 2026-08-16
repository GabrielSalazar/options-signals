"""Option structure builder service with Black-Scholes pricing."""
import logging

# Importa componentes de precificação de opções baseado em Black-Scholes
from backend.domain.option_pricing import OptionPricer, OptionInput, OptionType

logger = logging.getLogger("option_builder")


class OptionBuilder:
    """Build option structures with accurate Black-Scholes pricing and Greeks.

    Uses OptionPricer for generic (ticker-agnostic) option valuation.
    Supports any underlying asset without changes.
    """

    def __init__(self, risk_free_rate: float = 0.10):
        """Initialize builder with risk-free rate.

        Args:
            risk_free_rate: Annual risk-free rate (default 10% - Selic proxy)
        """
        self.pricer = OptionPricer()
        self.risk_free_rate = risk_free_rate

    def build(
        self,
        ticker_base: str,
        preco: float,
        tipo_sinal: str,
        direcao_label: str,
        dte: int,
        strike_ref: float,
        dist_otm: float,
        iv_impl: float,
        hv_20d: float,
        dividend_yield: float = 0.0,
        **kwargs
    ) -> dict:
        """Build option structure with accurate Black-Scholes pricing.

        Args:
            ticker_base: Stock ticker (e.g., 'PETR4')
            preco: Current stock price
            tipo_sinal: Signal type ('CALL_ALTA', 'PUT_BAIXA', etc.)
            direcao_label: Direction label (unused, for compatibility)
            dte: Days to expiration
            strike_ref: Strike price
            dist_otm: Distance OTM (percentage, for info only)
            iv_impl: Implied volatility from market
            hv_20d: Historical volatility 20 days
            dividend_yield: Annual dividend yield (default 0%)

        Returns:
            dict with accurate pricing, Greeks, and targets
        """
        # Identifica o tipo de opção a partir do sinal
        is_call = "CALL" in tipo_sinal
        option_type = OptionType.CALL if is_call else OptionType.PUT

        # Converte dias até expiração para fração de ano (365 dias base)
        time_to_expiry = dte / 365.0

        # Usa volatilidade implícita se disponível; caso contrário, histórica
        volatility = iv_impl if iv_impl > 0 else hv_20d

        # Cria entrada genérica para precificação (funciona com qualquer ativo)
        option_input = OptionInput(
            spot_price=preco,
            strike_price=strike_ref,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
            risk_free_rate=self.risk_free_rate,
            dividend_yield=dividend_yield,
            option_type=option_type,
        )

        # Calcula preço e gregas usando Black-Scholes
        pricing = self.pricer.price(option_input)

        # Estima volatilidade em pontos de preço usando volatilidade histórica
        atr_approx = preco * hv_20d

        # Define níveis de alvos e stop baseado na direção (CALL sobe, PUT desce)
        if is_call:
            alvo1 = preco + atr_approx * 0.5
            alvo2 = preco + atr_approx * 1.0
            alvo_final = preco + atr_approx * 1.5
            stop = preco - atr_approx * 0.5
        else:
            alvo1 = preco - atr_approx * 0.5
            alvo2 = preco - atr_approx * 1.0
            alvo_final = preco - atr_approx * 1.5
            stop = preco + atr_approx * 0.5

        # Calcula razão risco/recompensa: (alvo - entrada) / (entrada - stop)
        rr_alvo1 = (alvo1 - preco) / (preco - stop) if (preco - stop) != 0 else 0
        rr_alvo2 = (alvo2 - preco) / (preco - stop) if (preco - stop) != 0 else 0
        rr_final = (alvo_final - preco) / (preco - stop) if (preco - stop) != 0 else 0

        # Retorna estrutura completa com precificação Black-Scholes + alvos e ratios
        return {
            # Identificadores
            "ticker_opcao": f"{ticker_base}{dte}",
            "strike_ref": strike_ref,
            "dist_otm": dist_otm,
            "dte": dte,
            "iv_impl": iv_impl,
            "hv_20d": hv_20d,
            # Preço e Gregas (Black-Scholes)
            "premium": pricing.premium,
            "delta": pricing.delta,
            "gamma": pricing.gamma,
            "vega": pricing.vega,
            "theta": pricing.theta,
            "rho": pricing.rho,
            "intrinsic_value": pricing.intrinsic_value,
            "time_value": pricing.time_value,
            "moneyness": pricing.moneyness,
            # Níveis de entrada e saída
            "entrada_min": preco * 0.98,
            "entrada_max": preco * 1.02,
            "alvo1": alvo1,
            "alvo2": alvo2,
            "alvo_final": alvo_final,
            "stop": stop,
            "book_until": "16:30",
            # Razões de risco/recompensa
            "rr_alvo1": rr_alvo1,
            "rr_alvo2": rr_alvo2,
            "rr_final": rr_final,
        }
