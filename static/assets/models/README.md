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
Team tints and separately modeled equipped weapons are applied at runtime.

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
