> Historical archive notes. The original delivery described below is not fully included in this source-only repository. Read the root README and this folder's README for what is actually available. Historical worker paths have been normalized to inputs/historical/.

# GREEN TERROR — verified native recovery

This package records work actually executed in this continuation. It is not a
claim that the V14 hyperrealism specification, matched 2K review set, or 240-frame
1080p film has been completed.

The working session contained no V14 model or render_profiled.py. A retained V11
model, the integrated botanical/contact repair source, and the native Blender
binary archive were available. The retained integrated repair was reconstructed
explicitly, not renamed as V14. The original V11 input was not modified.

## Changes and verification

* Native EXR configuration now uses supported RNA enum identifiers rather than a
  hard-coded, invalid MULTILAYER_IMAGE value. Both single-layer and multilayer EXR
  writes were executed in the retained Blender 5.4 Alpha build 3fe0f2ab2a29.
* The forest reconstruction executes native source stages, validates the final
  source report against the saved .blend hash, and emits its actual provenance.
* The packed model was reopened: 42 packed file images, no linked external Blender
  libraries, and 18,940 historical planting roots were detected.
* The render test uses the original close-up camera at 960 x 720, 32 samples.
  It is a pipeline proof from the reconstructed older asset revision, NOT a new
  realism candidate. Only a final matching render record establishes completion.
* No generated rainforest picture is used by the rebuild or renderer. Retained
  authorized scanned bark/soil/deadwood inputs and procedural foliage are used.

## Portable recovery entrypoint

Keep src/resume.py and src/exr_compat.py together. Use Python with NumPy for the
band assembly; Blender supplies its own Python for native geometry/render stages.
The baseline and rebuild source are separate inputs because neither their absence
nor a different hash may be silently bypassed.

```
python src/resume.py --blender /path/to/blender \
  --baseline /path/to/GREEN_TERROR_V11_STRUCTURE.blend \
  --source-archive /path/to/GREEN_TERROR_INTEGRATED_REPAIR_SOURCE.zip \
  --workdir /path/to/recovery --render
```

The exact baseline SHA-256 is
16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e.

Stages are resumable only when their input/source/binary hashes and completed
output hashes agree. Native pixel bands are resumed through the retained renderer.
A failure propagates as a failed run, not a completion claim.

## Scope still outstanding

The major art overhaul, new reference-matched asset acceptance, matched 2K
convergence comparisons, full motion validation, and 240-frame native film are
not completed by this repair. Reconstructed appearance inherits the earlier
forest's weaknesses. Do not promote the recovery image as a V14 visual upgrade.
