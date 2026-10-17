# Qskit_Online

Qiskit Fall Fest Phase 1: **PS-S3 - Noise Accumulation in Trotter Circuits**.

The complete required submission hierarchy is in [`project/`](project/). Start with the [project README](project/README.md), [executed notebook](project/main.ipynb), and [scientific report](project/report.md).

Supporting tests, reproduction scripts, and verification records are kept separately in [`support/`](support/). The original planning pack, Python environment, and caches are excluded.

Verified: all required files are present; 27 tests pass; the six-cell notebook executes from a fresh kernel; all 108 benchmark cases are exported. Exact results and limitations are documented in the report.

From the repository root, after creating a Python 3.12 environment:

```sh
python -m pip install -r project/requirements.txt
python support/manage.py test
python support/manage.py notebook
```

Actual team details remain to be supplied. No hackathon portal submission has been made.
