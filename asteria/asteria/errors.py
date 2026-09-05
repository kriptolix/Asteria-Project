"""Coleta centralizada de erros e warnings durante o pipeline de build.

O pipeline do Asteria nunca deve abortar no primeiro problema: cada etapa
reporta seus problemas neste coletor e o CLI decide, no final, se o build
teve sucesso (sem erros) e imprime um relatório legível.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class Diagnostic:
    severity: Severity
    message: str
    source: str | None = None  # ex: caminho do arquivo .odt

    def __str__(self) -> str:  # pragma: no cover - trivial
        prefix = "ERRO" if self.severity is Severity.ERROR else "AVISO"
        loc = f" [{self.source}]" if self.source else ""
        return f"{prefix}{loc}: {self.message}"


class Diagnostics:
    """Coletor mutável de diagnósticos, compartilhado entre os componentes."""

    def __init__(self) -> None:
        self._items: list[Diagnostic] = []

    def error(self, message: str, source: str | None = None) -> None:
        self._items.append(Diagnostic(Severity.ERROR, message, source))

    def warning(self, message: str, source: str | None = None) -> None:
        self._items.append(Diagnostic(Severity.WARNING, message, source))

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self._items if d.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self._items if d.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def extend(self, other: "Diagnostics") -> None:
        self._items.extend(other._items)

    def report(self) -> str:
        lines = [str(d) for d in self._items]
        return "\n".join(lines)


class AsteriaError(Exception):
    """Erro fatal que interrompe o build imediatamente (ex: YAML inválido)."""
