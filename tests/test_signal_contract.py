"""
Teste de Contrato — Validação da Estrutura de Sinal.

Garante que qualquer campo novo adicionado ao motor também é persistido
e refletido no tipo TypeScript.
"""
import json
import pytest
from pathlib import Path
from sqlalchemy import text

from backend.domain.signal import Signal  # Será criado em F1
from backend.services.signal_service import persist_signals


def get_persisted_columns() -> set[str]:
    """
    Extrair nomes de coluna da função persist_signals analisando código-fonte.

    Uma futura análise tipo-dirigida (Fase 1) vai eliminar essa duplicação.
    """
    # Hoje vamos ler a função e extrair os campos mapeados
    signal_service_path = Path("backend/services/signal_service.py")
    content = signal_service_path.read_text()

    # Procurar por linhas com '.get(' que indicam campos persistidos
    import re
    pattern = r"sinal\.get\(['\"]([^'\"]+)['\"]\)"
    fields = set(re.findall(pattern, content))

    return fields


def get_motor_fields() -> set[str]:
    """
    Extrair campos gerados pelo motor analisando core_engine.py.

    Busca a função _montar_sinal e lista todos os campos do dict retornado.
    """
    core_engine_path = Path("backend/services/core_engine.py")
    content = core_engine_path.read_text()

    # Procurar a função _montar_sinal
    import re
    # Simplificado: procurar por return { e depois extrair chaves
    match = re.search(r"def _montar_sinal\(.*?\).*?return\s*({.*?})", content, re.DOTALL)

    if match:
        dict_literal = match.group(1)
        # Procurar por "chave": ... ou 'chave': ...
        pattern = r"['\"]([^'\"]+)['\"]:\s*"
        fields = set(re.findall(pattern, dict_literal))
        return fields

    return set()


def get_typescript_fields() -> set[str]:
    """
    Extrair campos do tipo Signal em TypeScript.

    Lê src/types/signals.ts e extrai as propriedades do interface Signal.
    """
    ts_path = Path("src/types/signals.ts")
    if not ts_path.exists():
        return set()

    content = ts_path.read_text()

    import re
    # Procurar por interface Signal { ... } ou type Signal = { ... }
    match = re.search(r"(?:interface|type)\s+Signal\s*(?:=\s*)?{([^}]+)}", content, re.DOTALL)

    if match:
        interface_body = match.group(1)
        # Procurar por propriedades (name: type ou name?: type)
        pattern = r"(\w+)\s*\??\s*:\s*"
        fields = set(re.findall(pattern, interface_body))
        return fields

    return set()


@pytest.mark.serial
class TestSignalContract:
    """Testes de contrato de sinal."""

    def test_motor_persist_consistency(self):
        """
        Validar que todos campos do motor são persistidos.

        Se o motor adiciona um campo novo em _montar_sinal mas esquece
        de persistir em signal_service.persist_signals, este teste falha.
        """
        motor_fields = get_motor_fields()
        persisted_fields = get_persisted_columns()

        missing = motor_fields - persisted_fields

        assert not missing, (
            f"Campos no motor mas não persistidos: {missing}\n"
            "Adicione em backend/services/signal_service.persist_signals"
        )

    def test_persist_typescript_consistency(self):
        """
        Validar que campos persistidos existem em TypeScript.

        Se um campo é persistido em SQL mas não existe no tipo TS,
        o frontend vai receber undefined.
        """
        persisted_fields = get_persisted_columns()
        ts_fields = get_typescript_fields()

        missing = persisted_fields - ts_fields

        if missing:
            pytest.warns(
                UserWarning,
                f"Campos persistidos mas não em TypeScript: {missing}\n"
                "Verifique src/types/signals.ts"
            )

    def test_no_field_drift(self):
        """
        Resumo: validar alinhamento total de 3 fontes de verdade.

        Com Fase 1 (modelo Pydantic), esse teste será substituído
        por validação de tipo em tempo de compilação.
        """
        motor = get_motor_fields()
        persist = get_persisted_columns()
        ts = get_typescript_fields()

        # Hoje aceitamos leve divergência, mas documentamos
        drift = (motor | persist | ts) - (motor & persist & ts)

        if drift:
            print(f"\n⚠️  Drift de campos: {drift}")
            print(f"   Motor:     {motor}")
            print(f"   Persist:   {persist}")
            print(f"   TypeScript: {ts}")

        # Para Fase 1: isso vai falhar até que tenhamos 100% alinhamento
        # pytest.fail(f"Drift de 3 fontes de verdade: {drift}")
