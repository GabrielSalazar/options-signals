"""
Golden Master Test — Contrato de Não-Regressão do Motor de Sinais.

Este teste congela a saída do motor para as 12 fixtures determinísticas.
Qualquer mudança no motor que altere a emissão de sinais fará este teste falhar.

É a rede de proteção que valida que nenhuma refatoração introduz regressão.
"""
import json
import pytest
from pathlib import Path
from typing import Any, Dict

from backend.services.core_engine import analisar_ativo
from tests.fixtures.ohlcv_fixtures import get_fixture, list_fixtures


class GoldenMasterMotor:
    """Gerencia snapshots do golden master."""

    GOLDEN_DIR = Path(__file__).parent / "golden" / "motor"

    @classmethod
    def setup_class(cls):
        """Criar diretório se não existir."""
        cls.GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_golden_path(cls, fixture_name: str) -> Path:
        """Caminho do snapshot golden."""
        return cls.GOLDEN_DIR / f"{fixture_name}.json"

    @classmethod
    def save_golden(cls, fixture_name: str, signal_dict: Dict[str, Any]):
        """Salvar snapshot golden (apenas em modo --golden-generate)."""
        path = cls.get_golden_path(fixture_name)
        with open(path, 'w') as f:
            json.dump(signal_dict, f, indent=2, default=str)
        print(f"✅ Golden master salvo: {path}")

    @classmethod
    def load_golden(cls, fixture_name: str) -> Dict[str, Any]:
        """Carregar snapshot golden congelado."""
        path = cls.get_golden_path(fixture_name)
        if not path.exists():
            raise FileNotFoundError(
                f"Golden master não encontrado: {path}\n"
                "Execute: pytest --golden-generate para criar"
            )
        with open(path) as f:
            return json.load(f)

    @staticmethod
    def normalize_value(value: Any, tolerance: float = 1e-9) -> Any:
        """
        Normalizar valores para comparação.

        Floats são arredondados com tolerância; NaN é normalizado;
        outros tipos mantêm valor.
        """
        if isinstance(value, float):
            if abs(value) < tolerance:
                return 0.0
            return round(value, 9)
        elif value is None:
            return None
        return value

    @staticmethod
    def compare_signals(
        actual: Dict[str, Any],
        expected: Dict[str, Any],
        tolerance: float = 1e-9
    ) -> tuple[bool, str]:
        """
        Comparar dois sinais com tolerância numérica.

        Returns:
            (matches: bool, message: str)
        """
        # Chaves
        if set(actual.keys()) != set(expected.keys()):
            missing_in_actual = set(expected.keys()) - set(actual.keys())
            extra_in_actual = set(actual.keys()) - set(expected.keys())
            msg = "Conjunto de chaves divergiu:\n"
            if missing_in_actual:
                msg += f"  Faltam em actual: {missing_in_actual}\n"
            if extra_in_actual:
                msg += f"  Extras em actual: {extra_in_actual}\n"
            return False, msg

        # Valores
        for key in expected.keys():
            exp_val = expected[key]
            act_val = actual[key]

            exp_norm = GoldenMasterMotor.normalize_value(exp_val, tolerance)
            act_norm = GoldenMasterMotor.normalize_value(act_val, tolerance)

            if isinstance(exp_norm, float) and isinstance(act_norm, float):
                if abs(exp_norm - act_norm) > tolerance:
                    return False, f"Divergência em '{key}': {exp_norm} vs {act_norm}"
            elif exp_norm != act_norm:
                return False, f"Divergência em '{key}': {exp_norm} vs {act_norm}"

        return True, "OK"


def pytest_addoption(parser):
    """Adicionar opção --golden-generate ao pytest."""
    parser.addoption(
        "--golden-generate",
        action="store_true",
        default=False,
        help="Gerar/atualizar snapshots golden (cuidado: sobrescreve)"
    )


def pytest_configure(config):
    """Configurar plugin customizado."""
    config.addinivalue_line(
        "markers", "golden: marca testes que usam golden master"
    )


@pytest.mark.golden
class TestGoldenMasterMotor:
    """Testes de não-regressão do motor de sinais."""

    def setup_method(self):
        """Setup para cada teste."""
        GoldenMasterMotor.setup_class()

    @pytest.mark.parametrize("fixture_name", list(list_fixtures().keys()))
    def test_signal_emission_stable(self, fixture_name: str, request):
        """
        Validar que o sinal emitido é determinístico.

        Para cada fixture, verifica que:
        1. O motor produz um sinal (ou None)
        2. Esse sinal bate exatamente com o golden master congelado
        """
        # Carregar fixture de dados
        df_ohlcv = get_fixture(fixture_name)

        # Rodar motor
        signal = analisar_ativo(
            ticker="TEST",
            nome=f"TEST_{fixture_name.upper()}",
            interval="1d",
            df_provided=df_ohlcv,
            verbose=False
        )

        # Converter para dict se não for None
        signal_dict = signal if signal is None else dict(signal)

        # Modo geração (--golden-generate)
        if request.config.getoption("--golden-generate"):
            GoldenMasterMotor.save_golden(fixture_name, signal_dict)
            pytest.skip("Golden master gerado")

        # Modo validação (padrão)
        if signal is None:
            # Nenhum sinal emitido — compare com golden
            expected = GoldenMasterMotor.load_golden(fixture_name)
            assert expected is None, f"Golden esperava nenhum sinal, mas motor emitiu algo"
        else:
            # Sinal emitido — compare campo a campo
            expected = GoldenMasterMotor.load_golden(fixture_name)
            matches, message = GoldenMasterMotor.compare_signals(
                signal_dict, expected, tolerance=1e-9
            )
            assert matches, f"Regressão em {fixture_name}: {message}"


class TestGoldenMasterFixtures:
    """Testes de sanidade das fixtures."""

    def test_fixtures_carregaveis(self):
        """Validar que todas as fixtures podem ser carregadas."""
        for name in list_fixtures().keys():
            df = get_fixture(name)
            assert not df.empty, f"Fixture {name} está vazio"
            assert len(df) == 30, f"Fixture {name} deve ter 30 dias"
            assert 'Close' in df.columns
            assert 'Volume' in df.columns

    def test_fixtures_dados_validos(self):
        """Validar que fixtures têm dados válidos."""
        for name in list_fixtures().keys():
            df = get_fixture(name)
            # Sem NaN
            assert not df['Close'].isna().any(), f"{name}: Close tem NaN"
            assert not df['Volume'].isna().any(), f"{name}: Volume tem NaN"
            # Volumes positivos
            assert (df['Volume'] > 0).all(), f"{name}: Volume deve ser positivo"
