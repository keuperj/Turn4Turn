"""Test audio behavior."""

import io
import json
import tempfile
import unittest
import urllib.error
import wave
from pathlib import Path
from unittest.mock import patch
from audio_assets import CATALOG, discover, ensure_placeholders, SOUND_DIR
from tools.generate_sounds import generate
from world import THEMES


class AudioTests(unittest.TestCase):
    """Group automated checks for audio behavior."""
    def test_rocket_launch_has_public_origin_and_target_before_blast(self):
        """Verify that rocket launch has public origin and target before blast."""
        from test_fog import FogTests
        g=FogTests().field();u=g.units[0]
        g.action(dict(action='equip',unit=u['id'],weapon='RPG-7'))
        g.action(dict(action='attack',unit=u['id'],x=14,y=24,z=0))
        launch=next(e for e in g.events if e['type']=='rocket_launch')
        blast=next(e for e in g.events if e['type']=='blast')
        self.assertEqual(launch['target'],[14,24,0])
        self.assertEqual(launch['point'],g.position(u))
        self.assertLess(g.events.index(launch),g.events.index(blast))

    def test_every_theme_and_weapon_has_a_sample_group(self):
        """Verify that every theme and weapon has a sample group."""
        self.assertEqual({a.removeprefix('ambient_') for a in CATALOG if a.startswith('ambient_')},set(THEMES))
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);ensure_placeholders(folder)
            self.assertEqual(set(discover(folder)),set(CATALOG))
            for samples in discover(folder).values():
                self.assertTrue(samples[0]['placeholder'])
                with wave.open(str(folder/Path(samples[0]['url']).name)) as f:
                    self.assertGreater(f.getnframes(),100)
            # Re-running fallback generation must not rewrite existing files.
            before={p.name:p.stat().st_mtime_ns for p in folder.glob('*.wav')}
            ensure_placeholders(folder)
            self.assertEqual(before,{p.name:p.stat().st_mtime_ns for p in folder.glob('*.wav')})

    def test_numbered_variants_replace_placeholders_and_ignore_unrelated_files(self):
        """Verify that numbered variants replace placeholders and ignore unrelated files."""
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);ensure_placeholders(folder)
            (folder/'shot_m4a1_002.mp3').write_bytes(b'recorded sample')
            (folder/'shot_m4a1_010.ogg').write_bytes(b'another recorded sample')
            (folder/'secret.txt').write_text('not audio')
            (folder/'shot_m4a1_999.mp3').symlink_to(folder/'secret.txt')
            groups=discover(folder)
            self.assertEqual([s['number'] for s in groups['shot_m4a1']],[2,10])
            self.assertFalse(any(s['placeholder'] for s in groups['shot_m4a1']))
            # Replacing a fallback in place counts as a real sound even with the same filename.
            (folder/'hurt_001.wav').write_bytes(b'new recording')
            self.assertFalse(discover(folder)['hurt'][0]['placeholder'])

    def test_quota_exhaustion_keeps_all_missing_actions_playable(self):
        """Verify that quota exhaustion keeps all missing actions playable."""
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            error=urllib.error.HTTPError('https://api.elevenlabs.io/v1/sound-generation',429,'quota',{},None)
            with patch('urllib.request.urlopen',side_effect=error) as call:
                result=generate(folder,key='test-only')
            self.assertEqual(call.call_count,1)
            self.assertEqual(result['reason'],'http_429')
            self.assertEqual(len(discover(folder)),len(CATALOG))

    def test_generation_resumes_without_spending_credits_on_existing_sounds(self):
        """Verify that generation resumes without spending credits on existing sounds."""
        class Response(io.BytesIO):
            """Provide a minimal HTTP response double for audio-generation tests."""
            headers={'Content-Type':'audio/mpeg'}
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            with patch('urllib.request.urlopen',return_value=Response(b'ID3'+b'x'*256)) as call:
                result=generate(folder,key='test-only',actions=['shot_m4a1'])
            self.assertEqual(result['generated'],1)
            payload=json.loads(call.call_args.args[0].data)
            self.assertEqual(payload['model_id'],'eleven_text_to_sound_v2')
            self.assertFalse(discover(folder)['shot_m4a1'][0]['placeholder'])
            with patch('urllib.request.urlopen') as call:
                generate(folder,key='test-only',actions=['shot_m4a1'])
                call.assert_not_called()

    def test_invalid_response_and_missing_key_preserve_fallbacks(self):
        """Verify that invalid response and missing key preserve fallbacks."""
        class Response(io.BytesIO):
            """Provide a minimal HTTP response double for audio-generation tests."""
            headers={'Content-Type':'application/json'}
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)
            with patch('urllib.request.urlopen') as call:
                result=generate(folder,key='')
                call.assert_not_called();self.assertEqual(result['reason'],'missing_key')
            with patch('urllib.request.urlopen',return_value=Response(b'not sound')):
                result=generate(folder,key='test-only',actions=['hurt'])
            self.assertEqual(result['reason'],'invalid_response')
            self.assertFalse((folder/'hurt_001.mp3').exists())
