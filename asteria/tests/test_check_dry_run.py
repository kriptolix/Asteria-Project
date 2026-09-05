from pathlib import Path

from asteria.build import run_build

EXAMPLE_ROOT = Path(__file__).parent.parent / "examples" / "meu-site"


def test_dry_run_does_not_write_output_dir(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    shutil.copytree(EXAMPLE_ROOT, project)
    output_dir = project / "build"
    # Alguns testes de integração constroem diretamente em EXAMPLE_ROOT
    # (não numa cópia), então a pasta pode já existir aqui por causa da
    # ordem de execução de outros testes — remove antes de validar.
    shutil.rmtree(output_dir, ignore_errors=True)

    result = run_build(project, converter_name="fallback", dry_run=True)

    assert result.success
    assert not output_dir.exists()
    assert result.generated_files == []


def test_dry_run_still_reports_same_diagnostics_as_real_build(tmp_path: Path):
    import shutil

    project = tmp_path / "site"
    shutil.copytree(EXAMPLE_ROOT, project)

    dry = run_build(project, converter_name="fallback", dry_run=True)
    real = run_build(project, converter_name="fallback", dry_run=False)

    assert dry.success == real.success
    assert len(dry.diagnostics.warnings) == len(real.diagnostics.warnings)
    assert len(dry.pages) == len(real.pages)
    assert len(dry.posts) == len(real.posts)


def test_dry_run_detects_broken_reference_without_writing(tmp_path: Path):
    import shutil
    import zipfile

    project = tmp_path / "site"
    shutil.copytree(EXAMPLE_ROOT, project)
    shutil.rmtree(project / "build", ignore_errors=True)
    inicio = project / "content" / "pages" / "inicio.odt"

    with zipfile.ZipFile(inicio) as zin:
        content = zin.read("content.xml").decode("utf-8")
    content = content.replace("[[sobre]]", "[[pagina-inexistente]]")
    tmp_zip = inicio.with_suffix(".tmp.odt")
    with zipfile.ZipFile(inicio) as zin, zipfile.ZipFile(tmp_zip, "w") as zout:
        for item in zin.infolist():
            if item.filename == "content.xml":
                zout.writestr(item, content)
            else:
                zout.writestr(item, zin.read(item.filename))
    inicio.unlink()
    tmp_zip.rename(inicio)

    result = run_build(project, converter_name="fallback", dry_run=True)

    assert not result.success
    assert any("pagina-inexistente" in e.message for e in result.diagnostics.errors)
    assert not (project / "build").exists()


def test_dry_run_leaves_existing_output_untouched(tmp_path: Path):
    """`check` não deve mexer num build/ já existente de uma execução
    anterior de `asteria build`."""
    import shutil

    project = tmp_path / "site"
    shutil.copytree(EXAMPLE_ROOT, project)

    run_build(project, converter_name="fallback", dry_run=False)
    output_dir = project / "build"
    assert output_dir.exists()
    marker = output_dir / "MARCADOR_DE_TESTE.txt"
    marker.write_text("não deveria sumir", encoding="utf-8")

    run_build(project, converter_name="fallback", dry_run=True)

    assert marker.exists()
    assert marker.read_text(encoding="utf-8") == "não deveria sumir"
