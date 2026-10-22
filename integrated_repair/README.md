# Integrated repair, code-only recovery

Recovered construction and rendering source for the post-study integration into the retained V11 forest. The upstream checkpoint explicitly contains neither models nor textures. The root README describes the missing full-scene prerequisites.

`src/` contains branching, leaf-family binding, local contact repair, render orchestration and validation. `legacy/` retains the helper modules imported by the repair stages. `requirements.txt` contains the original host-Python requirements. The exact V11 input is checked by `src/rebuild_delivery.py`; missing assets must not be silently substituted.

`ARCHIVE-NOTES.md` describes a historical full delivery, not the contents of this code-only checkout. `RECOVERY_MANIFEST.json` preserves the original checkpoint hashes. Some source defaults were normalized from old absolute worker paths to `inputs/historical/`, so those original hashes are historical evidence rather than checksums for the normalized source files here. No Blender pipeline has been rerun for publication.

The obsolete archive release packager was excluded because it hard-coded private account-storage status. Its original checksum remains only as a historical entry in the checkpoint manifest; it is not a required modeling/rendering stage.
