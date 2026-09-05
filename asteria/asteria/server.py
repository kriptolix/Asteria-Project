"""Servidor de desenvolvimento local (`asteria serve`, spec seção 23-24).

Gera o site, serve `output/` via HTTP, observa `content/`, `static/`,
`theme/` e `site.yaml` (via `watchfiles`, dependência padrão) e reconstrói
automaticamente a cada mudança. **Live reload no navegador é o padrão**:
as páginas geradas ganham um pequeno script que escuta um endpoint de
Server-Sent Events e recarrega a aba sozinha depois de cada rebuild — sem
precisar de nenhuma dependência JS externa, só um endpoint HTTP simples
implementado com a biblioteca padrão do Python.

Páginas HTML "cruas" (`asteria/raw.py`) **nunca** recebem esse script — a
garantia de que elas são servidas exatamente como o autor escreveu
continua valendo em `serve`, não só em `build`.

`--no-watch` desativa tanto o rebuild automático quanto o live reload
(não faz sentido injetar o script se nada nunca vai notificá-lo).
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import threading
import time
from pathlib import Path

from .build import run_build
from .errors import AsteriaError

LIVE_RELOAD_ENDPOINT = "/__asteria_live_reload__"

LIVE_RELOAD_SCRIPT = f"""
<script>
(function() {{
  function connect() {{
    var es = new EventSource("{LIVE_RELOAD_ENDPOINT}");
    es.onmessage = function(ev) {{
      if (ev.data === "reload") {{ location.reload(); }}
    }};
    es.onerror = function() {{ es.close(); setTimeout(connect, 1000); }};
  }}
  connect();
}})();
</script>
""".strip()


def _print_result(result, prefix: str = "Build") -> None:
    for diag in result.diagnostics:
        print(diag)
    if result.success:
        print(f"{prefix} ok ({len(result.generated_files)} arquivo(s)).")
    else:
        print(
            f"{prefix} com {len(result.diagnostics.errors)} erro(s) — "
            "servindo o que já existe em disco.",
            file=sys.stderr,
        )


def _run_build_safe(project_root: Path, converter_name: str, prefix: str, live_reload_script):
    try:
        result = run_build(
            project_root,
            converter_name=converter_name,
            live_reload_script=live_reload_script,
        )
    except AsteriaError as exc:
        print(f"ERRO FATAL: {exc}", file=sys.stderr)
        return None
    _print_result(result, prefix=prefix)
    return result


class ReloadBroadcaster:
    """Contador de gerações + condição, usado pelos handlers SSE para saber
    quando um novo rebuild aconteceu (spec 24: "detectar alterações")."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._generation = 0

    def notify_reload(self) -> None:
        with self._condition:
            self._generation += 1
            self._condition.notify_all()

    def current_generation(self) -> int:
        with self._condition:
            return self._generation

    def wait_for_change(self, last_seen: int, timeout: float) -> int:
        with self._condition:
            if self._generation != last_seen:
                return self._generation
            self._condition.wait(timeout)
            return self._generation


class _DevServerHandler(http.server.SimpleHTTPRequestHandler):
    """Serve arquivos estáticos normalmente, mais um endpoint SSE para o
    live reload. O broadcaster fica no `self.server` (ver `_Server` abaixo)
    para não depender de estado global."""

    def do_GET(self) -> None:  # noqa: N802 (nome exigido pela stdlib)
        if self.path == LIVE_RELOAD_ENDPOINT:
            self._handle_sse()
            return
        super().do_GET()

    def _handle_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        broadcaster: ReloadBroadcaster = self.server.broadcaster  # type: ignore[attr-defined]
        last_seen = broadcaster.current_generation()
        try:
            while True:
                new_gen = broadcaster.wait_for_change(last_seen, timeout=25)
                if new_gen != last_seen:
                    self.wfile.write(b"data: reload\n\n")
                    last_seen = new_gen
                else:
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        if args and "__asteria_live_reload__" in str(args[0]):
            return  # não poluir o log com a conexão SSE de longa duração
        sys.stderr.write(f"  {self.address_string()} - {args[0] if args else ''}\n")


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def _start_http_server(output_dir: Path, host: str, port: int) -> _Server:
    handler = functools.partial(_DevServerHandler, directory=str(output_dir))
    httpd = _Server((host, port), handler)
    httpd.broadcaster = ReloadBroadcaster()  # type: ignore[attr-defined]
    return httpd


def serve(
    project_root: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    converter_name: str = "auto",
    watch: bool = True,
) -> int:
    live_reload_script = LIVE_RELOAD_SCRIPT if watch else None

    result = _run_build_safe(project_root, converter_name, "Build", live_reload_script)
    if result is None:
        return 1

    try:
        httpd = _start_http_server(result.output_dir, host, port)
    except OSError as exc:
        print(f"ERRO: não foi possível abrir {host}:{port} — {exc}", file=sys.stderr)
        return 1

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    print(f"\nServindo em http://{host}:{port}/ (Ctrl+C para sair)")

    if not watch:
        print("Rebuild automático e live reload desativados (--no-watch).")
        _idle_until_interrupted()
        httpd.shutdown()
        return 0

    watch_paths = [
        p
        for p in [
            project_root / "content",
            project_root / "static",
            project_root / "theme",
            project_root / "site.yaml",
        ]
        if p.exists()
    ]
    if not watch_paths:
        print("Nada para observar (content/static/theme/site.yaml não encontrados).")
        _idle_until_interrupted()
        httpd.shutdown()
        return 0

    from watchfiles import watch as watchfiles_watch

    watched_names = ", ".join(str(p.relative_to(project_root)) for p in watch_paths)
    print(f"Observando mudanças em: {watched_names} (live reload ativo)\n")

    try:
        for changes in watchfiles_watch(*watch_paths):
            print(f"\n{len(changes)} mudança(s) detectada(s), reconstruindo...")
            rebuilt = _run_build_safe(project_root, converter_name, "Rebuild", live_reload_script)
            if rebuilt is not None:
                httpd.broadcaster.notify_reload()  # type: ignore[attr-defined]
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()

    return 0


def _idle_until_interrupted() -> None:
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
