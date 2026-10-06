# Development and technical reference

[Documentation](README.md) · [Back to the game](../README.md)

Python runs the authoritative simulation. Babylon.js renders locally with WebGPU
and an automatic WebGL 2 fallback. Each player has an isolated game session.
The engine, models, textures and sounds are bundled; gameplay uses no runtime CDN.

## Architecture

| Path | Responsibility |
| --- | --- |
| `server.py` | Threaded HTTP server, cookies, capacity, and per-player sessions |
| `tutorial.py` | Fixed training mission, server-validated lessons and harmless targets |
| `static/tutorial.js` | Guided lesson panel and highlighted gameplay controls |
| `game.py` | Authoritative turns, missions, movement, and damage |
| `tactical_ai.py` | Shared enemy intelligence, coordinated routes, independent civilian planning |
| `deployment.py` | Seeded rescue placement with enemy separation and initial concealment |
| `targeting.py` | Attack previews and coordinate targeting |
| `visibility.py` | Fog of war and public-state filtering |
| `fieldcraft.py` | Facing, peeking, healing, and nearby interactions |
| `arsenal.py` | Loadouts, ammunition, explosives, and destruction |
| `scenarios/` | Scenario base classes, registry, generators and shared building logic |
| `static/scenarios/` | Per-scenario renderers, backgrounds and exclusive model assets |
| `world.py` | Compatibility exports for scenario generation |
| `static/app.js` | Browser state, session consent, controls, and preparation UI |
| `static/scene.js` | Babylon.js battlefield and effects |
| `static/characters.js` | glTF character models, animation, and poses |
| `static/environment.js` | Structures, scenery, and visual damage |
| `static/minimap.js` | Fog-aware tactical overview |
| `static/audio.js` | Local effects, ambience, and spatial mixing |

The Python state is authoritative. The renderer handles presentation and input,
but it cannot decide whether an action is legal or alter hidden simulation state.

Rendering updates retain unchanged buildings, props, ladders and character rigs.
Visibility updates rebuild only the two fog meshes; discovery, damage and cutaways
invalidate the affected scenery layers. Moving or turning a character updates its
transform without cloning its skeleton and materials. Scene cleanup also releases
character-owned texture clones while preserving shared source textures.

Maintained Python modules, classes, and functions use docstrings. Maintained
browser modules and named APIs use JSDoc. Bundled third-party libraries under
`static/vendor/` and `static/comparison/vendor/` retain their upstream comments.

## Tactical AI

Enemy sightings are shared in a mission-local contact memory. Observations update
at movement steps, player actions, peeks, and between hostile actions. Contacts
store snapshots rather than references to live units; unseen movement and deaths
do not update them. A contact is discarded when its old position is visibly empty
or after more than three rounds without another sighting. Shared information
helps movement and target assignment; shooting still requires the shooter's own
visibility and weapon range.

Enemies allocate contacts with a distance and commitment score, then assign
support, left-flank and right-flank positions with distinct reserved destinations.
Rescue objectives favor known civilians, but soldiers can also be attacked. Flag
attackers advance on the squad flag; defenders without contacts guard their flag.
Whole-map routes account for walls, doors, fire, stairs and ladders. A bounded
three-phase lookahead compares staging positions and exposure at intermediate
turn endpoints. Objectives persist with a stability bonus and are reconsidered
as teammates discover contacts or change the battlefield. Execution respects AP,
door costs, collisions and reaction-fire deaths. This is heuristic route planning,
not a full adversarial simulation of future player turns.

Each civilian has a separate contact memory populated only by personal sightings.
A width-16 beam search examines three future turns, with up to two movement steps
per turn and waiting as an explicit option. It balances actual path distance to a
ground-level evacuation edge against weapon danger along the route, using sight,
cover and aging remembered threats. Civilians can retreat, detour or wait in
concealment, and reconsider every turn. They cannot open doors. Neither civilian
memories nor enemy assignments are stored on public unit records or sent to the
browser. Terrain is available to both planners; hidden unit positions are not used
as objectives or threat data.

Behavior tests in `tests/test_tactical_ai.py` cover team sightings, hidden contact
memory, independent civilian knowledge, flanking assignments, route detours,
doors, vertical links, hiding, evacuation and public-state privacy.

## Engine comparison

Start the game and visit [http://localhost:8000/comparison/](http://localhost:8000/comparison/)
to view the isolated Babylon.js, PlayCanvas, and Three.js renderer study. It uses
shared assets and camera paths but is separate from the playable simulation. See
the [comparison notes](../static/comparison/README.md).

## Testing

Run the simulation and server tests:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Optional browser checks require Playwright and Chromium:

```sh
python3 tests/browser_smoke.py --browser /snap/bin/chromium
python3 tests/browser_webgpu.py
python3 tests/browser_campaign.py
python3 tests/browser_loading.py
python3 tests/browser_picking.py
python3 tests/browser_picking.py --dpr 1
python3 tests/browser_incremental.py
python3 tests/browser_incremental.py --webgpu
python3 tests/browser_background.py
python3 tests/browser_urban.py
python3 tests/browser_streets.py
python3 tests/browser_interiors.py
python3 tests/browser_babylon.py
python3 tests/browser_audio.py
```

### Browser WebGPU readiness test

With the server running, open [http://localhost:8000/gpu-test](http://localhost:8000/gpu-test).
The page tests the visiting browser's GPU—not the server's—and reports:

- secure-context and WebGPU API availability;
- hardware or fallback adapter identity;
- GPU features and capacity limits;
- device creation, WGSL compute, and canvas rendering; and
- browser-specific recovery hints when a stage fails.

Remote visitors must use HTTPS (start the server with `--https`). A network URL such as
`http://192.168.1.50:8000/gpu-test` is not a secure context and browsers will
not expose WebGPU there. The test does not send detected hardware information
back to the server.

Firefox enables WebGPU by default on supported Windows releases and Apple
silicon Macs. On Linux and Intel Macs, use the current Firefox Nightly build.
For experimental Firefox testing, open `about:config`, set
`dom.webgpu.enabled` to `true`, restart Firefox, and inspect the Graphics
section of `about:support` if the adapter is still unavailable.

To validate WebGPU independently of the game, check that Chromium can acquire a
GPU adapter and complete both compute and canvas-rendering work:

```sh
python3 tools/check_webgpu.py
# Or select a browser explicitly:
python3 tools/check_webgpu.py --browser /snap/bin/chromium
```

The check exits with status 0 when WebGPU works and status 1 when the API,
adapter, device, compute shader, or canvas render is unavailable. Use `--json`
for machine-readable output and `--headed` to diagnose differences between
headless and interactive browser sessions. On Linux, the checker starts
Chromium's full headless implementation with its Vulkan WebGPU backend enabled.

The suite covers game rules, all themes and map sizes, fog-of-war privacy,
interiors, loadout validation, campaign persistence, session isolation, player
capacity, WebGPU and WebGL rendering, animation, and audio fallback behavior.

## Assets and credits

- Port uses bundled CC0 models from [Marina and Yacht Club](https://3dassets.dev/packs/marina-and-yacht-club).
  Source URLs, licenses and hashes are in [the Port manifest](../static/scenarios/port/models/manifest.json);
  rebuild them with `.venv/bin/python tools/import_port.py /tmp/port-sources`.

- Babylon.js is bundled under the [Apache 2.0 license](../static/vendor/BABYLON-LICENSE.txt).
- Character source and conversion notes are documented in
  [static/assets/models/README.md](../static/assets/models/README.md).
- Equipment, landing, campaign, ammunition, and stance images were created for
  the project with OpenAI image generation. Prompt records are stored alongside
  the assets where available.
- Local action and ambience samples were generated with ElevenLabs. See the
  [sound asset guide](../static/sounds/README.md).

There is no music and the game does not contact image or audio generation
services during play.
