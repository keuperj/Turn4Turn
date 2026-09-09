"""Generate missing initial ElevenLabs samples; resume safely after quota exhaustion.
Run from the project directory: python3 tools/generate_sounds.py
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audio_assets import CATALOG, SOUND_DIR, discover, digest, ensure_placeholders, read_sources, write_sources


def api_key():
    key=os.environ.get('ELEVENLABS_API_KEY','').strip()
    if key:return key
    env=Path(__file__).resolve().parents[1]/'.env'
    if env.is_file():
        for line in env.read_text().splitlines():
            name,sep,value=line.strip().removeprefix('export ').partition('=')
            if sep and name.strip()=='ELEVENLABS_API_KEY':return value.strip().strip('\"\'')
    return ''


def generate(directory=SOUND_DIR, key=None, placeholders_only=False, actions=None):
    ensure_placeholders(directory)
    if placeholders_only:return dict(generated=0,reason='placeholders_only')
    key=api_key() if key is None else key
    if not key:
        print('ELEVENLABS_API_KEY unavailable. Local placeholders are ready; rerun to fill missing samples.',flush=True)
        return dict(generated=0,reason='missing_key')
    generated=0;reason='complete'
    for action in actions or CATALOG:
        samples=discover(directory).get(action,[])
        if any(not s['placeholder'] for s in samples):continue
        request=urllib.request.Request('https://api.elevenlabs.io/v1/sound-generation',
            data=json.dumps(CATALOG[action]).encode(),
            headers={'xi-api-key':key,'Content-Type':'application/json','Accept':'audio/mpeg'},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=55) as response:
                content_type=response.headers.get('Content-Type','').split(';')[0]
                data=response.read()
                if content_type not in ('audio/mpeg','audio/mp3','application/octet-stream') or len(data)<128:
                    print(f'{action}: invalid audio response; remaining fallbacks retained.',flush=True)
                    reason='invalid_response';break
            filename=action+'_001.mp3';temporary=directory/(filename+'.tmp')
            temporary.write_bytes(data);temporary.replace(directory/filename)
            sources=read_sources(directory);sources[filename]=dict(source='elevenlabs',sha256=digest(data),request=CATALOG[action])
            write_sources(sources,directory);generated+=1
            print(f'Generated {filename}',flush=True)
        except urllib.error.HTTPError as exc:
            # Do not print request headers or response bodies: they may contain credentials.
            reason=f'http_{exc.code}'
            print(f'ElevenLabs returned HTTP {exc.code}. Stopped API requests; all missing samples have placeholders.',flush=True)
            break
        except (urllib.error.URLError,TimeoutError,OSError):
            reason='network_error'
            print('ElevenLabs connection failed. Stopped requests; rerun later to resume safely.',flush=True)
            break
    remaining=sum(all(s['placeholder'] for s in discover(directory).get(a,[])) for a in CATALOG)
    print(f'Generated {generated}; {remaining} action/theme groups still use placeholders. Status: {reason}.',flush=True)
    return dict(generated=generated,reason=reason,remaining=remaining)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placeholders-only',action='store_true',help='No API requests or credits used')
    parser.add_argument('--action',action='append',choices=CATALOG,help='Generate only the named action(s)')
    args=parser.parse_args()
    result=generate(placeholders_only=args.placeholders_only,actions=args.action)
    # Network failures are distinct so an agent can request sandbox network access.
    sys.exit(2 if result['reason']=='network_error' else 0)
