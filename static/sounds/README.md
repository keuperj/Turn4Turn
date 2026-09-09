# Local battlefield audio

All gameplay audio is served locally. ElevenLabs is used only by the offline
`tools/generate_sounds.py` script, never by a browser or the running game server.

## Adding or replacing samples

Use `action_001.mp3`, `action_002.wav`, `action_003.ogg`, etc. Three-digit numbering
is recommended, but any positive integer works. The action is everything before
the final underscore and number. Names are lowercase. Supported formats: MP3,
WAV and Ogg (use a codec your browser supports).

Examples:

- `shot_m4a1_001.mp3`, `shot_m4a1_002.mp3`
- `reload_001.wav`, `reload_002.wav`
- `hurt_001.mp3`
- `door_open_001.mp3`, `door_close_001.mp3`
- `ambient_woods_001.mp3`, `ambient_woods_002.mp3`

The server scans this folder on each `/api/audio` request. Reload the page or
start another mission to discover added files. The player randomly selects a
matching sample, avoiding the immediately previous choice when alternatives
exist. Ambience chooses a new variant at each crossfaded loop boundary.

The complete list of action names and editable generation prompts is in
`audio_assets.py`. Weapon shots are single-shot clips; automatic fire plays one
sample per simulated round. Movement clips should be short single steps.
Ambience must contain no music or unrelated combat and should loop smoothly.

`_sources.json` records provenance and placeholder hashes. Do not rename this
file. Real samples always take precedence over generated fallback WAVs. A real
recording can replace a fallback in place, or be added with another number;
either approach is detected automatically. Missing or unplayable files also
have a quiet runtime fallback. The server does not expose this metadata file.

## Generating missing sounds

From the project root:

```
python3 tools/generate_sounds.py
```

Set `ELEVENLABS_API_KEY` in the terminal environment or the project-root `.env`.
The `.env` is excluded from version control and is outside the served directory.
Never put credentials in this folder.

The script first fills every missing action/theme group with a local placeholder,
then makes one request per missing group. Successful samples are saved immediately.
It stops on HTTP errors (including quota/rate limits) or connection failures;
all remaining fallbacks stay usable. Re-run to resume. Existing real recordings
are never overwritten and incur no requests. This script fills missing groups;
it does not automatically purchase additional variants.

To retry only one group: `python3 tools/generate_sounds.py --action hurt`.
To prepare fallback files without contacting ElevenLabs:
`python3 tools/generate_sounds.py --placeholders-only`.

Generated clips use your ElevenLabs account and its applicable usage/license terms.
