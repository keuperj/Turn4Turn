# Character asset

`soldier.glb` is the shared comparison soldier, converted from Quaternius
Soldier_Male.fbx in the CC0 Ultimate Animated Character Pack:
https://quaternius.com/packs/ultimatedanimatedcharacter.html

Converted with Three.js FBXLoader/GLTFExporter during asset authoring (not runtime).
Materials converted to rough PBR, dark cloth colors brightened; FBX skinning
weights limited to four per vertex. Source and authoring utility remain under
`static/comparison/`. Babylon.js renders and animates this asset in the game.

The soldier is stylized. Idle/walk clips are authored skeletal animations;
kneeling and prone are adapted poses, not bespoke motion-captured animations.
Enemies use `Ninja_Male.glb`. Civilians select deterministically from six male and
female casual, older, and worker characters using the mission seed and unit ID.
Original civilian and ninja colors are preserved. Soldiers keep `soldier.glb`;
rest-pose planar UVs apply the existing camouflage fabric only to green uniform
materials. Skin, boots and other accessories retain their original materials.
All variants retain independent skeletons, animations and equipped weapons;
civilians hide weapons. Each source is independently normalized to 1.62 units.

`characters.json` records the original pack download URLs and source/output hashes.
Rebuild the seven additional GLBs using the existing Python/Playwright environment:

```sh
.venv/bin/python tools/import_characters.py /tmp/character-fbx --download
.venv/bin/python tests/browser_babylon.py
```

The character assets are **CC0 1.0**, independent of the game's license.

# Transport assets

`transport/` contains 13 local GLBs by **Quaternius**, licensed **CC0 1.0**:

- [Cars Pack](https://quaternius.com/packs/cars.html): two everyday cars, SUV, taxi.
- [Modular Train Pack](https://quaternius.com/packs/modulartrain.html): diesel locomotive,
  steam locomotive, container freight wagon (used as rail transport).
- [Public Transport Pack](https://quaternius.com/packs/publictransport.html): passenger
  train, city bus, school bus, ambulance.
- [Zombie Apocalypse Kit](https://quaternius.com/packs/zombieapocalypsekit.html):
  unarmored pickup and cargo truck, with the original color atlas embedded in each GLB.

Original license notices are in `transport/LICENSE-*.txt`. The Zombie kit's supplied
notice has an unrelated pack heading; its pack page also explicitly states CC0.
The Public Transport pack's CC0 declaration is on its linked pack page.
These assets retain their separate CC0 license, independent of the game's license.

`transport/manifest.json` records source URLs, source/output SHA-256 hashes,
axis corrections, and measured dimensions (width, height, length). Source FBXs
are converted offline with the repository's Three.js loaders/exporter. Public
Transport's old FBX files export white diffuse materials; the conversion assigns
a palette to their original material slots. No runtime FBX parsing or remote asset
requests are needed. The GLBs are loaded once per battlefield and reused for every scene instance.

Rebuild with the existing Python/Playwright environment and Chromium installed:

```sh
.venv/bin/python tools/import_transport.py /tmp/quaternius-transport --download
```

The pipeline corrects source axes, applies **uniform** scale, centers each model,
and places its lowest point at ground level. Cars are 1.22–1.36 units high,
trucks 1.50–2.00, buses 2.50–3.04, ambulance 1.93, and trains 2.44–3.38.
Compare with the game's 1.62-unit standing human and 3-unit building floor.
The tactical grid is approximately one metre per cell; these are stylized models,
not exact full-size engineering replicas. The long high-speed locomotive was
excluded because fitting its length would make it too short beside humans.

Server scene generation stores both `variant` and the explicit `model` ID, chosen
with the scene's seeded RNG. Both renderers use the same catalog and shared loaded
sources. Instance meshes share immutable source materials; scene cleanup removes
clones and their shadows. A further uniform footprint cap supports older/custom
scenes; trains sit 0.085 units above ground on the rails. Imported meshes preserve
structure picking, health labels, fog visibility and destruction. Failed downloads
fall back to procedural props. Existing aircraft, tractors and standalone shipping
containers retain their original geometry; the downloaded rail containers include
bogies and are used only as rail vehicles.

Validation:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/browser_transport.py
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json .venv/bin/python tests/browser_transport.py --webgpu
```

The browser test renders all seven themes, measures/picks every asset, compares
it with humans and a building floor, checks cleanup and fallback, and writes
`/tmp/transport-webgl.png` or `/tmp/transport-webgpu.png`.

# Background scenery

`background/` contains 19 **CC0 1.0** models by Quaternius from the
[Ultimate Nature Pack](https://quaternius.com/packs/ultimatenature.html),
[Farm Buildings Pack](https://quaternius.com/packs/farmbuildings.html), and
[Simple Buildings Pack](https://quaternius.com/packs/simplebuildings.html).
The manifest records source links, original/output hashes, texture atlas bindings,
axis corrections, and normalized dimensions. Original Nature and Farm license
notices are bundled; Simple Buildings declares CC0 on its pack page.

The older Simple Buildings FBXs omit texture bindings. Conversion restores the
supplied 32×32 palette atlases using their existing UVs. Untextured legacy FBX
colors are corrected for the export's color-space conversion. Mesh material groups
are consolidated, scale stays uniform, and origins are centered at ground level.

The game uses shared instances with non-pickable meshes outside the playable grid.
The seeded layout persists through turns, cutaways, and visibility changes; it is
replaced only when the mission seed, theme, or size changes. Day/night horizon fog
follows camera distance so the tactical board stays legible at different zooms.
Ground materials and decorative roads, fields, rails, and runway markings follow
the scenario. Both WebGL and WebGPU use the same scenery. The additional GLBs total
about 3.4 MiB on disk / 0.67 MiB over gzip; no remote requests occur during play.

Rebuild and validate:

```sh
.venv/bin/python tools/import_background.py /tmp/background-fbx --download
.venv/bin/python tests/browser_background.py
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json .venv/bin/python tests/browser_background.py --webgpu
```


### Farm equipment and livestock

The farm uses two tractors (standard and front-loader) from [Kenney Car Kit](https://kenney.nl/assets/car-kit)
and a cow, sheep, and pig from [Quaternius Farm Animal Pack](https://quaternius.com/packs/farmanimal.html).
Both packs are CC0; original licenses are preserved as `transport/LICENSE-farm-vehicles.txt`
and `transport/LICENSE-farm-animals.txt`. The animal download is also available on
[the creator's OpenGameArt page](https://opengameart.org/content/lowpoly-animated-farm-animal-pack).
The bundled GLBs are centered, grounded and uniformly scaled to their collision footprints.
Animals are baked to static rest poses for scenery. They do not wander or simulate livestock behavior.
The transport manifest records per-model authors, sources, dimensions and SHA-256 hashes.
Models load locally, with procedural fallback geometry if loading fails.

Rebuild these models with `.venv/bin/python tools/import_farm.py /tmp/farm-sources`.
The importer downloads the original CC0 archives if they are absent.
