# Adding a scenario

Scenarios are discovered at server startup. Add a Python package and a matching
static folder with the same stable ID, then restart the server. No edits to
`world.py`, the HTTP routes, the menu, or the browser dispatcher are needed.
Only install trusted Python/JavaScript addons: scenario discovery executes code.

```text
scenarios/
  base.py                    Scenario and reusable LotScenario contracts
  registry.py                Discovery, validation and ordered registration
  assets.py                  Combined model catalog
  buildings.py               Shared rooms, walls, portals and floor access
  common.py                  Edge keys and shared prop footprints
  courtyard/
    __init__.py
    scenario.py              Exports SCENARIO
    layout.py                Optional layout/prop helpers
static/
  scenarios/
    registry.js              Loads modules advertised by /api/scenarios
    courtyard/
      index.js               Browser hooks and background profile
      scene.js               Optional ground/building/prop rendering
      background.js          Optional background placement
      models/                Optional manifest.json, GLBs and licenses
```

Existing scenarios use this structure. Shared textures, characters, background
buildings/vegetation and road vehicles stay under `static/assets/`; shared
rendering helpers stay in `static/`. `world.py` retains compatibility exports for
existing consumers, but new code should import `scenarios` or `scenarios.common`.

## Minimal working addon

Create an empty `scenarios/courtyard/__init__.py`, then
`scenarios/courtyard/scenario.py`:

```python
from scenarios.base import LotScenario


class CourtyardScenario(LotScenario):
    id = 'courtyard'
    order = 100
    theme = dict(label='Courtyard', names=['WORKSHOP'], ground='#8c9c71',
                 road='#42494b', wall='#b6a290', props=[])

    def plan(self, game):
        n = game.size
        game.tiles = [['grass'] * n for _ in range(n)]
        lots = [dict(x=x, y=y, width=4, depth=4)
                for x in (2, n-7) for y in (3, n//2)]
        return lots, None


SCENARIO = CourtyardScenario()
```

Create `static/scenarios/courtyard/index.js`:

```javascript
export const profile = {
  color: '#8c9c71', sky: '#a3b2b5', texture: 'terrain-mixed-v2.webp'
};
```

Restart `python3 server.py` and select **Courtyard** in the scenario menu. This
uses the common ground, building, room and traversal renderers and a plain grassy
background. The example is exercised through `Game` in `tests/test_scenarios.py`.

IDs must match package names and use lowercase letters, digits and underscores,
starting with a letter. `random` is reserved. Duplicate IDs fail startup.
Discovery expects a concrete `Scenario` instance named `SCENARIO` and a browser
`index.js`. Definitions are sorted by `(order, id)`; builtins keep orders 0–6 to
preserve existing random-theme selection. Adding an addon changes the random
selection pool; explicit theme/seed pairs remain deterministic.

## Python hooks

Use `LotScenario` for rectangular, enterable buildings. Its `plan(game)` sets
terrain and returns `(lots, context)`. Each lot has integer `x`, `y`, `width` and
`depth`, and may include custom metadata. Keep lots inside the map, at least two
tiles wide/deep, separated with accessible entrances, and clear of the final four
rows used for deployment. Supported sizes are 24, 30 and 40.

Override only the hooks needed:

| Hook | Purpose |
| --- | --- |
| `building_name(game, index)` | Choose a building label |
| `building_levels(game, lot, index, archetype)` | Choose floor/roof height |
| `configure_building(game, building, lot, index)` | Set appearance and custom roles |
| `wall_archetype(building, original)` | Select the window layout policy |
| `double_door(...)`, `portal_kind(...)` | Customize exterior portals |
| `open_interior(building)` | Omit internal partitions |
| `place_props(game, context)` | Place props and update blocked cells |
| `scenery_details(game, context)` | Add public renderer metadata |

See `base.py` for exact signatures and `farm/scenario.py` for a compact example.
Shared building generation retains legacy RNG draws to preserve existing seeds.
Use `game.rng` for all gameplay randomness. Registered instances are shared among
player sessions: never store game-specific mutable state on `self`. Keep it on
`game` or in the context returned by `plan`.

For nonstandard layouts, derive directly from `Scenario` and implement
`generate(game)`, as the factory does. Populate `tiles`, `heights`, `surfaces`,
`buildings`, `walls`, `blocked`, `portals`, `ladders`, `stairs`, `props`, `road_x`,
`cross_y` and `scenery`. Coordinates are `(x, y, level)`; each visual level is three
metres high. `walls` uses canonical `edge_key` pairs. Traversal links must have
walkable, unblocked endpoints; all upper floors need stairs or ladders. Explicit
surfaces must match visible floor holes. Props need unique IDs, positions,
footprints, variants and matching blocked cells. `scenery` includes the theme ID,
road coordinates and theme palette. See `factory/layout.py` for the full contract
and its connectivity validator.

## Browser hooks

`index.js` must export `profile` (`color`, `sky`, optional shared texture filename
and background `height`, default `-0.025`). All other exports are optional:

| Export | Contract |
| --- | --- |
| `ground(view, state)` | Add scenario ground details |
| `building(view, building, state)` | Return true after fully rendering a custom building; otherwise use the shared renderer |
| `prop(view, prop, group)` | Return truthy after rendering a custom prop; otherwise use imported models or the shared fallback |
| `background(state, rng)` | Called with the shared `BackgroundAssets` instance as `this`; use its `plane`, `material`, `add`, `root` and `view` helpers |

Use relative imports (`../../rendering.js`, `../../surfaces.js`) or re-export
hooks from sibling files. The browser loads registered modules before
`Battlefield.ready` resolves. Honor fog/unknown tiles, picking ownership and
cleanup, and support both Babylon WebGL and WebGPU. Background decoration must
stay outside the playable grid and must not be pickable. The airport's ground and
background modules demonstrate geometry continuing across the board boundary.

## Models and other assets

Place exclusive assets under `static/scenarios/<id>/`. For imported prop models,
create `models/manifest.json` with a `models` array. Entries use the existing
catalog schema: globally unique `id`, `kind`, local `file`, metre-scale
`dimensions: [width, height, depth]`, `sha256`, source/provenance and license
fields. Keep license files beside the assets. Copy a current manifest as a
schema reference. GLBs should be Y-up, centered horizontally, grounded at zero
and scaled to fit the prop footprint.

`/api/models` combines shared and registered scenario catalogs and adds each
model's resolved `url`. Both server-side variant selection and the browser use
this catalog. Files cannot escape their own model directory. Use
`scenarios.assets.transport_models()` to select IDs by kind. For a new kind,
supply its collision footprint and a procedural fallback or a browser `prop`
hook. Catalogs are cached for the server lifetime; restart after changes.

Farm, airport and factory import tools now write directly to their scenario
folders. `tools/import_transport.py --scenario train_station SOURCE_DIR` rebuilds
rail models; omit `--scenario` for shared road vehicles. Shared background models
remain in their common catalog because multiple scenarios use them. Existing
ambient sound mappings are optional; a new ID without audio entries uses synthesized fallback ambience.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
.venv/bin/python tests/browser_scenarios.py
.venv/bin/python tests/browser_transport.py
```

Rescue deployment also needs enough reachable ground for five civilians, each
at least ten tiles horizontally from every enemy and outside initial enemy sight.
The shared deployment planner retries randomized pockets and enemy positions; it
rejects layouts that cannot meet these rules instead of spawning unsafe civilians.

Add generation tests across all sizes and several seeds. Check deterministic
layouts, deployment clearance, collision/visual agreement, reachable levels and
model footprints. The static tests follow every registered module's imports and
re-exports and fetch catalog model URLs, catching broken dynamic imports.
