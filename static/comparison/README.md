# Isolated engine comparison

Open http://localhost:8002/comparison/ after `python3 server.py --port 8002`.
Options: 1 Babylon.js 9.25.0; 2 PlayCanvas 2.22.1; 4 Three.js r169 (the previous game renderer version, with improved shared assets).
This comparison remains separate from gameplay. The main game has since migrated to Babylon.js; its engine files are shared from `/vendor/`.

## What to compare

Use the same camera preset and cutaway in each engine. Drag to orbit and scroll to zoom; switching engines preserves the camera. Inspect the facade, beveled edges, glass, shadows, textured paving, animated soldier, and furnished rooms. Trigger smoke and explosions. Pause for still inspection. Save a screenshot or measurements JSON.

All three WebGL baselines load the exact same GLBs locally, at the same scale, with a 45-degree vertical field of view, 1x render resolution, antialiasing, 2048px sun shadows, and ACES tone mapping. Shared JavaScript controls camera, movement path and deterministic effect positions. Ambient lighting and shadow implementations differ, so their numeric settings are not physically equivalent. This is a representative visual baseline, not each engine's maximum achievable quality.

Frame intervals are rolling median/p95 of up to 240 browser animation frames after a two-second warmup. These include CPU work, browser scheduling and refresh-rate limits; they are not GPU timings. Compare identical viewport sizes on the same machine. Startup includes loading local files, decoding and engine setup; browser caches affect it. Only one renderer runs at a time.

## Scope and limitations

- Shared textured two-storey courtyard building with window frames, glass, multiple rooms, furniture, doors, roof details and floor cutaways.
- Rigged stylized soldier with authored idle/walk/run and other animation clips. This is not a photorealistic character or final game animation set. Walking is a presentation loop, without foot IK or tactical pathfinding.
- Textured delivery truck is a vehicle-scale proxy, not a final military asset.
- Matching procedural smoke/fire puffs test transparent rendering. They are not production volumetric smoke, destruction, or physics.
- No gameplay, LOS/fog-of-war, interactive doors, combat, audio, navigation or migration implemented here.
- Shadows, materials and skeletal animation alone do not solve art quality: final production would still need consistent high-quality meshes, PBR textures, animation blending, lighting and effects.
- Automated checks use Chromium/SwiftShader in this development environment. Measure performance yourself on your normal WebGL hardware; software-rendered timings cannot rank GPU performance.

## Asset and software credits

- `assets/character.glb`: converted from Quaternius **Soldier_Male.fbx**, [Ultimate Animated Character Pack](https://quaternius.com/packs/ultimatedanimatedcharacter.html), CC0. Converted to glTF with Three.js FBXLoader/GLTFExporter; materials converted to rough PBR and dark cloth colors brightened. FBX import limits skinning to four weights per vertex. Source FBX retained for reproducibility.
- `assets/CesiumMilkTruck.glb`: © 2017 Cesium, CC BY 4.0, unmodified file from [Khronos glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CesiumMilkTruck). Display scale/orientation adjusted. See `CesiumMilkTruck-LICENSE.md` and `Cesium-Trademark.txt`; the logo has a separate trademark notice.
- `assets/CesiumMan.glb`: unused fallback, © 2017 Cesium, CC BY 4.0. See its accompanying license.
- `assets/courtyard.glb`: generated specifically for this project by `author.js`, incorporating the project's existing generated `concrete.png` and `ground.png` textures.
- Babylon.js and loaders: Apache 2.0, `vendor/BABYLON-LICENSE.txt`.
- PlayCanvas engine: MIT, `vendor/PLAYCANVAS-LICENSE.txt`.
- Three.js and matching addons: MIT, `vendor/THREE-LICENSE.txt`. The core module remains `/vendor/three.module.js`.
- fflate (FBX authoring dependency): MIT; copyright/license notice is included in `vendor/libs/fflate.module.js`.

## Development

`author.html` provides `exportScene()` and `exportCharacter()` for rebuilding the shared GLBs. The files are prebuilt; authoring is not required to view the comparison. Engine adapters expose the same camera/cutaway/motion/update interface. The parent page runs only one renderer iframe; all runtime libraries and assets are vendored and no remote services are used.

Run `python3 tests/browser_comparison.py` with the local server running on port 8002. The test checks all three engines load, controls work, animation time advances/pauses, effects trigger, and captures download without external requests. It writes screenshots under `/tmp/comparison-*` for visual inspection.

## WebGPU enhanced study

Choose **HQ · WebGPU enhanced**, or open `/comparison/?engine=webgpu`. This explicitly requires WebGPU on HTTPS/localhost; unsupported devices display a clear error and can select any existing WebGL baseline. It never silently labels a fallback as WebGPU.

The enhanced view retains the shared model placements, camera presets, animation paths and cutaway controls, but intentionally increases the art and rendering workload: 4096px filtered shadows, 4x pipeline MSAA plus FXAA, restrained HDR bloom, generated limestone albedo and procedural micro-normal detail, facade quoins and drainage, window trim, HVAC louvers and antenna, furnished desks and binders, truck mirrors/steps/rack, animated torso gear and knee pads, supply crates, trees, streetlights and distant buildings with atmospheric fog. The source GLBs and three WebGL baseline render settings are unchanged. Added building detail follows the original cutaway hierarchy.

This is a **quality comparison**, not an equal-workload engine benchmark. Exports identify backend and quality profile. All profiles retain 1x comparison resolution. The game also uses the shared lighting/material profile, animated gear and additional prop/building/background detail only when its existing WebGPU initialization succeeds; its WebGL fallback retains the previous art path. These remain stylized base models, not replacement photorealistic scanned figures or vehicles.

Texture provenance and exact generation prompt: [`../assets/PROMPTS.md`](../assets/PROMPTS.md), `limestone-webgpu-v1.png`. All assets run locally with no generation service called during gameplay.

Validation: `python3 tests/browser_comparison.py --engine webgpu` uses Chromium with Vulkan enabled. On machines needing software Vulkan, select the installed lavapipe ICD with `VK_ICD_FILENAMES`. Software-rendered timing is not representative of hardware performance. Run the default comparison test separately for the three WebGL baselines, and `tests/browser_webgpu.py` for gameplay startup/fallback.

### Second detail pass

The enhanced study now includes two separately authored cars: a short red hatchback and a longer blue estate with roof rails. They have distinct body profiles and generated paint textures, inset glazing, bumpers, lights, grilles, mirrors, door seams and alloy wheels. Both are procedural meshes authored for this project, not downloaded branded vehicle assets. Use **Vehicles & street** to inspect them.

Background facades now use generated limestone/brick materials, window sills, mullions, floor bands, downpipes, doors and rooftop equipment. The street includes a bicycle, dumpster, pallets, hydrant, drains and barriers. **Furniture detail** with the ground-floor cutaway reveals chairs, shelves and individual books, a sofa, rug, table, kitchenette, desk lamp, keyboard, mug and papers; the upper floor adds a bed and blanket. All interior additions inherit their floor's visibility.

Trees use generated bark, tapered branching geometry and alpha-tested leaf sprays with veins, merged into two meshes per tree. The WebGPU effect pool contains 148 smoke/fire/spark/debris/dust elements plus a brief local light. Effects are deterministic functions of simulation time and obey pause/reset. They are layered raster particles, not volumetric fluid simulation. Shared generated timber, brick, tree and smoke improvements also apply to the game's WebGPU path, along with the enhanced blast effect; WebGL keeps the original implementation.

Five new albedo textures are in `/assets/{brick,timber,bark,car-red,car-blue}-webgpu-v2.png`. Exact built-in image generation prompts and provenance are in `../assets/PROMPTS.md`. Runtime leaf masks and smoke opacity textures are procedural.
