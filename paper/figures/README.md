# Reproducing the Figures

The plotting code reads only committed CSV files under `paper/source_data/`; it does not read API keys and never calls an LLM.

Create a clean environment and generate all figures:

```powershell
python -m venv .figure-env
.\.figure-env\Scripts\python.exe -m pip install matplotlib==3.10.3 numpy==2.2.6 pillow==11.2.1
.\.figure-env\Scripts\python.exe paper\figures\make_figures.py
```

Each figure is exported as editable `SVG/PDF`, 360-dpi `PNG`, and 600-dpi LZW-compressed `TIFF` under `paper/figures/output/`. The bilingual interpretation notes are in `paper/figure_descriptions_bilingual.md`.
