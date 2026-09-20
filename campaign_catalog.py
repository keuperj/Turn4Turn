"""Three curated campaigns and authoritative mission configuration."""
import json
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).parent/'campaigns'


@lru_cache(maxsize=1)
def campaign_catalog():
    """Return campaigns in Easy, Medium, Hard order."""
    return {'campaigns':[json.loads((ROOT/name).read_text()) for name in ('easy.json','operation_turning_point.json','hard.json')]}


def campaign_mission(campaign_id,index):
    """Resolve a published mission; clients cannot override its size or difficulty."""
    campaign=next((c for c in campaign_catalog()['campaigns'] if c['id']==campaign_id),None)
    if not campaign:raise ValueError('Unknown campaign.')
    if type(index) is not int or not 0<=index<len(campaign['missions']):raise ValueError('Invalid campaign mission index.')
    return campaign['missions'][index]
