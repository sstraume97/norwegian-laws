"""Tests for generate_laws_json schema with kind and path fields."""
import json
from pathlib import Path

from lovdata_publisher.quarto import generate_laws_json


def _write_law(p: Path, refid: str, korttittel: str = ""):
    body = (
        '---\n'
        f'tittel: "Test law"\n'
        f'korttittel: "{korttittel}"\n'
        f'refid: "{refid}"\n'
        'departement: "Finansdepartementet"\n'
        'ikrafttredelse: "2001-01-01"\n'
        '---\n\n# Test\n'
    )
    p.write_text(body, encoding="utf-8")


def test_generate_laws_json_lov_only(tmp_path):
    lover = tmp_path / "lover"
    lover.mkdir()
    _write_law(lover / "lov-1998-07-17-56.md", "lov/1998-07-17-56", "Regnskapsloven")
    out = tmp_path / "laws.json"

    laws = generate_laws_json(str(lover), str(out), version_tags=["v2001"])

    assert len(laws) == 1
    assert laws[0]["kind"] == "lov"
    assert laws[0]["path"] == "lover/lov-1998-07-17-56.md"
    assert laws[0]["lovdata"].startswith("https://lovdata.no/dokument/NL/")


def test_generate_laws_json_with_forskrifter(tmp_path):
    lover = tmp_path / "lover"
    lover.mkdir()
    forskrifter = tmp_path / "forskrifter"
    forskrifter.mkdir()
    _write_law(lover / "lov-1998-07-17-56.md", "lov/1998-07-17-56", "Regnskapsloven")
    _write_law(forskrifter / "forskrift-2024-06-21-1166.md", "forskrift/2024-06-21-1166")

    out = tmp_path / "laws.json"
    laws = generate_laws_json(
        str(lover), str(out),
        version_tags=["v2024"],
        forskrifter_dir=str(forskrifter),
    )

    kinds = {law["kind"] for law in laws}
    assert kinds == {"lov", "forskrift"}

    forskrift = next(l for l in laws if l["kind"] == "forskrift")
    assert forskrift["path"] == "forskrifter/forskrift-2024-06-21-1166.md"
    assert forskrift["lovdata"].startswith("https://lovdata.no/dokument/SF/")


def test_generate_laws_json_no_forskrifter_dir_is_ok(tmp_path):
    lover = tmp_path / "lover"
    lover.mkdir()
    _write_law(lover / "lov-1998-07-17-56.md", "lov/1998-07-17-56", "Regnskapsloven")

    out = tmp_path / "laws.json"
    laws = generate_laws_json(str(lover), str(out), version_tags=["v2024"], forskrifter_dir=None)
    assert all(l["kind"] == "lov" for l in laws)
