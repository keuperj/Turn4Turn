# Ground Control — tactical operations

A browser-based, XCOM-inspired single-mission game. Python owns combat,
pathfinding, visibility, equipment and randomized missions. The locally bundled
Three.js renderer displays the battlefield. There is no campaign or economy.

## Run

Requires Python 3.10+ and a browser with **WebGL 2** enabled. No Python packages,
CDN access, or internet connection are needed to play.

```sh
python3 server.py --port 8002
```

Open **http://localhost:8002**. Stop with Ctrl+C. Restart after Python changes;
refresh after frontend changes. The loopback server stores one shared mission
in memory, so connected tabs play the same battle.

## Mission preparation

Every new mission opens a visual equipment screen:

- Choose one of seven themes or a random theater.
- Choose **Compact 24×24**, **Standard 30×30**, or **Large 40×40**. Building and
  scenery density scale with area; larger missions contain more hostiles.
- Click a pictured main-weapon/support slot to open the equipment catalog.
- Each fighter receives a main weapon, M9 and two different support items.
- The shield/check icon deploys the squad. Equipment cannot change afterward,
  but carried items can be switched freely while a fighter has AP.

Themes: urban district, factory, train station, airport, streets, woods and farm.
Buildings have interior floors, roofs, doors, windows and stairs. Scenery includes
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
inspect interiors or roofs. Stairs and ladders connect walkable levels.

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
3D models rather than photogrammetric scans. Sounds are local synthesized
weapon reports, impacts, footsteps, explosions and pain cries; there is no music.

Three.js / OrbitControls 0.169.0 is bundled with its MIT license in
`static/vendor/THREE-LICENSE.txt`.

## Verify

```sh
python3 -m unittest discover -s tests -q
python3 tests/browser_smoke.py --browser /snap/bin/chromium
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
four fighter IDs, each with `primary`, `utility1` and `utility2`.

`POST /api/preview` validates an order and returns its description without
spending resources. Example: `{"action":"attack","unit":"s0","x":12,"y":24,"z":0}`.
Send the same body to `/api/action` to execute. Structure clicks add a `structure`
ID and a tile on that structure. Moves use `action:"move"`; door/window orders
use `action:"interact"` plus a portal ID. The server revalidates on execution. `face` uses an X/Y direction point with no AP cost; `heal` takes a teammate target ID; `peek` takes one of the returned corner coordinates.

`game.py` — simulation; `targeting.py` — previews and coordinate attacks; `fieldcraft.py` — healing, facing and corners;
`arsenal.py` — equipment/timers/destruction; `visibility.py` — squad knowledge;
`world.py` — map generation; `server.py` — HTTP API; `static/scene.js` — WebGL;
`static/environment.js` — scenery; `static/app.js` — controls and preparation;
`static/minimap.js` — overview; `static/icons.js` — action icons;
`static/audio.js` — action sound.
