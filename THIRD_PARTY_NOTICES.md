# Third-party sources and rights

## Inherited scan assets

The retained project manifest records Poly Haven bark, soil and deadwood inputs under CC0-1.0. It includes artist names, asset URLs, original source-byte checksums and the license URL. The manifest is historical provenance; raw scan textures and native packed models are intentionally not part of this checkout.

- [Poly Haven asset license](https://polyhaven.com/license)
- [Mud Forest](https://polyhaven.com/a/mud_forest), credited to eye-candy.xyz.
- [Dead Tree Trunk 02](https://polyhaven.com/a/dead_tree_trunk_02), photography by Jenelle van Heerden and processing by Rico Cilliers.
- Other inherited bark and forest assets: see `provenance/ORIGINAL_ASSET_MANIFEST.json` for exact attribution and hashes.

## Botanical and algorithmic references

The source packages identify [Runions et al. (2005), Modeling and visualization of leaf venation patterns](https://algorithmicbotany.org/papers/venation.sig2005.html) as methodological inspiration. The authored hybrid implementation is not the paper's complete growth model.

A01's `references/SOURCES.json` records NC State botanical pages and photo credits for morphological observation, including KENPEI (CC BY-SA 3.0) and Alex Popovkin (CC BY 2.0). Those photographs are not redistributed or used as texture bytes in this repository. The asset-gate notes also reference NParks and botanical field imagery. Reference names are not an assertion of species-calibrated reconstruction.

## Runtime dependencies

Blender, NumPy, SciPy, Pillow, Shapely, FFmpeg and other external runtime dependencies are not vendored. Their own terms apply when installed separately.

## Project source and media

Publication does not create a new blanket software or artwork license. Existing rights and third-party terms remain intact; the third-party CC0 statements do not relicense original source code or artwork.
