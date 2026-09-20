"""
Local development server.
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
from .config import load_config
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
        print(f"{prefix} ok ({len(result.generated_files)} file(s)).")
    else:
        print(
            f"{prefix} com {len(result.diagnostics.errors)} error(s) — "
            "serving what already exists on disk.",
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
        print(f"FATAL ERROR: {exc}", file=sys.stderr)
        return None
    _print_result(result, prefix=prefix)
    return result


class ReloadBroadcaster:
    """Generation counter + condition, used by SSE handlers to determine
        when a new rebuild has occurred.."""

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
    """Serves static files normally, plus an SSE endpoint for
        live reload."""

    def do_GET(self) -> None:  # noqa: N802 (name required by the stdlib)
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
            return  # avoid cluttering the log with the long-lived SSE connection
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
        print(f"ERROR: could not open {host}:{port} — {exc}", file=sys.stderr)
        return 1

    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    print(f"\nServing at http://{host}:{port}/ (Ctrl+C to exit)")

    if not watch:
        print("Automatic rebuild and live reload disabled (--no-watch).")
        _idle_until_interrupted()
        httpd.shutdown()
        return 0

    # Mirrors run_build's own path resolution (project_root / "source" /
    # config_filename): all editable project files — content, static
    # assets, site.yaml — live under source/, not directly under
    # project_root.
    source_dir = project_root / "source"
    watch_paths = [
        p
        for p in [
            source_dir / "content",
            source_dir / "static",
            source_dir / "site.yaml",
        ]
        if p.exists()
    ]

    # The active theme's directory — SiteConfig.theme_dir combines
    # `theme.directory` and `theme.name` from site.yaml (falling back to
    # Asteria's own bundled theme when the project doesn't have its own),
    # so this follows whatever the site is actually configured to use
    # instead of a fixed guess at `source/themes`. Loaded again here
    # (rather than threaded through from the initial build above)
    # because BuildResult doesn't carry the SiteConfig it built from; the
    # try/except is defensive only — this same file already parsed
    # successfully moments ago for the initial build.
    try:
        theme_dir = load_config(source_dir / "site.yaml").theme_dir
        if theme_dir.exists():
            watch_paths.append(theme_dir)
    except AsteriaError:
        pass

    if not watch_paths:
        print("Nothing to observe (source/content, source/static, source/site.yaml, theme directory not found).")
        _idle_until_interrupted()
        httpd.shutdown()
        return 0

    from watchfiles import watch as watchfiles_watch

    # The theme directory may be Asteria's own bundled theme, which
    # lives inside the installed package rather than under project_root
    # — relative_to() would raise for that one, so fall back to an
    # absolute path in the (rare) case it isn't actually relative.
    watched_names = ", ".join(
        str(p.relative_to(project_root)) if p.is_relative_to(project_root) else str(p)
        for p in watch_paths
    )
    print(f"Watching for changes in: {watched_names} (live reload active)\n")

    try:
        for changes in watchfiles_watch(*watch_paths):
            print(f"\n{len(changes)} change(s) detected, rebuilding...")
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