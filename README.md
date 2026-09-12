# Turn4Turn

Turn-based tactical operations in the browser. Command a four-person fireteam,
manage limited action points and equipment, clear multi-storey environments, and
keep civilians alive. Python runs the authoritative simulation while Babylon.js
renders the battlefield locally with WebGL 2.

> A vibe coding project by [Janis Keuper](https://github.com/keuperj), built with GPT-6 Astra.

![Turn4Turn landing page](docs/screenshots/landing.png)

## Features

- **Two ways to play:** a ten-mission campaign with fixed briefings and a fully
  configurable single-mission mode.
- **Server-authoritative tactics:** movement, visibility, targeting, damage,
  destructible structures, enemy turns, and objectives are validated in Python.
- **Isolated multiplayer sessions:** every consenting browser receives its own
  game instance; per-player locks keep concurrent requests safe.
- **Procedural battlefields:** urban districts, factories, stations, airports,
  streets, woods, and farms across three map sizes.
- **Enterable buildings:** connected rooms, multiple floors, doors, windows,
  stairs, ladders, roofs, cutaway views, and indoor defenders.
- **Four mission types:** eliminate hostiles, rescue civilians, capture a flag,
  or defend a position.
- **Tactical positioning:** standing, kneeling, and prone stances; directional
  cover; high ground; peeking; overwatch; smoke; and last-seen contact markers.
- **Flexible loadouts:** rifles, machine guns, pistols, sniper rifles, shotgun,
  RPG, grenades, demolition charges, and medical support. Preferred loadouts can
  be saved as a browser cookie.
- **Destructible environments:** weapons damage vehicles and structures;
  collapsed buildings become rubble and can kill occupants.
- **Fog of war:** the browser receives only detected enemies, remembered
  casualties, and previously observed positions—never hidden live state.
- **Local audiovisual assets:** rigged glTF soldiers, generated equipment and
  stance art, spatial effects, weapon sounds, interactions, and themed ambience.
- **No runtime CDN:** the engine, models, textures, and sounds are bundled.

![Turn4Turn gameplay](docs/screenshots/gameplay.png)

## Requirements

- Python 3.10 or newer
- A modern browser with WebGL 2 enabled
- No Python packages for normal play

The battlefield currently uses WebGL through Babylon.js. WebGPU is not enabled.

## Setup

Clone the repository and start the server:

```sh
git clone https://github.com/keuperj/RBS_Alien.git
cd RBS_Alien
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000). On the first visit, choose a
user name and consent to the cookies required for player identification and
progress. Stop the server with `Ctrl+C`.

To use a different port:

```sh
python3 server.py --port 8002
```

Then open [http://localhost:8002](http://localhost:8002).

## Server configuration

Command-line options:

| Option | Default | Description |
| --- | ---: | --- |
| `--port PORT` | `8000` | Local HTTP port. The server binds to `127.0.0.1`. |
| `--max-players COUNT` | `10` | Maximum number of active, isolated player sessions. Must be at least 1. |

Example:

```sh
python3 server.py --port 8080 --max-players 20
```

Additional constants are defined near the top of `server.py`:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `MAX_PLAYERS` | `10` | Default active-player limit used when the CLI option is omitted. |
| `SESSION_TIMEOUT` | `1800` seconds | Idle time after which a session releases its player slot. |
| `COOKIE_AGE` | `365` days | Lifetime of persistent player cookies. |

When the active-player limit is reached, a new visitor is not assigned a game
and sees a **Try again later** screen. An existing active player can reconnect
with the same user-ID cookie without consuming another slot.

The in-memory game sessions do not survive a Python server restart. Browser
cookies for identity, campaign progress, and preferred loadout remain available.

## Browser storage and privacy

Turn4Turn asks for consent before creating its player cookies.

| Cookie | Contents |
| --- | --- |
| `turn4turn_user` | Random player ID; marked `HttpOnly` and `SameSite=Lax`. |
| `turn4turn_name` | The chosen display name. |
| `turn4turn_campaign` | Current campaign index and active mission seed. |
| `turn4turn_loadout` | Optional default equipment selection. |

Cookies are scoped to the game path and are not sent to third-party services.
The loadout cookie is created only when **Use this equipment selection as my
default loadout** is enabled during mission preparation. Clearing site data
resets the browser identity and saved preferences.

## Mission configuration

Single Mission mode exposes the following settings before deployment. Campaign
missions provide these values from their briefing and keep them locked.

### Mission type

| Mission | Objective |
| --- | --- |
| Eliminate all enemies | Neutralize every hostile fighter. |
| Save the civilians | Evacuate every civilian or eliminate all hostiles without civilian losses. |
| Capture the enemy flag | Reach the hostile flag within 30 rounds. |
| Defend the flag | Hold the squad flag for 30 rounds or eliminate all hostiles. |

### Theater and scale

- **Theaters:** Random, Urban District, Factory, Train Station, Airport, Streets,
  Woods, and Farm.
- **Map sizes:** Compact `24×24`, Standard `30×30`, and Large `40×40`.
- **Time:** Day or Night.

Larger maps generate more scenery, structures, walkable area, and hostiles.

### Difficulty

| Difficulty | Squad AP | Hostile AP |
| --- | ---: | ---: |
| Easy | 3 | 1 |
| Medium | 2 | 2 |
| Hard | 2 | 3 |

### Equipment

Each fighter receives four distinct equipment slots. Any weapon or support item
can occupy any slot, and carried equipment can be switched during the mission.
The chosen loadout becomes fixed after deployment.

| Equipment | Tactical role |
| --- | --- |
| M4A1, HK416, M249 | Single or three-round automatic fire |
| M110 | Accurate semiautomatic marksman rifle |
| M24 sniper | Long-range, high-damage shot requiring 2 AP |
| Shotgun | High damage at short range |
| M9 | Sidearm; firing costs 1 AP |
| RPG-7 | Direct-fire explosive and heavy structural damage |
| Frag grenade | Ballistic throw over obstacles; radius damage to either team |
| Smoke grenade | Ballistic throw; blocks sight for three hostile phases |
| Demolition charge | Short-range placement, delayed four-tile blast |
| Medikit | Two adjacent treatments restoring up to 6 HP each |

Grenades may arc to an explored surface without direct line of sight. Walls and
closed doors still shield units from the resulting blast. Rockets require a
clear line of fire, and demolition charges must be planted within 1.5 tiles.

## Controls

1. Select a fighter and choose movement, attack, or facing mode.
2. Single-click a point to preview the authoritative path or attack solution.
3. Double-click the same point to execute it.

| Input | Action |
| --- | --- |
| `1`–`4` | Select a squad member |
| `F` | Focus the selected fighter |
| `R` | Reload |
| `O` | Enter overwatch |
| `Escape` | Cancel the current preview |
| `Enter` | Execute a pending order or end the squad phase |
| Right-drag | Orbit the camera |
| Left-drag | Pan the camera |
| Mouse wheel | Zoom |
| Minimap click | Reposition the camera without issuing an order |

Opening doors and windows costs 1 AP. Changing stance costs 1 AP. Peeking costs
1 AP and briefly exposes the fighter to reaction fire. The interface reports AP
cost, hit chance, target health, blast victims, and friendly-fire risk before an
order is executed.

## Architecture

| Path | Responsibility |
| --- | --- |
| `server.py` | Threaded HTTP server, cookies, capacity, and per-player sessions |
| `game.py` | Authoritative turns, AI, missions, movement, and damage |
| `targeting.py` | Attack previews and coordinate targeting |
| `visibility.py` | Fog of war and public-state filtering |
| `fieldcraft.py` | Facing, peeking, healing, and nearby interactions |
| `arsenal.py` | Loadouts, ammunition, explosives, and destruction |
| `world.py` | Seeded map and building generation |
| `static/app.js` | Browser state, session consent, controls, and preparation UI |
| `static/scene.js` | Babylon.js battlefield and effects |
| `static/characters.js` | glTF character models, animation, and poses |
| `static/environment.js` | Structures, scenery, and visual damage |
| `static/minimap.js` | Fog-aware tactical overview |
| `static/audio.js` | Local effects, ambience, and spatial mixing |

The Python state is authoritative. The renderer handles presentation and input,
but it cannot decide whether an action is legal or alter hidden simulation state.

## Engine comparison

Start the game and visit [http://localhost:8000/comparison/](http://localhost:8000/comparison/)
to view the isolated Babylon.js, PlayCanvas, and Three.js renderer study. It uses
shared assets and camera paths but is separate from the playable simulation. See
the [comparison notes](static/comparison/README.md).

## Testing

Run the simulation and server tests:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Optional browser checks require Playwright and Chromium:

```sh
python3 tests/browser_smoke.py --browser /snap/bin/chromium
python3 tests/browser_campaign.py
python3 tests/browser_interiors.py
python3 tests/browser_babylon.py
python3 tests/browser_audio.py
```

The suite covers game rules, all themes and map sizes, fog-of-war privacy,
interiors, loadout validation, campaign persistence, session isolation, player
capacity, real WebGL interaction, animation, and audio fallback behavior.

## Assets and credits

- Babylon.js is bundled under the [Apache 2.0 license](static/vendor/BABYLON-LICENSE.txt).
- Character source and conversion notes are documented in
  [static/assets/models/README.md](static/assets/models/README.md).
- Equipment, landing, campaign, ammunition, and stance images were created for
  the project with OpenAI image generation. Prompt records are stored alongside
  the assets where available.
- Local action and ambience samples were generated with ElevenLabs. See the
  [sound asset guide](static/sounds/README.md).

There is no music and the game does not contact image or audio generation
services during play.
