"""Local sound catalog, file discovery and explicitly tracked fallback assets."""
import hashlib
import io
import json
import math
import random
import re
import struct
import wave
from pathlib import Path

SOUND_DIR = Path(__file__).resolve().parent / 'static' / 'sounds'
# One initial sample per audible action. Further numbered variants need no code changes.
CATALOG = {}
def entry(name, prompt, seconds=1.5, ambient=False):
    CATALOG[name] = dict(text=prompt, duration_seconds=seconds, loop=ambient,
                         model_id='eleven_text_to_sound_v2', prompt_influence=.5)

for key, description in {
    'm4a1':'M4A1 5.56mm assault rifle', 'hk416':'HK416 5.56mm assault rifle',
    'm110':'M110 7.62mm marksman rifle', 'm249':'M249 light machine gun',
    'm9':'M9 9mm pistol', 'm24_sniper':'M24 bolt action sniper rifle',
    'shotgun':'12 gauge pump action shotgun', 'alien_carbine':'alien energy carbine with a sharp electrical discharge',
}.items():
    entry('shot_'+key, f'Exactly one isolated shot from a {description}. Immediate sharp attack, powerful realistic report and short outdoor decay. No burst, no voices, no music, no handling before firing.', 1.5)
entry('hurt','One adult soldier gives a short natural pained cry and gasp after being hit. Believable human vocal performance, no words, no electronic tones, no music, no other sounds.',1)
for theme, description in {
    'urban':'Quiet deserted urban courtyard, breeze between buildings, distant ventilation and occasional loose debris rustling',
    'factory':'Industrial factory, low steady ventilation, distant machinery rumble and subtle metal creaks',
    'train_station':'Quiet empty railway station, breeze along the tracks, faint electrical hum and occasional rail metal creaks',
    'airport':'Quiet regional airfield, open runway wind, faint terminal ventilation and distant hangar rattles',
    'streets':'Deserted street intersection, wind between buildings, soft distant city hum and paper rustling',
    'woods':'Woodland, light wind in leaves, scattered birds and quiet insects',
    'farm':'Rural farmstead, wind in grass, quiet insects, distant birds and wooden barn creaks',
}.items():
    entry('ambient_'+theme, description+'. Subtle continuous environmental ambience, seamless loop, no speech, music, gunfire, explosions or dramatic changes.',12,True)
for key, (description, seconds) in {
    'move':('One boot footstep on rough concrete with a little tactical gear rustle',.5),
    'crawl':('A short movement crawling over dirt, cloth scraping and equipment rustle',.5),
    'climb':('One boot stepping on a metal ladder rung with a subdued clank',.5),
    'reload':('A quick rifle reload: magazine release, new magazine clicks into place, bolt clicks forward',1.2),
    'throw':('Grenade pin pull with a metal click and a short cloth swish as it is thrown',.7),
    'rocket_launch':('One RPG launcher firing, explosive launch thump followed by a short rushing rocket hiss',1),
    'blast_grenade':('One fragmentation grenade explosion, sharp crack, deep thump, short grit and debris fall',2),
    'blast_rocket':('One rocket impact explosion, heavy low blast with metal fragments and debris falling',2.5),
    'blast_charge':('One powerful demolition explosion followed by collapsing concrete, twisting metal and falling rubble',3),
    'smoke':('Smoke grenade beginning to release smoke with a pop and soft sustained pressurized hiss',2),
    'charge_place':('Setting down a demolition charge, fastening its strap and activating a timer with one small electronic click',1),
    'impact':('One bullet strikes masonry, a sharp dry crack with a brief scatter of grit',.5),
    'heal':('Opening a medical pouch, tearing a sterile dressing wrapper and wrapping a cloth bandage',1.2),
    'door_open':('One heavy wooden door opens, latch click followed by a brief hinge creak',.8),
    'door_close':('One heavy wooden door closes with a solid short thud and latch click',.7),
    'window_open':('One window latch clicks and its framed glass pane slides open',.8),
    'window_close':('One framed glass window slides closed with a small rattle and latch click',.7),
    'equip':('A soldier lifts a rifle on its sling, tactical fabric rustle and a subdued metallic clack',.6),
    'stance':('A soldier changes crouching posture, brief cloth and knee pad rustle',.5),
    'face':('A tiny boot pivot and soft clothing rustle',.5),
    'peek':('A short careful body lean around cover with quiet clothing brushing a wall',.5),
    'overwatch':('A rifle is shouldered into a ready position, soft gear movement and small mechanism click',.5),
    'fire_mode':('One crisp small rifle selector switch click',.5),
    'evacuate':('Brief hurried footsteps retreating into the distance',1),
}.items():
    entry(key, description+'. Isolated realistic game sound effect, immediate onset, no music or speech.',seconds)

PATTERN = re.compile(r'^([a-z][a-z0-9_]*?)_(\d+)\.(wav|mp3|ogg)$')

def read_sources(directory=SOUND_DIR):
    try:return json.loads((directory/'_sources.json').read_text())
    except (FileNotFoundError, ValueError):return {}

def write_sources(sources, directory=SOUND_DIR):
    temporary=directory/'_sources.json.tmp'
    temporary.write_text(json.dumps(sources,indent=2)+'\n')
    temporary.replace(directory/'_sources.json')

def digest(data):return hashlib.sha256(data).hexdigest()

def discover(directory=SOUND_DIR):
    """Only numbered audio files; real variants replace rather than mix with fallbacks."""
    groups={};sources=read_sources(directory)
    if not directory.exists():return groups
    for p in sorted(directory.iterdir()):
        match=PATTERN.fullmatch(p.name)
        if not match or not p.is_file() or p.is_symlink() or not p.stat().st_size:continue
        action,number,_=match.groups()
        meta=sources.get(p.name,{})
        placeholder=meta.get('source')=='placeholder' and meta.get('sha256')==digest(p.read_bytes())
        groups.setdefault(action,[]).append(dict(url='/sounds/'+p.name,number=int(number),placeholder=placeholder))
    for action, samples in groups.items():
        real=[s for s in samples if not s['placeholder']]
        groups[action]=sorted(real or samples,key=lambda s:(s['number'],s['url']))
    return groups

def placeholder_bytes(action):
    """Quiet, short foley/noise fallback; ambience is a subtle loopable wind bed."""
    ambient=action.startswith('ambient_');duration=3 if ambient else .22
    rate=22050;n=int(rate*duration);rng=random.Random(action);smooth=0.;frames=[]
    heavy=action.startswith(('blast_','shot_'))
    for i in range(n):
        t=i/rate;smooth=.90*smooth+.10*rng.uniform(-1,1)
        envelope=math.sin(math.pi*i/(n-1))**2 if ambient else min(1,i/100)*math.exp(-t*24)
        # No fake synthesized human scream. Missing voices get a quiet soft rustle.
        value=smooth*(.09 if ambient else .35)*envelope
        if heavy:value+=.15*math.sin(2*math.pi*75*t)*envelope
        frames.append(struct.pack('<h',int(max(-1,min(1,value))*32767)))
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(b''.join(frames))
    return out.getvalue()

def ensure_placeholders(directory=SOUND_DIR):
    directory.mkdir(parents=True,exist_ok=True);groups=discover(directory);sources=read_sources(directory)
    for action in CATALOG:
        if groups.get(action):continue
        filename=action+'_001.wav';data=placeholder_bytes(action)
        (directory/filename).write_bytes(data)
        sources[filename]=dict(source='placeholder',sha256=digest(data))
    write_sources(sources,directory)
