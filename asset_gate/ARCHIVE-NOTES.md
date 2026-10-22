> Historical archive notes. The original delivery described below is not fully included in this source-only repository. Read the root README and this folder's README for what is actually available. Historical worker paths have been normalized to inputs/historical/.

# GREEN TERROR — reference-informed botanical asset gate

This package is the **bounded asset-development step**, not a replacement rainforest,
not V14, and not the requested final forest film. The original GREEN TERROR forest
was not edited. The portable branch, fern, and litter-section scenes are real mesh
geometry rendered in native Blender Cycles.

## What to open

- `BRANCH_ASSET_GATE.blend`: a 12-leaf asymmetric, attached twig with two lateral shoots.
- `CORDATE_ASSET_GATE.blend`: a distinct broad, cordate-blade family.
- `FERN_ASSET_GATE.blend`: an asymmetric crown with 7 fronds, attached pinnae,
  2 circinate buds, and selected modeled underside sori. Pinna meshes are instanced.
- `PATCH_ASSET_GATE.blend`: a 1.70 x 1.44 m substrate test using those assets,
  original deadwood/soil, and newly generated litter. This is an evaluation patch,
  not a miniature substitute for the full forest.
- `LEAF_UPPER_INSPECTION.blend` and `LEAF_UNDERSIDE_INSPECTION.blend`: close cameras
  viewing the SAME real leaf in the branch, not isolated photographic plates.
  The underside lights are reflected about the local leaf plane for comparable
  relative illumination; the studio receiver is hidden for the macro inspection.
- `BRANCH_INSPECTION_ANIMATION.blend`: two keyframed 48-frame camera moves, 24 fps.
  This is a static-asset inspection. There is no wind or whole-forest motion here.

All active textures in the delivery models are packed. Their source files are also
included for editing. Native render records bind each image to a saved scene hash.

## Provenance and methods

No image-generation model was used. No leaf photograph was projected onto geometry
or sampled into these leaf textures. Leaf albedo, thickness, roughness, relief, and
venation are produced by `src/make_atlases.py` from numeric construction.

The venation algorithm is a hybrid: a prescribed asymmetric primary/secondary
network, attractor-directed fine branching, and local terminal connections. It is
informed by the class of models in Runions et al. (2005), but is NOT a faithful full
reimplementation, growth simulation, or species-calibrated plant model. Material
parameters are authored approximations, not measured spectral scattering data.

Each blade has an explicit upper surface, lower surface, closed edge, petiole, and
selected geometric underside veins. The vascular map coordinates and geometry
use the same analytic outline and parameterization. Light transport uses an
approximate thin-leaf reflection/transmission material with a transparent shell
exit to avoid counting sheet attenuation twice.

Litter leaves retain their modeled curls. Each is translated vertically as one
rigid object onto a 750 x 750 support raster containing terrain, the native deadwood
BVH, and earlier leaves. Vertices AND lamina centroids are checked. Each accepted
leaf's full projected mesh is rasterized for subsequent support. This is NOT a
continuous collision solver, cloth simulation, equilibrium calculation, or a claim
that all microscopic intersections are absent. The report records rejected/accepted
support decisions instead of claiming global physical validity.

Original `mud_forest` and `dead_tree_trunk_02` CC0 assets are retained from the
existing project. These ARE photographic/scan assets, not newly procedural surfaces.
The full inherited manifest, artist attribution, and original file checksums are
in `provenance/ORIGINAL_ASSET_MANIFEST.json` and the substrate evidence.
No web reference photographs are redistributed in this package.

## Reference notes

- Runions, Fuhrer, Lane, Federl, Rolland-Lagan & Prusinkiewicz (2005),
  *Modeling and visualization of leaf venation patterns*, ACM TOG 24(3), 702–711.
  https://algorithmicbotany.org/papers/venation.sig2005.html
- NParks, *Nephrolepis biserrata*: an architectural and underside-sori reference.
  https://www.nparks.gov.sg/florafaunaweb/flora/1/5/1554
- Piper aduncum field imagery, unequal bases and curved secondary-vein references:
  https://floraofsingapore.wordpress.com/2011/02/11/piper-aduncum/
  https://www.gbif.org/es/species/3086337
- The Piper-like and fern forms are authored approximations. Do not label this
  package as an exact reconstruction of a particular botanical specimen.

## Rebuild and rendering

Tested with Blender **5.4.0 Alpha, build 3fe0f2ab2a29**, native CPU Cycles.
Opening the packed files does not execute scripts. The runtime archive is not
included. Texture generation uses host Python with NumPy, SciPy and Pillow.
The Blender generator uses Blender's own Python, bpy, mathutils and NumPy.

From this folder, with `BLENDER` set to your Blender executable:

```bash
python3 -m pip install numpy scipy pillow
python3 src/make_atlases.py
for kind in branch cordate fern patch; do
  "$BLENDER" --background --threads 4 --python-exit-code 1 \
    --python src/build_assets.py -- --kind "$kind"
done
"$BLENDER" --background --threads 4 --python-exit-code 1 \
  --python src/build_macro.py

"$BLENDER" --background --threads 4 --python-exit-code 1 \
  --python src/render_asset.py -- \
  --scene BRANCH_ASSET_GATE.blend --out review_renders/03_BRANCH_SOFT.png \
  --lighting soft --width 1920 --height 1440 --samples 128
```

Use `--lighting side` or `--lighting back` for the other controlled branch tests.
Use `PATCH_ASSET_GATE.blend --width 2048 --height 1365` for the main substrate shot.
The renderer uses native pixels, adaptive sampling, and Cycles denoising; no output
upscaling or image-generated enhancement. Max samples are in each PNG's adjacent JSON.

The source-frame renderer is `src/render_inspection_video.py`. It writes all native
poses, individual frame records and PNGs. The MP4 uses 960 x 720, 24 fps, 96 source
frames at 32 samples each, encoded without scaling or interpolation. There are two
camera shots and a lighting cut between them. There is no audio and no leaf motion.
MP4 frame counts, source hashes and decoded-frame hashes are validated separately.

## Visual approval is separate from technical validation

The first branch, overly uniform fern, shiny litter, and weak contact candidates
were rejected during this run. Their pictures are not the final render set.
`review_renders/` contains only the frozen candidate renders linked to their saved
models. A native reopen/geometry check establishes portability and structural
integrity. It does NOT establish hyperrealism.

The current remaining weaknesses include smooth branch bark, overly uniform leaf
margin/tissue behavior in some views, residual regularity in fern pinnae, and
local rigid litter seating rather than deformable contact relaxation. The asset
set has not been replicated into the full rainforest. No final forest-video or
world-wide ecological simulation claim is made.

### Memory-safe 2K patch rendering

The initial combined 2K render/denoise process exceeded this worker's 4 GiB memory
limit. The final patch files instead use a native float32 multilayer EXR with the
actual Cycles denoising normal and albedo passes, followed by a fresh compositor
process. No geometry or pixel dimensions are removed by that change.

```bash
python3 src/render_memory_safe.py --blender "$BLENDER" \
  --scene PATCH_ASSET_GATE.blend --output review_renders/07_LITTER_PATCH.png \
  --width 2048 --height 1365 --samples 96 --lighting soft
```

The macro underside is lit from the opposite side, reflected about the inspected
blade's local plane. It is not a claim that upper and lower photographs were taken
from the same light position. Branch soft/side/back tests keep the camera, geometry,
exposure, and resolution fixed while changing which key light is active.

### Selected dry-leaf surface profile

The selected litter model includes the subsequent native review correction in
`src/refine_litter_materials.py`. It reduces exaggerated microscopic relief and
pigment contrast on the dead leaves, and gives the thin rims separate normals.
It does not move the already seated leaves. To reproduce the selected patch after
building the four asset scenes, run:

```bash
"$BLENDER" --background --threads 4 --python-exit-code 1 \
  --python src/refine_litter_materials.py
cp PATCH_DRY_LAMINA_CANDIDATE.blend PATCH_ASSET_GATE.blend
```

The promotion record links the reviewed candidate bytes to the delivered patch.
The branch/fern materials are not modified by this postprocess.

### Tested host environment

The numeric map generator was executed with Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0, and Pillow 12.3.0. `requirements.txt` gives compatible minimums, not a claim that every version combination was tested. The render models are packed and open without the old forest. The unchanged-original regression hash check in the validation script requires that original separately.

### Final review decision

The new branch is the strongest candidate because the veins, attachments, blade curvature, and two surfaces are readable under more than one light. The fern still exposes repeated pinna shapes. In the 2K ground-section image, some dry leaves still read as folded paper and stand too prominently above their support. Those weaknesses are not hidden by the technical checks: **the entire asset set is not approved for full-forest replication**. The pack contains native review candidates and a reusable construction/rendering pipeline, not a photorealism acceptance certificate.
