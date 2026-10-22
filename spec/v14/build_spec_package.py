"""Assemble a planning package from retained records; never executes Blender."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path('inputs/historical/GREEN_TERROR_V14_SPEC')
INPUTS = ROOT / 'evidence_inputs'
INPUTS.mkdir(parents=True, exist_ok=True)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(name: str, data: object) -> None:
    (ROOT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def zip_json(package: str, member: str, dest: str) -> dict:
    with zipfile.ZipFile('inputs/historical/' + package) as z:
        raw = z.read(member)
    (INPUTS / dest).write_bytes(raw)
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError(f'{member} did not contain a JSON object')
    return obj

close = zip_json('GREEN_TERROR_INTEGRATED_REPAIR_RENDERS.zip',
                 'GREEN_TERROR_ASSET_REPAIR/renders/09_FOREST_CLOSEUP_FINAL.json',
                 'historical_closeup_render.json')
wide = zip_json('GREEN_TERROR_INTEGRATED_REPAIR_RENDERS.zip',
                'GREEN_TERROR_ASSET_REPAIR/renders/10_FOREST_UNDERSTORY_FINAL.json',
                'historical_understory_render.json')
bindings = zip_json('GREEN_TERROR_INTEGRATED_REPAIR_SOURCE.zip',
                    'GREEN_TERROR_ASSET_REPAIR/evidence/forest_integration.json',
                    'historical_forest_integration.json')
contract = zip_json('GREEN_TERROR_INTEGRATED_REPAIR_SOURCE.zip',
                    'GREEN_TERROR_ASSET_REPAIR/evidence/final_scene_contract.json',
                    'historical_scene_contract.json')
report_path = Path('inputs/historical/GREEN_TERROR_ASSET_REPAIR/DELIVERY_REPORT.json')
if report_path.is_file():
    (INPUTS / 'historical_delivery_report.json').write_bytes(report_path.read_bytes())

sources = {
    'retrieved_date': '2026-10-21',
    'scope': 'Public documentation and research, not evidence of a native V14 implementation.',
    'S1': {'title': 'Modeling and visualization of leaf venation patterns',
           'authors': 'Runions et al.', 'year': 2005,
           'url': 'https://algorithmicbotany.org/papers/venation.sig2005.html'},
    'S2': {'title': 'Self-organizing tree models for image synthesis',
           'authors': 'Palubicki et al.', 'year': 2009,
           'url': 'https://algorithmicbotany.org/papers/selforg.sig2009.html'},
    'S3': {'title': 'Blender Manual: Displacement',
           'url': 'https://docs.blender.org/manual/en/latest/render/materials/components/displacement.html'},
    'S4': {'title': 'Blender Manual: Cycles Sampling',
           'url': 'https://docs.blender.org/manual/en/latest/render/cycles/render_settings/sampling.html'},
    'S5': {'title': 'Intel Open Image Denoise documentation',
           'url': 'https://www.openimagedenoise.org/documentation.html'},
    'S6': {'title': 'Blender Manual: Geometry Nodes Instances',
           'url': 'https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/instances.html'},
}
write_json('sources.json', sources)

v11 = Path('inputs/historical/GREEN_TERROR_V11/GREEN_TERROR_V11_STRUCTURE.blend')
preferred = Path('inputs/historical/GREEN_TERROR_ASSET_REPAIR/GREEN_TERROR_FOREST_REPAIRED_FINAL.blend')
expected_v11 = '16b3a638e8392e298e7169da8d752ef2153d8fab84b9416e8382870bf7eaf17e'
expected_preferred = '02c3132703404571f2f85bbcc16290639d32497ff819433a68639e2441c6a9fd'
actual_v11 = sha256(v11) if v11.is_file() else None
actual_preferred = sha256(preferred) if preferred.is_file() else None
if actual_v11 is not None and actual_v11 != expected_v11:
    raise RuntimeError('Surviving V11 model hash differs from recorded reference.')

def baseline_entry(path: Path, expected: str, actual: str | None) -> dict:
    return {'recorded_path': str(path), 'expected_sha256': expected,
            'currently_present_at_path': path.is_file(), 'actual_sha256': actual,
            'byte_identity_checked': actual is not None,
            'byte_identity_matches': actual == expected if actual is not None else None,
            'native_reopen_performed_for_spec': False,
            'note': 'Path check is local to specification preparation; absence is not a Library-wide search.'}

cameras = []
for key, d, dims in [('C01', close, (2048,1536)), ('C02',wide,(2048,1366))]:
    cameras.append({'id': key, 'name': d['camera'],
                    'status': 'historical_record_imported_not_native_reopened',
                    'source_record': 'evidence_inputs/' + ('historical_closeup_render.json' if key=='C01' else 'historical_understory_render.json'),
                    'recorded_scene_sha256': d['scene_sha256'], 'world_matrix': d['camera_matrix'],
                    'lens_mm': d['lens_mm'], 'proposed_review_resolution': list(dims),
                    'frame': 1, 'recorded_display': {k:d[k] for k in ('exposure','view_transform','look','gamma')},
                    'must_capture_at_G0': ['sensor_width','sensor_height','sensor_fit','shift_x','shift_y',
                                          'clip_start','clip_end','dof','pixel_aspect','active_camera_after_marker_evaluation'],
                    'complete_camera_snapshot': False})

criteria = {
    'G0': ['Verified baseline identity or explicitly labeled reconstruction', 'Fresh control render from reopened baseline',
           'Complete camera/light/render/dependency snapshot', 'Protected original bytes and durable checkpoint'],
    'G1': ['Reference-matched outlines and growth-family identity', 'Upper/lower/grazing leaf tests',
           'Soft/side/backlight branch tests', 'No cutout, inflated, corrugated or rectangular-hole failure',
           'No unapproved proportion change on instancing', 'All four foliage families pass in-context inspection'],
    'G2': ['Rooted acyclic plant graphs', 'Distinct growth-form silhouettes', 'Stable identities across frames and LOD',
           'Evaluated references prove actual replacement use', 'No camera-hidden repetition or density loss'],
    'G3A': ['Convincing gray-material buttress, trunk and junction form', 'Host reattachment follows remodeling',
             'Readable bark with non-stamped attached growth', 'Fungi thickness, attachment and undersides accepted'],
    'G3B': ['Support gaps and penetrations within declared hero tolerances', 'Rest-shape strain audit within limits',
             'No stretched-root, hovering, flat-stamp or uniform-crumple artifacts',
             'Sampled collision coverage disclosed; no false global proof'],
    'G4': ['4x4m section wins in C01 and C03', 'Wide view C02 improves; low view C04 holds up',
           'No critical regression in shape, material, contact or repetition',
           'Full-stand migration has no stale bindings', 'No hidden render-budget degradation'],
    'G5': ['48-frame motion diagnostics pass', '240 native frames at 1920x1080 and 24 fps',
           'Root stability and deformation hierarchy validated', 'No interpolation, frame padding, sliding or popping',
           'Temporal source and encoded-output review passes', 'Final duration and decoded frame count verified']
}
manifest = {
    'schema': 'green-terror-rebuild-contract/1.0',
    'project': 'GREEN TERROR', 'revision_label': 'V14 specification', 'date': '2026-10-21',
    'status': 'specified_not_implemented', 'native_v14_executed': False,
    'new_scene_created': False, 'new_images_rendered': False, 'new_video_encoded': False,
    'threshold_policy': 'Proposed project QA tolerances; not measured biological truths or guarantees of photorealism.',
    'baseline': {'selected': None, 'locked': False,
                 'preferred': baseline_entry(preferred,expected_preferred,actual_preferred),
                 'surviving_recovery_input': baseline_entry(v11,expected_v11,actual_v11),
                 'automatic_fallback_allowed': False,
                 'historical_renderer': {'version':'5.4.0 Alpha','build_hash':'3fe0f2ab2a29','binary_digest':None},
                 'missing_required_evidence': ['Native reopened baseline selection','Complete render/camera snapshot','Selected photographic reference sheets']},
    'constraints': {
        'renderer': 'Native Blender Cycles', 'image_generation_allowed': False,
        'generated_texture_substitutes_allowed': False, 'frame_interpolation_allowed': False,
        'still_pan_as_camera_motion_allowed': False, 'upscaling_as_native_resolution_allowed': False,
        'existing_authorized_scans_allowed': True, 'numerical_raytracing_denoising_allowed': True,
        'original_files_read_only': True, 'preserve_named_comparison_cameras': True,
        'preserve_exact_wood_coordinates': False, 'preserve_all_18940_root_positions_and_counts': False,
        'wood_attachment_rebinding_required': True, 'placement_change_ledger_required': True,
        'no_unreported_camera_frustum_culling': True, 'no_unreported_quality_reduction': True,
        'visual_approval_separate_from_technical_checks': True,
    },
    'asset_scope': {
        'foliage_families': ['broad_climber','narrow_woody_understory','elliptic_sapling_shrub','compound_fern'],
        'separate_architectures': ['climber','lateral_shrub','suppressed_sapling','tall_juvenile','palm','fern'],
        'historical_plant_collection_bindings': [
            {'family':r['family'],'collection':r['collection'],'migration_status':'not_started'}
            for r in bindings['prototype_bindings']],
        'hero_host_names_to_resolve': ['Tropical_08_wood','Tree prototype 08','GT7 | Tree prototype 08',
                                      'Tree prototype 02','Subcanopy prototype 02','Subcanopy prototype 03'],
        'ground_collections_to_resolve': ['DETAIL | Litter prototype 00..23',
                                        'DETAIL | Scan tree_stump_01','DETAIL | Scan dead_tree_trunk_02'],
        'integration_patch_dimensions_m': [4.0,4.0],
        'reference_sheets_selected': False,
    },
    'camera_contract': {
        'inherited': cameras,
        'extra': [
            {'id':'C03','base':'C01','translation_camera_local_right_m':0.8,
             'aim':'Frozen baseline patch target','lens_mm':45.0,'resolution':[2048,1536],
             'target_world':None,'status':'proposed_not_instantiated'},
            {'id':'C04','base':'C01','translation_camera_local_right_m':0.4,
             'height_above_locked_terrain_m':0.35,'aim':'Frozen ground patch target',
             'lens_mm':45.0,'resolution':[2048,1536],'target_world':None,'status':'proposed_not_instantiated'},
        ],
        'asset_rig': {
            'axis_convention': {'X':'leaf_longitudinal','Y':'lateral','Z':'upper_surface'},
            'camera_forward_axis':'-Z', 'camera_up_axis':'+Y',
            'directions': {'A01':[0,-0.8,2], 'A02':[0,-0.8,-2], 'A03':[0,-2,0.3]},
            'normalize_direction_vectors':True,'lens_mm':70.0,'sensor_mm':[36.0,24.0],
            'sensor_fit':'HORIZONTAL','resolution':[1600,1200],
            'distance_rule':'1.10 * bounds_sphere_radius / sin(min(fov_x,fov_y)/2)',
            'depth_of_field':False,
            'silhouette_pose':{'offset_in_bounds_radii':[3,-4,2], 'projection':'ORTHO',
                               'ortho_scale_bounds_diameters':2.2},
            'status':'specified_not_instantiated'
        }
    },
    'lighting': {'historical_AB':'Capture and hold exact baseline rig; no side-specific edits',
                 'neutral_AB':'Separate readable inspection rig, serialized and identical on A and B',
                 'production_light_redesign':'Separate experiment after geometry/material gates',
                 'leaf_triplet':{'source':'area','offset_in_upper_camera_basis':{
                     'soft':[-1,-1,2], 'side':[-2,0,0.25], 'back':[0,0,-2]},
                     'normalize_offsets':True,'distance_bounds_radii':4,
                     'size_bounds_radii':{'soft':2,'side':0.5,'back':2},
                     'energy':'Calibrate once on a neutral card, serialize, lock for both A and B',
                     'energy_value':None}},
    'render_contract': {
        'preview_width_px':960,'preview_can_pass_visual_gate':False,
        'review_initial_fixed_spp':256,'review_adaptive_sampling':False,
        'convergence_crop_spp':[256,512],'independent_seed_replicates_required':True,
        'convergence_action':'Increase both sides if details or conclusions still materially change; no automatic pass at 512 spp',
        'color_master':'scene_linear_EXR','display_output':'16bit_PNG',
        'required_channels':['beauty','albedo','shading_normal','depth'],
        'denoiser':'OIDN or declared compatible native denoiser',
        'feature_filter_and_projection_match':True,'noisy_features_never_declared_clean':True,
        'retain_undenoised_for_review':True,'single_display_transform':True,
        'band_assembly':'Native film coordinates plus filter margins; full-frame denoise; overlap-control test required'
    },
    'technical_tolerances': {
        'hero_attachment_m':'min(0.0002, 0.005 * blade_length_m)',
        'hero_declared_support_max_gap_m':0.0005,
        'hero_sampled_penetration_max_m':0.0002,
        'contact_rest_edge_strain_p95_max':0.03,'contact_rest_edge_strain_max':0.10,
        'root_motion_max_m':0.00001,
        'collision_scope':'Sampled hero surfaces, including edges/interiors; not proof of full-forest nonintersection',
        'nonfinite_coordinates_allowed':0,'invalid_indices_allowed':0,'exact_zero_area_faces_allowed':0,
        'small_positive_area_faces':'Scale-aware audit; never delete solely to inflate pass count'
    },
    'gates': [ {'id':gid,'status':'not_evaluated','criteria':reqs,'technical_pass':None,
                'visual_pass':None,'user_approved':None,'evidence':[]} for gid,reqs in criteria.items()],
    'release_video': {'status':'not_started','width':1920,'height':1080,'fps_num':24,'fps_den':1,
                      'duration_seconds':10,'native_frame_count':240,'frames':[1,240],
                      'diagnostic_duration_seconds':2,'diagnostic_frame_count':48,
                      'camera_motion_and_deformation_evidence_required':True,
                      'motion_model':'Rooted hierarchical procedural model unless calibrated solver is actually validated',
                      'temporal_review_required':True,'standard_OIDN_RT_assumed_temporally_stable':False,
                      'no_static_noise_hash_as_motion_proof':True},
    'code_handoff': {
        'baseline_snapshot.py':'New complete evaluated camera/light/render/texture/dependency snapshot and provenance lock',
        'make_atlases.py':'Reference-bounded vein/tissue mapping from the same leaf surface coordinates',
        'repair_geometry.py':'Replace weak leaf, fern and rest-litter construction, not shader-only variation',
        'refine_architecture.py':'Distinct rooted branch grammars; stable identity and per-family development',
        'integrate_forest.py':'Evaluated base/variant binding migration plus explicit placement-change ledger',
        'repair_climber_bindings.py':'Keep family proportions; reproject attachments after host remodeling',
        'wood_rebuild.py':'New continuous buttress/junction reconstruction and attachment coordinates',
        'litter_contact.py':'New or revised shape-preserving support/contact solver with disclosed sample coverage',
        'validate_scene_contract.py':'Replace old exact-wood/root invariants; preserve cameras and original inputs',
        'render_banded.py':'Match native film coordinates and filter margins; validate seams against full/crop control',
        'denoise_linear_asset.py':'Audit guide definitions/noise/filter alignment; retain raw beauty',
        'review_gate.py':'Record human visual decisions separately from numerical pass flags',
        'wind_hierarchy.py':'Proposed parent-coupled deformation and root invariance test',
        'verify_release.py':'Clean-directory native reopen, provenance match, decode video and preserve rejection records',
    },
    'release_state': {'implementation_complete':False,'visual_acceptance_complete':False,
                      'renders_complete':False,'video_complete':False}
}
write_json('acceptance_manifest.json',manifest)

review = {
    'schema':'green-terror-visual-review/1.0', 'status':'not_evaluated',
    'reviewer':None, 'reviewer_role':None,
    'reviewer_roles':['user','internal_visual_reviewer','external_reviewer'],
    'baseline_scene_sha256':None,'candidate_scene_sha256':None,
    'gate':None,'camera':None,'image_pair':{'baseline':None,'candidate':None},
    'labels_blinded':None, 'matched_controls_verified':False,
    'viewing_scales':['thumbnail','normal','native_100_percent'],
    'criteria':[{'name':c,'decision':'not_evaluated','baseline_crop':None,'candidate_crop':None,
                 'reason':None,'critical_regression':None} for c in [
                     'leaf_shape_and_attachment','material_response','plant_architecture',
                     'wood_macroform','attached_growth','litter_contact_and_decay','depth_and_distribution']],
    'decision':None,'allowed_decisions':['accept','reject','not_evaluated'],
    'technical_status_does_not_set_visual_status':True,
    'user_approval':None,'next_required_change':None
}
write_json('VISUAL_REVIEW_TEMPLATE.json',review)

source_packages = [Path('inputs/historical/GREEN_TERROR_INTEGRATED_REPAIR_SOURCE.zip'),
                   Path('inputs/historical/GREEN_TERROR_INTEGRATED_REPAIR_RENDERS.zip'),
                   Path('inputs/historical/GREEN_TERROR_V11_STRUCTURAL_REBUILD.zip')]
write_json('INPUT_AUDIT.json',{
    'scope':'Files and records inspected while drafting specification; no Blender execution',
    'native_v14_scene_created':False,
    'source_packages':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha256(p)} for p in source_packages],
    'local_model_checks':manifest['baseline'],
    'imported_camera_records':len(cameras),'historical_collection_bindings':len(bindings['prototype_bindings'])
})

(ROOT/'README.md').write_text('''# GREEN TERROR V14 spec package

Start with `REBUILD_SPEC.md`. `acceptance_manifest.json` contains exact recorded camera matrices, the historical collection binding inventory, proposed QA tolerances and unexecuted gate states. `VISUAL_REVIEW_TEMPLATE.json` separates human visual decisions from technical validation.

`evidence_inputs/` holds historical records copied from retained project archives. The paths in those records describe previous executions and are not proof that those outputs exist in this runtime. `INPUT_AUDIT.json` identifies what was checked locally. `sources.json` names external primary documentation.

No new Blender scene, image or video was built by this package. No acceptance gate has been passed. The manifest is an implementation contract, not an executable scene builder or an already-tested acceptance runner.

The main design change is explicit: wood geometry and repetitive small-plant placement are allowed to change. Camera/provenance locks remain. Every approved replacement must win an in-context image review before forest-wide replication.
''')

checks = []
def check(name: str, condition: bool) -> None:
    checks.append({'name':name,'passed':bool(condition)})
    if not condition:
        raise AssertionError(name)

check('Two historical cameras imported',len(cameras)==2)
check('Camera scene record matches preferred historical scene',all(c['recorded_scene_sha256']==expected_preferred for c in cameras))
check('Recorded lens lengths imported',cameras[0]['lens_mm']==45 and cameras[1]['lens_mm']==30)
for c in cameras:
    matrix=c['world_matrix']
    check(c['id']+' matrix shape and finite values',len(matrix)==4 and all(len(r)==4 for r in matrix) and all(math.isfinite(x) for row in matrix for x in row))
    check(c['id']+' homogeneous row',matrix[-1]==[0,0,0,1])
    errs=[abs(sum(matrix[k][i]*matrix[k][j] for k in range(3))-(1.0 if i==j else 0.0)) for i in range(3) for j in range(3)]
    check(c['id']+' rotation orthonormal within source precision',max(errs)<1e-5)
check('56 historical bindings preserved in manifest',len(manifest['asset_scope']['historical_plant_collection_bindings'])==56)
check('All gates deliberately not evaluated',all(g['status']=='not_evaluated' and g['technical_pass'] is None and g['visual_pass'] is None for g in manifest['gates']))
check('No native completion claimed',not any(manifest[k] for k in ('native_v14_executed','new_scene_created','new_images_rendered','new_video_encoded')))
check('Ten seconds at 24 fps gives 240 native frames',manifest['release_video']['duration_seconds']*manifest['release_video']['fps_num']/manifest['release_video']['fps_den']==manifest['release_video']['native_frame_count'])
check('Same historical transform/exposure for both cameras',cameras[0]['recorded_display']==cameras[1]['recorded_display'])
check('Original file references never treated as a new completed scene',manifest['baseline']['locked'] is False and manifest['baseline']['selected'] is None)
for f in ROOT.rglob('*.json'):
    json.loads(f.read_text())
check('All JSON parse successfully',True)
write_json('SPEC_PACKAGE_VALIDATION.json',{'passed':True,'scope':'Document/package structure, imported-record consistency and JSON parsing ONLY; not native rendering or visual quality',
                                        'checks':checks,'native_blender_tests_executed':0,'visual_reviews_performed':0})
archive=Path('inputs/historical/GREEN_TERROR_V14_REBUILD_SPEC.zip')
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(ROOT.rglob('*')):
        if p.is_file():z.write(p,'GREEN_TERROR_V14_SPEC/'+str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:
    if z.testzip() is not None:raise RuntimeError('Archive CRC check failed')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,
                  'spec_words':len((ROOT/'REBUILD_SPEC.md').read_text().split()),
                  'checks_passed':len(checks), 'new_renders':0,'new_native_models':0},indent=2))
