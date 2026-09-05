"""Alguns testes de integração chamam `run_build` diretamente sobre
`examples/meu-site` (não sobre uma cópia em tmp_path), o que deixa um
`build/` e um `.asteria-cache.json` reais dentro do repositório. Isso é
inofensivo para os testes em si (cada um gera o que precisa), mas pode
confundir outros testes que comparam estado "antes/depois" nesse mesmo
diretório. Limpa antes e depois da sessão inteira, por precaução.
"""
import shutil
from pathlib import Path

import pytest

EXAMPLE_ROOT = Path(__file__).parent.parent / "examples" / "meu-site"
EXAMPLE_BUILD_DIR = EXAMPLE_ROOT / "build"
EXAMPLE_CACHE_FILE = EXAMPLE_ROOT / ".asteria-cache.json"


def _clean():
    shutil.rmtree(EXAMPLE_BUILD_DIR, ignore_errors=True)
    EXAMPLE_CACHE_FILE.unlink(missing_ok=True)


@pytest.fixture(autouse=True, scope="session")
def _clean_example_build_dir():
    _clean()
    yield
    _clean()
