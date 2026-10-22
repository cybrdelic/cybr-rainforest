# GREEN TERROR — V14 rebuild specification

**Status: specification, not an executed scene revision.**

The deliverable defined here is a visibly stronger version of the existing native rainforest, not a rendering-pipeline repair, a new picture inspired by the scene, or a larger object count. Blender/Cycles remains the rendering path. No image generation, generated replacement backgrounds, generative texture synthesis, image-to-video substitution, or AI frame interpolation is permitted. Numerical rendering denoising remains allowed, subject to the tests below.

This specification is deliberately fail-closed: missing evidence means **not evaluated**, not passed. All acceptance decisions in the supplied manifest are initially unset. Numerical thresholds below are proposed project engineering tolerances, not scientific definitions of realism or biological measurements. Changes to them require a versioned rationale before judging the candidate, not after it fails.

## 1. What is being replaced, and what is preserved

The latest retained integration report explicitly leaves smooth/repeated leaf silhouettes, repeated upright growth, simple inherited wood geometry, crumpled-looking litter, and untested animation unresolved. It also records a contract preserving all wood coordinates and planting controllers. Those invariants conflict with the requested wood and distribution redesign. [P1]

**Preserve:** the rainforest's terrain coordinate system, major landmark locations, extent, named comparison cameras, reference images, approved scanned bark/soil/deadwood inputs, and an untouched baseline copy. Preserve major trunk/root centerlines as landmarks unless a documented local change is required. Do not delete distant forest merely to make a close-up render fit memory.

**Permit and record:** replacement leaf/branch/fern/palm geometry; remodeling trunk and buttress surfaces; reattachment of affected climbers and growth; changing juvenile-plant species, height, orientation, and root distribution where the layout is repetitive; redesigning litter and its contact solve. The historical count of 18,940 roots is provenance, not a visual acceptance target. Every changed/deleted/added placement receives an explicit old/new mapping.

**Do not inherit the old validator unchanged.** Keep camera, provenance, and input-file protection checks. Replace `wood_coordinates == baseline` with a registered wood-remodel audit and attachment validation. Replace exact equality of all vegetation controllers with an explicit distribution-change ledger and a full-forest extent/coverage comparison. Counts alone must never pass a visual gate.

## 2. Baseline and recovery contract — G0

The preferred comparison lineage is the integrated forest `GREEN_TERROR_FOREST_REPAIRED_FINAL.blend`, recorded SHA-256 `02c3132703404571f2f85bbcc16290639d32497ff819433a68639e2441c6a9fd`. Its render records and source archive are retained. Its actual full-forest model is not mounted during preparation of this specification. Do not claim it was reopened.

The surviving local V11 model is `GREEN_TERROR_V11_STRUCTURE.blend`, expected SHA-256 `16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e`. It is a possible recovery input, not an automatic replacement for the preferred baseline. The input audit records its current byte/hash check. [P1, P2]

To close G0, either restore and reopen the exact preferred model, or reconstruct from retained source and give the reconstruction a new identity. If reconstruction is necessary, label it as such and freshly render that control; do not imply byte-identical recovery. Do not use the rejected shinier-leaf candidate as the baseline. Do not compare a new render to an old image made with different settings and call that a controlled A/B test.

Record the executable version, build hash and binary digest; loaded scene hash; every external input hash; OCIO configuration; Cycles and per-view-layer sampling; ray visibility; shader/node-group state; volumes; light transforms and energy; pixel filter; seed; camera sensor, shift, clipping and depth of field; output pixel aspect; and color-management settings. Pin all of this for matched comparisons. The reports used Blender 5.4.0 Alpha build `3fe0f2ab2a29`; this is provenance, not a recommendation to migrate to an alpha. A renderer change requires a new baseline render. [P2]

Snapshot data must be read from the evaluated scene at the requested frame, after any timeline-marker camera overrides have been resolved or disabled. Hash shader dependencies recursively, not just top-level node names. Render one small original-camera test, then reopen the saved baseline in a clean folder with scripts disabled and verify a packed-input render.

**G0 fails** on a missing model, unverified reconstruction, unresolved texture, changed input hash, ambiguous camera, silent renderer change, or a report that describes a different scene than the image. No asset rollout proceeds on a failed G0.

## 3. Asset registry and reference contract

The supplied manifest lists the 56 historically referenced broadleaf, shrub, fern and midstory collection bindings. These are migration targets, not an assertion that they have already been replaced. Discover all evaluated references, including base prototypes, nested choice collections and geometry-node inputs. An improved asset sitting unused in a library is a failed integration.

Create four foreground foliage families initially: a broad climber, a narrow woody-understory leaf, an elliptic sapling/shrub leaf, and a compound fern. Keep palm development separate rather than stretching one of these families into palm leaflets. Assign each individual/vine one family with explicit developmental transitions; do not choose unrelated adult leaf shapes independently at every node.

Each family must have a reference sheet with source/license, uncertain species identity clearly marked, approximate physical scale, upper/lower views, side silhouette, attachment, mature/juvenile examples, and the intended dry or damp condition. At least one photograph per family is held out from construction and used for review. Photographs inform structure; they are not projected backgrounds. Existing authorized scans may remain. New botanical surfaces in this branch are procedural or explicitly authored; scanned replacements require a documented change to that asset's provenance.

Do not infer measured reflectance, biological accuracy or exact leaf dimensions from an uncalibrated photo. Clearly distinguish observed morphology from authored approximations. Real references still need to be selected for this build; this package does not pretend that step is complete.

## 4. Leaf and branch replacement — G1

### Construction

Represent a leaf with explicit boundary curves, a central rib curve, cross-blade curvature controls and a petiole attachment frame. Keep overall droop/twist separate from fine tissue relief. Fit a coherent form first; only then vary family-bounded parameters. Eliminate rectangular face-deletion damage. Cuts and holes must have irregular, refined boundaries with credible thickness and edge treatment.

Use a connected venation graph that drives relief, visible vascular structure and thickness-related response from the same coordinates. Preserve family distinctions in topology; avoid painting a generic rib pattern onto every blade. Runions et al. supplies a useful foundation for branching and looped vein graphs, not an automatic species-correct result. [S1]

Make upper/lower material behavior explicit. Choose either a thin-surface optical model or a finite-thickness shell consistently; avoid accidentally adding two unrelated translucent layers. Model edge thickness only where it resolves. Constrain nonuniform instance transforms: a long narrow approved leaf must not be stretched into the inherited broad template. Use shape/development parameters to vary proportions rather than arbitrary XYZ scaling.

Generate petioles, buds, nodes and secondary shoots as connected plant parts. Every leaf has a stable asset ID, family, maturity, parent branch and attachment frame. Growth damage alters shape and tissue coherently, not independent random values in each material channel.

### Required tests

Render a single leaf upper side, underside and grazing view; a complete branch under soft, lateral and backlighting; and the branch in the original forest close-up. Preserve geometry and camera within each light-triplet comparison. Test at least one alternate pose not used during modeling.

At native size, the outline, tip, attachment, margin, veins and response to light must remain intelligible without heavy blur or invented sharpening. Review without textures, without specular contribution, and with the complete material to isolate the source of an improvement. Specular highlights are not forbidden; unexplained broad highlight bands that conceal weak shape are a rejection reason.

**Technical criteria:** finite coordinates; valid indices; no truly zero-area triangles; no unintended normal flips; correct UV/attribute domains; stable parentage; no accidental gaps at petiole junctions. Proposed hero attachment error is at most `min(0.0002 m, 0.005 × blade length)`. Small but positive-area geometry is flagged for review rather than indiscriminately deleted. Approved blade silhouettes must survive instancing and integration without undeclared deformation.

**Visual rejection:** cutout-like blades; inflated or regularly corrugated surfaces; grid-shaped holes; duplicated distinctive damage patterns in the same foreground; one material response across all ages and sides; an improvement visible only as extra shine; success in the studio but regression in the forest. Technical correctness cannot override a visual rejection.

**G1 passes only** after all four required families have accepted asset and in-context reviews. One strong branch is a partial milestone, not approval to propagate the weak fern or ground leaf family.

## 5. Plant architecture and layout replacement — G2

Build rooted acyclic branching graphs with branch order, age, vigor, direction, resting frame and terminal shoots. Use separate architectural rules for climbers, lateral shrubs, suppressed saplings, taller juveniles, palms and ferns. Vary where and how branching occurs, not just angle/height/color. Self-organizing models offer a light/space-competition foundation; the cited model's demonstrated species are temperate, so tropical architecture still requires independent reference matching. [S2]

Preserve hierarchy when geometry is shared. A leaf cluster's attachment and family must remain stable through LOD selection and wind. Do not use a different random seed to regenerate the plant at every frame.

Create a normalized silhouette sheet with eight independently seeded examples per architecture as an inspection sample, not a minimum realism score. Review the full arrangement at both original cameras: neighboring plants should not repeatedly expose the same distinctive fork, fan, damage pattern or branch-tier ladder.

For distribution, replace purely independent scattering with authored patch fields for available space, root exclusion, slope and coarse light access. Record these as placement heuristics, not validated ecology. Allow shorter or sparser juveniles in selected root zones without hollowing out all off-camera forest. Compare stand extent, height distribution and depth layers before/after; accept changed density only with an explicit composition/ecology rationale.

Trace the evaluated collection references all the way to the generated mesh IDs. Render an ID-debug view to prove the new families are actually used. Any old weak asset still appearing inside a declared replacement region is a failed binding test, not an acceptable legacy detail.

**G2 fails** if the silhouette test still reads as the same plant with different rotations, if full-stand bindings remain stale, if scale changes enlarge every leaf, or if apparent variety comes primarily from camera-dependent deletion or atmospheric concealment.

## 6. Wood, buttresses and attached growth — G3A

Begin with `Tropical_08_wood` and its historically visible collections `Tree prototype 08` / `GT7 | Tree prototype 08`, then include `Tree prototype 02`, `Subcanopy prototype 02` and `Subcanopy prototype 03` where they appear. These are recorded identifiers to re-resolve at G0, not guaranteed names in every reconstruction. [P2]

Reconstruct irregular cross-sections, taper transitions, buttress/root continuity and branch junctions with continuous structural geometry. The surface must remain credible in a neutral gray-material image under grazing light. A bark texture cannot repair a cylindrical silhouette. Bump shading changes the lighting response rather than replacing the modeled form; use geometry/displacement for form that must affect boundaries and contact. [S3]

Create attachment coordinates on the host surface. When the host changes, recompute vines, moss, epiphytes and liana contacts from those coordinates and check them in world space. Do not warp wood alone while leaving its growth suspended or embedded incorrectly. Preserve coherent root/trunk mass instead of independent noisy tubes.

Keep readable exposed bark. Divide growth into films/crusts, patch edges, cushions and occasional small attached plants. Use shared habitat controls to correlate them, with authored patch boundaries rather than a uniform blanket or repeated rosette stamps. Do not require the same coverage percentage everywhere; match the selected references and leave bark structure visible.

**Reject** the wood replacement if its plain geometry still reads as inflated cylinders or cones, if bark is uniformly washed out, if all grooves run with identical frequency, if a root vanishes into the ground without a convincing transition, or if colonies hide the weakness rather than improve their own forms. Fungi must have credible thickness, host attachment, uneven rims and undersides; repetitive decorative bands are not sufficient.

## 7. Ground and litter integration — G3B

Use the terrain, exposed roots and retained deadwood as real supports. Define separate rest forms for intact curled leaves, collapsed leaves, folded fragments, veins and fibers, bark chips and fine humus. Do not treat every dead leaf as the same leathery wrinkled object.

Seat large pieces first, using rigid placement followed by a constrained contact solve on a low-resolution simulation mesh. Transfer that deformation to the detailed surface. Preserve intended folds and edge lengths rather than vertically projecting the entire leaf onto terrain. Drying-related shape changes belong in the rest state, not in numerical contact stretching.

Build support relationships among litter pieces as well as with terrain and wood; reject cycles or ungrounded support chains. Natural lifted margins and curled overhangs are allowed. Evaluate contact specifically at declared support regions, not by insisting every leaf vertex touches the ground.

Proposed hero-study tolerances: support gap at declared contacts no greater than 0.5 mm; penetration at tested contact samples no deeper than 0.2 mm; 95th-percentile edge strain relative to the chosen rest form no greater than 3%, with maximum 10%. These are quality-control tolerances, not calibrated leaf mechanics. Sample triangle interiors and edges, not only centroids; record sample coverage and the worst violations. Sparse checks do not prove globally collision-free contact.

Add smaller debris after large forms settle. Accumulation should follow depressions and obstructions without creating an evenly sprinkled layer. Keep decay/material variation correlated with the selected state. Add fungi and fine roots as connected organisms or fibers, not independent floating noise.

**G3B fails** on stretched litter climbing a vertical root, flattened tan stamps, visible hovering at claimed support points, deep penetrations, uniform crumpling, or a contact statistic that improves while the image gets worse.

## 8. Exact camera and lighting contract

The manifest contains complete recorded world matrices for the two original cameras. Positions below are rounded for reading; use the JSON values for implementation. Camera matrices use Blender's recorded `matrix_world` convention, not a custom forward-axis convention. [P1, P3]

| Test | Camera and placement | Optics and native output |
|---|---|---|
| C01 — original close-up | `04_BARK_AND_LITTER`; location approximately (-3.4, 0.2, 2.4808669) m | Recorded 45 mm lens; 2048 × 1536 |
| C02 — original wide view | `02_ROOTS_AND_UNDERSTORY`; approximately (-3.3, -3.5, 1.0489966) m | Recorded 30 mm lens; 2048 × 1366 |
| C03 — nearby close-up | Copy C01, translate 0.80 m along its local +X/right axis, then aim at the same frozen patch target | 45 mm; 2048 × 1536 |
| C04 — low ground view | From C01, translate 0.40 m local +X; set height to 0.35 m above the locked terrain support directly below; aim at the frozen ground-patch target | 45 mm; 2048 × 1536 |
| A01–A03 — leaf inspection | Upper, underside and grazing poses in a declared asset-local coordinate frame | 70 mm, proposed 36 × 24 mm sensor, horizontal fit; 1600 × 1200 |
| A04 — plant silhouettes | Camera at (3R, -4R, 2R) relative to each plant's bounds center, looking at that center | Orthographic scale 2.2 × bounds diameter; 1600 × 1200 |

For A01–A03, define the specimen's longitudinal direction as +X, lateral direction as +Y and upper-surface direction as +Z. Let R be its bounding-sphere radius about its bounds center. Use camera directions normalize(0,-0.8,2), normalize(0,-0.8,-2) and normalize(0,-2,0.3). Distance is `1.10 × R / sin(min(horizontal_FOV, vertical_FOV)/2)`. Use a deterministic look-at with local camera -Z aimed at the specimen and +Y as up; disable depth of field for diagnosis. These are proposed rig specifications, not recovered historical cameras.

Sensor size/fit, shifts, clipping, pixel aspect and depth of field for C01/C02 must still be read from the selected native baseline at G0. The render records supply matrices and focal lengths but not every field. Do not guess missing fields or inherit new defaults. Freeze target points for C03/C04 from baseline surface hits before rebuilding; do not chase moving candidate geometry with a new target.

Run two independent lighting tracks. The **historical A/B track** preserves the recorded environment, light transforms, exposure 4.199999809265137, AgX / Medium High Contrast, gamma 1.0, and all remaining captured settings. The **readable inspection track** uses a separately frozen soft-light setup applied identically to both sides. Light redesign is allowed only after geometry/material tests pass and must be shown separately.

For the isolated leaf triplet, use one area emitter with fixed color and area. In the upper inspection camera's right/up/back basis, place its center at specimen center + D × normalize(-1,-1,2) for soft light, normalize(-2,0,0.25) for grazing light, and normalize(0,0,-2) for backlight, with D = 4R. Aim it at the specimen. Use size 2R for soft/back and 0.5R for grazing. Set light energy once per family/rig using a neutral reference card, then lock and serialize the value for both versions. This is a reproducible test rig, not a measured daylight reconstruction.

Every final comparison includes full frames and registered native-size crops. Crops are fixed before candidate review. Disabling fog, color textures or gloss is permitted in named diagnostics only; never silently change them between A and B.

## 9. Rendering and convergence contract

Maintain a low-cost preview tier at 960 pixels wide for iteration. It is never final acceptance evidence. Matched reviews use the camera dimensions above, fixed 256 samples initially, adaptive sampling off, identical seeds and identical per-view-layer overrides. This is a starting experiment, not a guarantee of convergence.

Before reviewing fine detail, render fixed native-pixel crops at 256 and 512 samples with independent seed replicates. Raise both baseline and candidate sampling if surface details, contact edges or conclusions change materially. Freeze final settings after this audit. Adaptive sampling may be used for production only with its minimum, maximum and noise threshold recorded; Cycles' noise threshold is not a perceptual realism score. [S4]

Retain scene-linear beauty, albedo, shading-normal and depth data; emit 16-bit display PNGs. Preserve an undenoised comparison and apply the display transform once. Do not export a display-transformed guide as if it were linear albedo. Guides must align in camera, motion, shutter, dimensions and pixel filtering. OIDN guidance calls for matched reconstruction filters, shading-normal features and correct handling of noisy auxiliary inputs; a separate low-sample guide is not automatically clean. [S5]

Prefer full-frame denoising after native pixel-band assembly. Bands must carry consistent film coordinates and sufficient render-filter overlap; compare an overlap/control render for edge bias. Exact row concatenation alone does not prove equivalence. This spec does not require byte-identical stochastic renders; it requires recorded settings and tested differences within the convergence reference. No resizing or hidden smoothing may substitute for native detail.

## 10. Integrated section and forest-wide rollout — G4

Build a 4 × 4 m review section centered on the original trunk/litter grouping, with the actual surrounding forest still participating in shadows, reflections and indirect lighting. This is not a substitute diorama, and the prototype definitions must remain reusable beyond the patch.

First compare old/new geometry with materials fixed; then materials with accepted geometry fixed. Deliver both original cameras plus C03/C04. Include beauty, gray material, surface color, silhouette and native crops that expose the same leaf, bark, attachment and litter problems in both versions. New geometry is permitted to occlude an old landmark only with an explicit composition change review; crowding the defect out of frame is not a pass.

Then propagate accepted definitions through all evaluated bindings. Re-render C01/C02 and one full-stand overview. Test an unoptimized alternate camera path. Verify that the declared replacement region contains no stale base prototypes; verify that distant forest was not removed to save memory. Spatial distribution changes must be independent of the beauty-camera frustum except for documented representation/LOD changes that preserve visibility and lighting contributions.

**Visual decision rule:** each mandatory criterion is `pass`, `reject`, or `not_evaluated`, with a specific image/crop reference and short rationale. Review A/B labels blind where practical at thumbnail scale, normal viewing size and native crops. The user remains the acceptance authority; an internal assessment must be identified as such. The target dimensions of shape, material, contact and repetition must visibly improve over the selected baseline. Any critical regression in another dimension blocks promotion. Do not average a bad leaf away with a higher moss score. Reports, triangle counts and successful native execution do not qualify as visual evidence.

## 11. Resource and reproducibility contract

Measure effective memory limits and peak working set separately for scene load, graph evaluation, geometry/BVH synchronization, transport, denoising and packing. Reducing image resolution does not establish that a geometry-synchronization problem is fixed. Reuse geometry where possible: realizing instances creates unique geometry and increases storage/memory demand. [S6]

Use plant/shoot/frond instancing and controlled variant libraries. Compare any memory optimization against the same images; no silent decimation, texture downsampling, bounces reduction, distant-forest deletion or asset replacement. If the approved appearance exceeds the available worker, report the measured shortfall and use a suitable execution environment rather than claiming that a degraded preview is the final result.

Save immutable stage checkpoints and a manifest after each successful gate. Persist source, dependencies, hashes, render settings, audit data and at least one completed image together. A sandbox path is not a persistence guarantee. Confirm a successful external/Library save when used, or deliver a complete downloadable package; never state that saving succeeded based on an attempted upload alone.

Use asset IDs and source hashes rather than names alone. Check that every saved image is associated with the scene state actually rendered. If motion or deformation is performed in memory, record the evaluated-frame state and script hash as well as the file hash. Reopen the frozen scene in a fresh process and render before release. Native model functionality must not depend on executing untrusted embedded scripts.

## 12. Motion and video release — G5

Only begin the release film after G4 is accepted. First render a two-second/48-frame diagnostic at the intended 24 fps: one fixed-camera foliage motion test and one moving-camera static-forest test. Inspect normal playback, frame stepping and 100% crops. Animated exposure, extra blur and frame blending cannot conceal unstable detail.

Implement rooted hierarchical deformation: trunk/branch compliance, petiole response and leaf flutter use separate scales and remain coupled at their attachments. Root placement pivots stay within 0.01 mm of their rest positions in the numerical audit. This is a procedural motion model unless a physically calibrated solver is actually implemented and validated; do not call it aerodynamic simulation.

The release target is a continuous ten-second move, 1920 × 1080 native, 24 fps, 240 individually rendered frames. Use a collision-checked path through the approved section into the wider forest. Choose and record motion-blur/shutter settings after the diagnostic. Do not infer motion from differing image hashes: path-tracing noise can make stationary frames differ. Record camera matrices and evaluated deformation evidence.

The standard OIDN RT filter is not temporally stable, so per-frame denoising does not prove a stable video. Require temporal inspection and sufficient sampling; use motion-aware/reprojection diagnostics only with disocclusion handling. Never label ordinary geometry motion as a validated temporal solver. [S5]

Reject duplicated-frame padding, optical-flow-generated frames, still-image pans presented as camera motion, discontinuous speed or camera collisions, visible root sliding, rigid-prop rocking of entire plants, LOD popping, crawling texture coordinates and distracting denoising flicker. Decode the final MP4 and verify dimensions, rational frame rate, 240 frame count and 10-second duration. Frame timestamps naturally end before the end-of-stream duration. Inspect the encoded output as well as source frames.

## 13. Release package and implementation handoff

The final package must include a portable `.blend`, reproducible source with relative paths or explicit arguments, asset provenance, the frozen comparison manifest, accepted/rejected review records, four comparison stills at the specified dimensions, relevant diagnostic passes, a contact-sheet index, the native film and its source-frame evidence. A final beauty grade may be supplied in addition to the neutral comparison, never instead of it. No duplicate version labels for materially different models.

Suggested implementation order is: baseline/snapshot capture; leaf geometry and optical test harness; branch graph generator and evaluated-binding audit; wood reconstruction and attachment rebinding; contact solver and litter families; integrated patch comparison; full-stand placement migration; motion rig; convergence/temporal review; release verification. The source-module map is in `acceptance_manifest.json`. It identifies replacement responsibilities, not completed implementations.

**The first actual build deliverable should be the new branch/fern tests and the integrated 4 × 4 m section in the two original cameras plus two nearby views.** Do not announce a new finished whole forest before those images visibly clear the review. A failed experiment remains useful evidence, but it is not a release.

## Sources and provenance

P1: retained integrated-repair `DELIVERY_REPORT.json`, source hash and unresolved-work record.
P2: retained V11 native report, source package, camera-host probes and verified local model hash.
P3: retained integrated-repair render records for `04_BARK_AND_LITTER` and `02_ROOTS_AND_UNDERSTORY`.
S1: Runions et al., *Modeling and visualization of leaf venation patterns* (2005), authors' project page.
S2: Palubicki et al., *Self-organizing tree models for image synthesis* (2009), authors' project page.
S3: Blender manual, Displacement.
S4: Blender manual, Cycles Sampling.
S5: Intel Open Image Denoise documentation, RT filter and feature requirements.
S6: Blender manual, Geometry Nodes Instances.

The source registry contains retrieval date and public URLs. The evidence folder contains copied historical records; those are inputs to this specification, not newly executed V14 tests. `SPEC_PACKAGE_VALIDATION.json` validates only this document package's consistency.
