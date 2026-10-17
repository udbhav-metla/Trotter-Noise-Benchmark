# Verification support

This folder is separate from the official required project tree. Extract both delivered ZIPs into the same parent directory, so `project/` and `support/` are siblings. The original supplied planning pack remains separate and is not part of the submission ZIP.

Create and activate Python 3.12's virtual environment, install `project/requirements.txt`, then run from the common parent:

```powershell
python support/manage.py static
python support/manage.py test
python support/manage.py run
python support/manage.py notebook
python support/manage.py test
```

`run` generates all 108 rows and six figures. `notebook` starts a fresh kernel with the current Python executable, repeats the entire grid, and checks that benchmark CSV and counts match the preceding run byte for byte. It writes the executed notebook and `notebook_verification.json`. `test` saves actual pytest output. Run `test` after `run` for the export-completeness gate; it skips that one gate if no data exists yet.

`python support/manage.py documents` regenerates README/report from actual tables and verification records. `python support/manage.py package` creates clean project and support ZIPs and a SHA-256 manifest. Neither command publishes or submits anything. `init` is an authoring-only command that resets processor JSON and notebook inputs; it is unnecessary for reproduction. `render-guide` expects the original planning pack and PyMuPDF; that helper is not needed to reproduce the scientific project.

`python support/manage.py portability` extracts the project ZIP into a new workspace directory and reruns the full grid there, comparing the benchmark CSV and raw counts byte for byte. `portability_verification.json` records the successful delivered run.

`environment-freeze.txt` records the full tested environment. `project/requirements.txt` pins the scientific/notebook/test dependencies. The support code uses paths relative to its own location. No user-specific machine path is needed.

The requirement ledger records graph selection before simulation. `test_output.txt`, `notebook_verification.json`, and `verification_log.md` record completed checks. The delivered project ZIP excludes caches, environments, planning files and supporting scripts, retaining the required hierarchy.
