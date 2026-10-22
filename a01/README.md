# A01 botanical working source

Earlier cordate, elliptic and lance leaf construction, kept separately from the later asset gate and the unimplemented V14 specification.

The numerical generator is `src/generate_vascular_assets.py`; it requires NumPy, SciPy, Pillow and Shapely with `contains_xy` support. `src/constrain_blade_boundaries.py` runs inside Blender and updates the generated boundary triangulations. The original generated PNG/NPZ assets are omitted; the source is retained.

Forest/litter integration needs the exact separate V11 scene, its legacy source layout and a Blender binary. Historical absolute defaults were normalized to `inputs/historical/`; adapt those paths deliberately before use. These archival orchestration scripts are not the root quickstart, and no A01 native model is included or relabeled V14.

`references/` preserves the botanical reference descriptions, attribution and inherited asset manifest. `evidence/` contains historical construction records, not a new test run.
