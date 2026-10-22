> Historical archive notes. The original delivery described below is not fully included in this source-only repository. Read the root README and this folder's README for what is actually available. Historical worker paths have been normalized to inputs/historical/.

# GREEN TERROR — integrated botanical and contact repair

This is an actual native Blender/Cycles continuation of the retained V11 forest
and the subsequent procedural botanical asset studies. It is not a recovery of
missing intermediate V12/V13 models. The numbered V11 cameras, world, lights,
terrain, large tree landmarks, and all 18,940 original planting-root transforms
are retained. Their referenced plant assets have changed.

## Frozen deliverables

* `GREEN_TERROR_FOREST_REPAIRED_FINAL.blend`: the complete instanced forest, with the
  new plant families, branching graphs, native host-attached climbing foliage,
  repaired woody-vine materials, fern families, and local litter clusters.
* `GROUND_SECTION_FINAL.blend`: a bounded approximately 1.7 by 1.44 metre contact
  study around inherited soil and deadwood. This is an asset-development section,
  not the entire forest and not a replacement miniature claimed as a forest.
* `renders/05_FOREST_CLOSEUP.png`: original `04_BARK_AND_LITTER` camera.
* `renders/06_FOREST_UNDERSTORY.png`: original `02_ROOTS_AND_UNDERSTORY` camera.
* `renders/04_GROUND_SECTION.png`: native repaired ground-section study.

The JSON completion record alongside each image identifies its exact scene hash,
resolution, samples, camera matrix and display transform. `DELIVERY_REPORT.json`
is generated only after those outputs have been independently checked. An image
without a completed matching record is not a final delivery.

## What is repaired

**Actual forest bindings.** Both original base families and later variant
collections are updated, rather than creating higher-quality orphan prototypes
that the forest does not actually reference. Unchanged planting transforms are
verified independently of asset replacement.

**Branching.** Referenced rooted plants contain hierarchical graphs with parent
relationships, irregular primary branching, secondary leafy shoots, buds and
subordinate leaders. Leaf dimensions are not multiplied by plant height without
bounds. This is authored developmental structure, not a measured ecological model.

**Leaves.** The previously reviewed procedural venation/tissue maps and explicit
upper/lower laminae are now used in context. Upper, lower and thin-rim normals are
separated so smoothing does not inflate the shell edges. Main leaf construction
remains the approved asset-study construction; it is not a new photograph or an
image-generated texture.

**Ferns.** Families use different age classes, staggered pinnae, variable spacing,
curvature, sweep, missing mature pinnae and connected fiddleheads. The leaflet
frame follows its frond. Shapes are still finite authored botanical approximations.

**Litter.** The bounded section uses sequential local position-based relaxation:
edge-length preservation, gravity, rest-shape constraints, support heights and
face-centroid contact checks. Upper/lower surfaces and veins move together. Bad
high-strain or unsupported candidates are rejected rather than stretched across
steep supports. The result is not a full cloth or global collision solver.

**Materials.** Woody lianas no longer share the uniformly green petiole response.
Inherited shelf-fungus materials lose their regular cartoon-like bands, without
claiming that every inherited fungus mesh has been rebuilt. The stronger original
bark and shared moss structures remain instead of being concealed under a new
uniform moss blanket.

## Reproduce the stills

The executed environment uses Blender **5.4.0 Alpha**, build `3fe0f2ab2a29`, CPU
Cycles, four threads. The binary is not bundled. This development build was the
available native runtime; compatibility with other Blender versions is not claimed
without testing. The saved scenes can be opened without running embedded text.

The two final models have packed file textures. No external source textures are
needed to open them. The tested rendering scripts externalize those packed bytes
into a local texture cache to reduce memory, without resampling the inputs.

From this directory, with Python dependencies installed:

```bash
python3 -m pip install -r requirements.txt
python3 src/render_banded.py --blender /path/to/blender \
  --scene GREEN_TERROR_FOREST_REPAIRED_FINAL.blend --camera 04_BARK_AND_LITTER \
  --output my_renders/closeup.png --width 1280 --height 960 --samples 48
python3 src/render_banded.py --blender /path/to/blender \
  --scene GREEN_TERROR_FOREST_REPAIRED_FINAL.blend --camera 02_ROOTS_AND_UNDERSTORY \
  --output my_renders/understory.png --width 1280 --height 854 --samples 40
python3 src/render_delivery.py --blender /path/to/blender \
  --kind ground --output my_renders/ground.png \
  --width 1600 --height 1067 --samples 80
```

Supply `--scene` when a model is elsewhere. The banded renderer assembles exact
full-resolution native pixel rows; it does not rescale or blend them. It resumes
only bands with matching plans, completion records and file hashes. The final
denoiser runs once on the assembled full frame. `render_delivery.py --dry-run`
prints its full-frame commands without executing them. Stages run serially and
stop on failures. Do not run
multiple full-forest workers concurrently in a 4 GiB cgroup. A prior concurrent
build/render attempt exceeded that worker limit; this is recorded, not hidden.
A later full-frame 1280 x 960 forest attempt also exceeded the worker budget
near completion. It was replaced with the banded path, not relabeled as complete.
No geometry is removed merely to make these delivered renders fit.

Forest output uses native scene-linear Cycles radiance followed by separate native
surface-color and **shading-normal** passes, independent full-frame OIDN, and one
AgX display conversion. Ground-section output uses native matching Cycles guides.
The output is not upscaled and not image-generated. The guides/denoiser are still
approximations, particularly for transparency and fine geometry.

## Rebuild and tests

Opening/rendering a packed model is independent from rebuilding the historical
lineage. To rebuild the forest, supply the **exact preserved V11 input**:

```
16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e
```

The convenience launcher validates this input before authoring and refuses to
overwrite a final output unless explicitly requested:

```bash
python3 src/rebuild_delivery.py --blender /path/to/blender \
  --baseline /path/to/GREEN_TERROR_V11_STRUCTURE.blend --dry-run
python3 src/rebuild_delivery.py --blender /path/to/blender \
  --baseline /path/to/GREEN_TERROR_V11_STRUCTURE.blend
```

For individual stages, set `GREEN_TERROR_BASELINE` to that `.blend` file. Run the native scripts in
this order: `src/integrate_forest.py`, `src/finalize_models.py`,
`src/refine_architecture.py`, then `src/repair_climber_bindings.py`. The last
script produces `GREEN_TERROR_FOREST_LEAF_BINDING_TEST.blend`; the delivered
`GREEN_TERROR_FOREST_REPAIRED_FINAL.blend` is an unchanged byte-copy of that reviewed
checkpoint. The bounded study is first produced with
`src/build_repaired_assets.py`; finalization expects that study to exist. See the
individual scripts' entry points and actual evidence records before invoking a
partial stage. All source and procedural assets required by these scripts are
included in the source bundle, except the separate preserved V11 input model.

```
/path/to/blender -b -t 4 --python-exit-code 1 -P src/test_repair_math.py
/path/to/blender -b -t 4 --python-exit-code 1 -P src/validate_models.py -- \
  GREEN_TERROR_FOREST_REPAIRED_FINAL.blend GROUND_SECTION_FINAL.blend
```

`validate_models.py` checks each actual native mesh for non-finite vertices and
zero-area triangles, and verifies packed image bytes. These checks do not certify
realism, absence of all intersections, botanical accuracy or temporal quality.

## Scope and provenance

The forest retains inherited CC0 scan-based soil, bark and deadwood. The maps and
geometry of the new foliage and litter are procedural. Original asset provenance
is retained under `provenance/`. No previously image-generated rainforest picture
is a texture, background, camera projection, or render input.

The bounded contact solve is not applied as a global dynamic forest simulation.
Distant crown geometry is retained. Plants are static in the delivered forest;
there is no new wind solver or full-forest film in this release. Repeated forms,
large trunk simplification and some overly smooth leaf shading remain visible.
The whole-forest integration is a real completed revision, not a claim that every
realism issue is solved.

Earlier source-study reports may be retained separately for provenance; only the
current `DELIVERY_REPORT.json` and its listed frozen-model/image hashes describe
this delivery. Never infer completion from a filename, process exit code alone,
or a report copied from an earlier asset study.

## Integration correction retained in this release

The final full-forest model no longer stretches the reviewed narrower leaves to
the inherited wide generic blade proportions. Each climbing vine uses one coherent
leaf family with developmental variation; separate vines can use different families.
Mature and juvenile blades differ in orientation. The woody host, planting roots,
and original camera/light controls remain unchanged. Basal plant families also
remain coherent across age states. These are authored botanical approximations,
not claims of a species-calibrated growth simulation.

The earlier integrated-review outputs and the rejected dry-tissue test are not
included as final deliverables. The source retains the necessary original dry
leaf maps, not the experimental flattened-color maps.

The native model files described above are not included in this public source-only checkout.
