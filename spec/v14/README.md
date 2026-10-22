# GREEN TERROR V14 spec package

Start with `REBUILD_SPEC.md`. `acceptance_manifest.json` contains exact recorded camera matrices, the historical collection binding inventory, proposed QA tolerances and unexecuted gate states. `VISUAL_REVIEW_TEMPLATE.json` separates human visual decisions from technical validation.

`evidence_inputs/` holds historical records copied from retained project archives. The paths in those records describe previous executions and are not proof that those outputs exist in this runtime. `INPUT_AUDIT.json` identifies what was checked locally. `sources.json` names external primary documentation.

No new Blender scene, image or video was built by this package. No acceptance gate has been passed. The manifest is an implementation contract, not an executable scene builder or an already-tested acceptance runner.

The main design change is explicit: wood geometry and repetitive small-plant placement are allowed to change. Camera/provenance locks remain. Every approved replacement must win an in-context image review before forest-wide replication.
