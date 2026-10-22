# Native recovery and EXR compatibility

`src/resume.py` and `src/exr_compat.py` are the portable recovery pair, preserved byte-for-byte from the recovered archive. The entry point refuses an incorrect V11 baseline and mismatched resume inputs. It still requires the complete integrated-repair archive and native scene, which are not included in this repository.

`test_compat_unit.py`, `test_exr_native.py` and the native reopen/inspection scripts are retained for later verification. They were parsed, not executed, during publication. Session-specific runners tied to an old worker installation and raw process logs were excluded.

The historical reports describe the recorded reconstruction and 960 × 720 proof. Their old worker paths were normalized to `inputs/historical/`; they do not establish that the native models remain available in this checkout. The exact preserved proof image is in `../media/recovery-proof.png`.

This recovery does not implement the V14 art revision or the requested final forest film.
