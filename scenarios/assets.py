"""Shared and scenario-owned model catalogs used by Python and the browser."""
import json
from functools import lru_cache
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1]/'static'


@lru_cache(maxsize=1)
def model_catalog():
    from . import registry
    directories = [STATIC/'assets/models/transport']
    directories += [STATIC/'scenarios'/s.id/'models' for s in registry]
    models, seen = [], set()
    for directory in directories:
        manifest = directory/'manifest.json'
        if not manifest.is_file():
            continue
        for entry in json.loads(manifest.read_text())['models']:
            if entry['id'] in seen:
                raise ValueError(f'Duplicate model ID: {entry["id"]}')
            file = (directory/entry['file']).resolve()
            if not file.is_relative_to(directory.resolve()) or not file.is_file():
                raise ValueError(f'Invalid model file: {file}')
            seen.add(entry['id'])
            models.append({**entry, 'url': '/'+file.relative_to(STATIC).as_posix()})
    return {'models': models}


@lru_cache(maxsize=1)
def transport_models():
    result = {}
    for model in model_catalog()['models']:
        result.setdefault(model['kind'], []).append(model['id'])
    return result
