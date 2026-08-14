"""
Configuração global dos testes (pytest).

Define fixtures, hooks customizados e configurações compartilhadas
entre todos os testes do projeto.
"""
import pytest


def pytest_addoption(parser):
    """Adicionar opções customizadas ao pytest."""
    parser.addoption(
        "--golden-generate",
        action="store_true",
        default=False,
        help="Gerar/atualizar snapshots golden (cuidado: sobrescreve)"
    )


def pytest_configure(config):
    """Registrar marcas customizadas."""
    config.addinivalue_line(
        "markers",
        "golden: marca testes que validam o golden master (não-regressão)"
    )
    config.addinivalue_line(
        "markers",
        "integration: marca testes de integração (usam rede/banco)"
    )
    config.addinivalue_line(
        "markers",
        "slow: marca testes lentos"
    )
    config.addinivalue_line(
        "markers",
        "serial: marca testes que devem rodar sequencial (não paralelo)"
    )


@pytest.fixture(scope="session")
def golden_generate_mode(request):
    """Fixture que indica se estamos em modo geração de golden."""
    return request.config.getoption("--golden-generate")
