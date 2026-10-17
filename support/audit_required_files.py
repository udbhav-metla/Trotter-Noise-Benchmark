"""Audit the official required hierarchy and the clean publication archive."""
import hashlib
import json
from pathlib import Path
import zipfile
import nbformat

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "project"
files = ["README.md", "main.ipynb", "requirements.txt",
         "processors/processor_A.json", "processors/processor_B.json",
         "src/__init__.py", "src/problem.py", "src/processors.py",
         "src/routing.py", "src/metrics.py", "src/visualization.py", "report.md"]
directories = ["data/raw", "data/processed", "processors", "src", "results/tables",
               "results/figures", "assets/qff_phase1_latex_images"]
missing = [p for p in files if not (ROOT / p).is_file()]
missing += [p + "/" for p in directories if not (ROOT / p).is_dir()]
assert not missing, f"Missing required paths: {missing}"
assert all((ROOT / p).stat().st_size for p in files), "Empty required file"
book = nbformat.read(ROOT / "main.ipynb", as_version=4)
nbformat.validate(book)
cells = [c for c in book.cells if c.cell_type == "code"]
assert all(c.execution_count is not None for c in cells)
assert not any(o.output_type == "error" for c in cells for o in c.outputs)
assert len(list((ROOT / "data/raw/circuits").glob("*.qpy"))) == 108
assert len(list((ROOT / "results/figures").glob("*.png"))) == 6
excluded = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".venv", ".git"}
payload = {p.relative_to(ROOT).as_posix(): p for p in ROOT.rglob("*")
           if p.is_file() and not excluded.intersection(p.parts)}
archive_path = BASE / "PS_S3_Phase1_Project.zip"
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    names = {n.removeprefix("project/") for n in archive.namelist() if not n.endswith("/")}
    assert names == set(payload), "Archive and clean project file lists differ"
    for name, path in payload.items():
        assert archive.read("project/" + name) == path.read_bytes(), f"Stale archive file: {name}"
status = {"required_files": {p: "present and nonempty" for p in files},
          "required_directories": {p: "present" for p in directories},
          "missing_required_paths": missing, "clean_project_files": len(payload),
          "executed_notebook_code_cells": len(cells), "compiled_circuits": 108,
          "figures": 6, "archive_matches_project": True,
          "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
          "optional_equation_images": "Not required; assets directory retained with .gitkeep."}
(BASE / "support/required_files_audit.json").write_text(json.dumps(status, indent=2)+"\n")
print(json.dumps(status, indent=2))
