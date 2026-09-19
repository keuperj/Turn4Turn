# Playing Turn4Turn

[Documentation](README.md) · [Back to the game](../README.md)

Command four fighters through a campaign or a custom mission. Plan around action
points, cover and visibility; protect civilians and check blast areas before firing.

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

Rescue missions randomize both groups while keeping every civilian at least
10 tiles from every enemy at deployment and outside every enemy’s initial view.
This gives the squad room to intervene before enemies close in.

Enemies share sightings and coordinate supporting fire and flanking routes. Once
spotted, breaking one enemy's line of sight may not be enough: another enemy can
keep the team informed. Lost contacts are remembered briefly, not tracked through
walls. In rescue missions, enemies must discover civilians before pursuing them.

Civilians act independently and plan several turns ahead. They weigh escape
progress against exposed routes and may take a detour or hide until danger eases.
Clearing threats and opening escape doors helps them reach the evacuation edge.

### Theater and scale

- **Theaters:** Random, Urban District, Factory, Train Station, Airport, Streets,
  Woods, and Farm.
- **Map sizes:** Compact `24×24`, Standard `30×30`, and Large `40×40`.
- **Time:** Day or Night.

Larger maps generate more scenery, structures, walkable area, and hostiles.

Urban maps use compact downtown blocks with 3–6-storey buildings, shops and cafés
with outdoor seating. Asphalt streets, crosswalks, sidewalks and paved pedestrian
lanes surround one seeded pocket park with trees, shrubs and a bench. Parked cars,
traffic signals, signs, street lamps and bins have collision footprints; generation
keeps entrances and pedestrian routes connected. Streets continue into a matching
background street grid and skyline. Cutaway controls include all six upper levels.

Street crossing is a suburban four-lane junction (two lanes in each direction on
both roads), with lane markings, zebra crossings, traffic signals and stopped cars.
Detached one- and two-storey homes sit behind sidewalks and planted front gardens,
with clear paths to their doors. The roads, sidewalks and houses continue into the
static background. Road paint and distant traffic are batched; fog updates retain
the scenery and vehicle instances.

Woodlands uses dense mixed forest with seeded grassy clearings and scattered
single-storey timber huts. Narrow footpaths connect every entrance to deployment
and continue into the surrounding forest. Vegetation preserves walkable routes;
background plants are decorative and do not affect movement or targeting.

Trainstation centers on two parallel railway tracks with independently placed trains.
A large station has paired double doors from the street and covered platform,
opening into a waiting hall with seating, a ticket counter, a table and bins.
Both door leaves open together for one action point. Framed windows and
forecourt trees complete the buildings; the opposite platform has benches, bins and lamps. Clear crossings
connect both sides, with smaller city buildings and streets where space permits.
The rails continue through the city background.

Farmstead has a farmhouse, barns and a machine shed connected by clear dirt paths.
Locally bundled tractor, front-loader, cow, sheep and pig models populate the yard.
Mixed trees, shrubs and pasture grass fill the playable grounds, with hedgerows and
shelter belts continuing into the surrounding fields. Equipment and vegetation
preserve access to every entrance; livestock are static scenery.

Airport centers on a clear runway and apron with locally bundled light aircraft,
business jet, tug, fuel bowser, power cart and windsock models. A larger terminal
has a furnished waiting area and check-in counter, alongside two hangars and a
three-storey control tower. Runway markings continue seamlessly into the flat
grassland background; an approach road leads directly to the terminal entrance.
Compact maps have one parked aircraft; standard and large maps have two.

Factory is an indoor production hall with dense, staggered machine rows and clear
work aisles. Outer mezzanines surround a central stack rising three floors above
the main floor. Only the north and west
outer walls are shown; the south and east sides stay open, against a plain background.
Imported CNC machines, lathes, mills, compressors, storage racks, welding robots,
conveyors and a forklift furnish the floors. Full stair flights with handrails and open stair wells connect the levels; floor
controls reveal lower work areas. Equipment has collision, visibility and damage on its own floor.

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
