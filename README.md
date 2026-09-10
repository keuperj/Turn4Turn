# Ground Control — tactical operations

A browser-based, XCOM-inspired single-mission game. Python owns combat,
pathfinding, visibility, equipment and randomized missions. The locally bundled
Babylon.js 9.25.0 renderer displays the battlefield. There is no campaign or economy.

## Run

Requires Python 3.10+ and a browser with **WebGL 2** enabled. No Python packages,
CDN access, or internet connection are needed to play.

```sh
python3 server.py --port 8002
```

Open **http://localhost:8002**. Stop with Ctrl+C. Restart after Python changes;
refresh after frontend changes. The loopback server stores one shared mission
in memory, so connected tabs play the same battle.

The separate [engine comparison](http://localhost:8002/comparison/) shows the same
textured courtyard, animated soldier, vehicle and effects in Babylon.js,
PlayCanvas and Three.js. It includes camera presets, floor cutaways and frame-time
measurements. See [comparison notes and credits](static/comparison/README.md).

## Mission preparation

Every new mission opens a visual equipment screen:

- Choose one of seven themes or a random theater.
- Choose **Compact 24×24**, **Standard 30×30**, or **Large 40×40**. Building and
  scenery density scale with area; larger missions contain more hostiles.
- Click any pictured equipment slot to open the equipment catalog.
- Each fighter has four selectable slots. Any weapon or item fits any slot; choose four distinct items.
- The shield/check icon deploys the squad. Equipment cannot change afterward,
  but carried items can be switched freely while a fighter has AP.

Themes: urban district, factory, train station, airport, streets, woods and farm.
Buildings have connected multi-room floors, internal doors, roofs, upper-floor
windows, stairs, and both indoor and outdoor ladders. Missions include indoor
enemy defenders, including upper-floor positions in multi-storey theaters. Scenery includes
cars, trucks, trains, aircraft, industrial equipment and trees. Vehicles cannot
be driven or boarded.

## Single-click / double-click controls

Action buttons use icons with hover hints and accessible labels. Equipment and
fighter buttons retain their pictures and names.

1. Select a fighter and choose movement or attack.
2. Single-click a point to select it. The path/aim line and status strip show
   the AP cost, hit chance, health and friendly-fire risks.
3. Double-click that goal to execute. There are no confirmation dialogs.
   Escape cancels; Enter executes a pending goal.

The browser waits for any pending preview before executing a double-click and
revalidates the same goal on the server. A single click or cancelled goal spends
no resources. Doors and ladders support the same double-click pattern. Reload,
stance, overwatch and peek icons perform their named action directly.

**All firearms and explosives can target empty ground within the selected
fighter’s line of sight and weapon range.** Walls, intervening cover, smoke,
height and stance still matter. Click a structure directly to damage it;
there is no separate structure-attack menu. Structures show health labels like
people. Coordinates represent tactical tiles and floor levels, not pixel-scale
ballistics. Grenades still use their short throwing range; charges are planted
within 1.5 tiles rather than launched across the map.

Right-drag orbits, left-drag pans, and the wheel zooms. The focus icon/F centers
the selected fighter; the home icon shows the mission. The always-visible
**overview map** shows explored terrain, friendly units and detected contacts.
Clicking it moves the camera without issuing orders. Unseen enemies never
enter the browser payload or the overview.

Shortcuts: **1–4** select, **F** focus, **R** reload, **O** overwatch,
**Escape** cancel, **Enter** execute a pending order or end the squad turn.

## Combat

Each fighter has 2 AP. Standing moves 5 tiles/AP, kneeling 3, prone 2. Changing
stance costs 1 AP. Kneeling adds 5 aim and 10 defense; prone adds 10 aim and 20
defense. Defense applies beyond two tiles. Prone fighters cannot climb or fire
RPGs. Directional cover and high ground also affect accuracy.

| Equipment | Behavior |
| --- | --- |
| M4A1 / HK416 / M249 | Single or automatic fire; firing ends the turn |
| M110 | Accurate semiautomatic marksman rifle |
| M24 sniper | 10 damage, range 20, five-round magazine; requires 2 AP |
| Shotgun | 10 damage, range 5, five-round magazine; firing ends the turn |
| Medikit | Support item: two treatments, each heals up to 6 HP for 1 AP |
| M9 | Handgun; each shot costs 1 AP |
| RPG-7 | Heavy structural damage, range 11, radius 2 |
| Frag grenade | Range 5, radius 2; affects friends and enemies |
| Smoke grenade | Range 5, radius 3; blocks both sides’ sight for 3 hostile phases |
| Demolition charge | Plant within 1.5 tiles; radius 4; detonates after 2 hostile phases |

Automatic fire uses up to three available rounds with a 20-point accuracy
penalty per projectile. Coordinate attacks fire the selected burst even when
a target falls during it. Each round produces its own sound and impact.
Overwatch fires one shot with a 15-point aim penalty; sniper overwatch requires
2 AP. Reload costs 1 AP and uses finite reserves. Firearms have three spare
magazines; RPGs have one spare rocket. Grenades and charges have no reserves.

Bullets chip structural health, grenades do moderate damage, RPGs cause heavy
damage, and demolition can destroy aircraft and level buildings. Buildings
collapse as a whole when health reaches zero. Walls, upper surfaces and stairs
are removed; upper-floor occupants die. Destroyed footprints become walkable
rubble. Dead people never obstruct walking paths.

Smoke does not stop blast damage. Demolition penetrates cover. Timers count
completed hostile phases, including the first phase after placement. Withdraw
beyond the four-tile radius before ending the second turn.

## Medical support, facing and corner tactics

Equip a medikit, then single-click another wounded soldier to preview treatment
and double-click to heal. The teammate must be alive, adjacent (within 1.5 tiles)
and on the same floor. Walls and closed doors block treatment; medikits cannot
revive casualties or refill from reserve ammunition.

The direction-arrow icon enters facing mode. Click a point to rotate the fighter
and heading indicator without spending AP or ammunition, even at 0 AP. Movement
also updates heading. Facing is visual: shared squad awareness continues to use
line of sight in all directions.

Standing or kneeling directly beside the end of cover exposes a directional
peek icon. A peek costs 1 AP, briefly moves to the adjacent free corner position,
reveals contacts and terrain, then returns to cover. Eligible enemies may each
fire one reaction shot, with hit chance capped at 10%. Peeking is not invulnerable;
if killed, the fighter's body is returned to the cover tile. Prone fighters cannot
peek, and a blocked side step prevents the action.

Frag and smoke grenades can be thrown around a corner from that same edge.
The preview shows a two-segment route. The entire route must fit the grenade's
range, the second segment cannot cross a wall or ceiling, and the destination
must have been explored (a peek can reveal it). This does not let firearms or RPGs
shoot through corners.

## Visibility, interiors and objectives

Standing sight is 14 tiles, kneeling 10, prone 7. A standing fighter holding an
M24 has 20-tile scoped sight. Kneeling targets are detected at 80% range and
prone targets at 55%. Eye heights, walls, floors and cover affect visibility.
Explored terrain remains remembered; live enemies disappear when undetected.
Gray silhouettes and minimap outlines mark the last *observed* enemy coordinates
and round. No hidden movement, current HP or inventory is copied into these
markers. Reacquisition replaces them with live contacts. Confirmed casualties and
close inspection of an old location clear the corresponding stale marker.

Open or close adjacent doors/windows for 1 AP. Windows cannot be traversed;
closed shutters block fire. Open windows allow shots above the sill. Auto cutaway
shows rooms when a door opens or a fighter enters. Use the floor selector to
inspect interiors or roofs. Stairs and ladders connect walkable levels. Door,
window, stair and ladder labels appear only on hover; their geometry and labels
are occluded by walls and ceilings in exterior view. Cutaways expose the selected
floor. Internal doors block walking and sight until opened.

Eliminate all hostiles to win; losing the squad ends the mission. Civilians
head toward the southern evacuation boundary after hostile phases. Keep them
safe from friendly fire. There is no saved-game system or multiplayer isolation.

## Rendering and assets

The battlefield is **WebGL only**; the software fallback and renderer selector
have been removed. Rendering uses antialiasing, up to 2× pixel density, 2048-pixel
soft shadows, ACES tone mapping, textured materials, articulated figures,
tracers, impact debris, smoke and corpses. The overview alone uses a small Canvas
2D HUD; it is not a software battlefield renderer. WebGL startup failure shows
an explanatory message.

All 13 equipment types have photographic artwork. Existing atlas images are
used for eight items; the additional images were generated using the built-in
image_gen tool and saved in the project:

- `static/assets/m24.png`
- `static/assets/smoke-grenade.png`
- `static/assets/demolition-charge.png`
- `static/assets/shotgun.png`
- `static/assets/medikit.png`

Shotgun/medikit prompts: [SUPPORT-PROMPTS.md](static/assets/SUPPORT-PROMPTS.md).
Previous additional prompts: [EQUIPMENT-PROMPTS.md](static/assets/EQUIPMENT-PROMPTS.md).
Earlier prompts: [PROMPTS.md](static/assets/PROMPTS.md) and
[ITEMS-PROMPT.md](static/assets/ITEMS-PROMPT.md). Figures and scenery are procedural
3D models rather than photogrammetric scans. Sounds are local ElevenLabs-generated samples for weapons, movement, interactions,
impacts, explosions and pain reactions, plus one ambience per map theme; there is no music.
The game never calls ElevenLabs during play.

Three.js / OrbitControls 0.169.0 is bundled with its MIT license in
`static/vendor/THREE-LICENSE.txt`.

## Verify

```sh
python3 -m unittest discover -s tests -q
python3 tests/browser_smoke.py --browser /snap/bin/chromium
python3 tests/browser_audio.py
python3 tests/browser_interiors.py
```

The optional browser check requires Python Playwright and Chromium. It starts an
isolated local server. Simulation tests cover combat, fog, interiors, loadouts,
timers, destruction, preview immutability, arbitrary-point targeting, structure
occlusion and all-theme generation at the supported map sizes. Browser tests
exercise real WebGL clicks, double-click execution/cancellation, item imagery, visual
mission setup, icons, minimap navigation, firing and structure health previews.

## API and source

`POST /api/new` accepts `{"seed":83,"theme":"urban","size":40}` and starts mission
preparation. `/api/action` with `action: "deploy"` accepts a `loadouts` map of the
four fighter IDs, each with `primary`, `sidearm`, `utility1` and `utility2` (legacy clients may omit
`sidearm`, which defaults to M9).

`POST /api/preview` validates an order and returns its description without
spending resources. Example: `{"action":"attack","unit":"s0","x":12,"y":24,"z":0}`.
Send the same body to `/api/action` to execute. Structure clicks add a `structure`
ID and a tile on that structure. Moves use `action:"move"`; door/window orders
use `action:"interact"` plus a portal ID. The server revalidates on execution. `face` uses an X/Y direction point with no AP cost; `heal` takes a teammate target ID; `peek` takes one of the returned corner coordinates.

`game.py` — simulation; `targeting.py` — previews and coordinate attacks; `fieldcraft.py` — healing, facing and corners;
`arsenal.py` — equipment/timers/destruction; `visibility.py` — squad knowledge;
`world.py` — map generation; `server.py` — HTTP API; `static/scene.js` — Babylon battlefield;
`static/rendering.js` — Babylon scene primitives, picking and camera;
`static/characters.js` — glTF skeletons, animation and poses;
`static/environment.js` — scenery; `static/app.js` — controls and preparation;
`static/minimap.js` — overview; `static/icons.js` — action icons;
`static/audio.js` — local sample playback, ambience, spatial mixing and variants;
`audio_assets.py` — sound catalog, discovery and fallback creation;
`tools/generate_sounds.py` — resumable offline ElevenLabs generation.

World health bars appear only while hovering over a person or destructible object. Sidebar selection centers the camera on that fighter. Enemy phases follow visible hostile actions without exposing hidden enemies. Wheel zoom ranges from close inspection to a full-map view (2–220 units).


## Sound files and additional variants

The initial set contains **33 action sounds and seven ambient loops**, generated
with ElevenLabs and stored in `static/sounds/`. Audio runs entirely from localhost.
The sound toggle controls both effects and ambience; the volume slider updates
currently playing sounds too. Ambience plays only during active missions and
pauses when the tab is hidden. Shot positions use only public game events.

Add numbered files such as `shot_m4a1_002.mp3`, `reload_002.wav` or
`ambient_farm_002.ogg`. Reload the page or start a new mission to discover them.
Playback randomly selects a matching variant and avoids immediate repeats when
there is more than one. Ambient variants crossfade at loop boundaries.

`GET /api/audio` discovers the local numbered MP3/WAV/Ogg files automatically.
Real files take precedence over tracked placeholders. Generated placeholders
remain available as backups; they are not mixed into groups with real samples.

To fill any missing groups later, run `python3 tools/generate_sounds.py` with
`ELEVENLABS_API_KEY` in your terminal environment or project-root `.env`.
The script skips existing real sounds, saves every successful response, and
stops API calls if quota, authentication, network or other service errors occur.
All unfinished groups retain placeholders, so implementation/play never depends
on API availability. It does not generate extra variants automatically.

See [the sound-folder guide](static/sounds/README.md) for filenames, replacement
rules and generation commands. Prompts and durations are editable in
`audio_assets.py`. Credentials are never served to the browser.


Smoke obscures sight and targeting, but does not block movement. Fighters can
preview and move to previously explored tiles inside or beyond a smoke cloud,
including greyed-out tiles; unexplored destinations still require exploration or
a nearby vertical connection. Moving through smoke does not reveal hidden enemies.


## Babylon.js renderer

The game runs entirely on the locally bundled Babylon.js engine. Three.js is
retained only for the separate historical comparison and asset authoring tools.
No CDN, account or external service is needed to play. Python remains authoritative
for movement, sight, targeting, destruction, equipment and turns.

The renderer includes rigged glTF fighters with walking/idle blending, attached
equipment, adapted kneeling/prone poses, PBR materials with procedural surface
normal maps, soft shadows, billboard smoke and native ray picking. The soldier
is stylized; custom crawl/climb animation sets and photorealistic replacement
models remain future art work. Doors, windows, floor cutaways, fog, memories,
hover labels, camera tracking and all existing controls are preserved.

Character credits: [model notes](static/assets/models/README.md). Engine license:
[Apache 2.0](static/vendor/BABYLON-LICENSE.txt).

Browser checks (Playwright + Chromium):
`python3 tests/browser_smoke.py`, `python3 tests/browser_interiors.py`,
`python3 tests/browser_babylon.py`, and `python3 tests/browser_audio.py`.
The Babylon test checks actual skeleton animation and resource counts across
state refreshes, in addition to saving a stance screenshot for inspection.
