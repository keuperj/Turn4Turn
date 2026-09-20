# Setup and hosting

[Documentation](README.md) · [Back to the game](../README.md)

## Requirements

- Python 3.10 or newer
- A modern browser with WebGPU or WebGL 2 enabled
- No Python packages for normal play

The landing page opens without downloading the game engine or mission assets.
The first mission loads the renderer, models, textures and sounds behind a progress
panel with rotating equipment artwork, descriptions and authoritative game stats.
Preview artwork is fetched and decoded before larger mission resources, so the
field guide only displays ready images. Audio and renderer loading overlap.
Later missions reuse loaded assets. The cards respect reduced-motion preferences.
Static resources support gzip and ETag revalidation; unchanged downloads are reused
across page reloads, while edited files receive fresh responses. Player API data
remains uncached. Gzip reduces the bundled engine/model payload from about 27 MiB
to 5.4 MiB; actual loading time also depends on the connection and rendering device.

The landing page runs a bounded capability check. Babylon.js selects WebGPU only
after adapter, device, compute, and canvas stages pass; WebGL 2 remains the
default when the check is unavailable, fails, or times out. WebGPU initialization
failures also fall back to WebGL 2.

## Setup

Clone the repository and start the server:

```sh
git clone https://github.com/keuperj/Turn4Turn.git
cd Turn4Turn
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

For development and CI, create the complete Conda environment with:

```sh
conda env create --file environment.yml
conda activate turn4turn
python -m playwright install chromium
```

The GitHub Actions Conda workflow uses the same `environment.yml` when running
lint and tests. The separate Playwright install command downloads Chromium for
local browser and WebGPU diagnostics; it is not needed for the Python unit
tests.

To make the game reachable from another computer, bind the server to the
machine's network IP:

```sh
python3 server.py --host 192.168.1.50
```

Alternatively, listen on all network interfaces with `--host 0.0.0.0`. Remote
players should open the server machine's actual IP address (for example,
`http://192.168.1.50:8000`), not `0.0.0.0`.

To enable HTTPS, pass `--https` and preferably bind to the exact name or IP that
players will open:

```sh
python3 server.py --host 192.168.1.50 --https
```

The server uses the `openssl` command to create a one-year self-signed
certificate in `.certs/`, then reuses it on later starts. Open
`https://192.168.1.50:8000` and accept the browser's warning for this local
certificate. In Firefox, choose **Advanced…** and **Accept the Risk and
Continue**. For repeated use, import the generated `.crt` file into the client
system or browser trust store. A public server should use a certificate from a
trusted certificate authority instead.

## Server configuration

Command-line options:

| Option | Default | Description |
| --- | ---: | --- |
| `--host ADDRESS` | `127.0.0.1` | IP address or host name to bind to. Use `0.0.0.0` for all interfaces. |
| `--port PORT` | `8000` | HTTP port. |
| `--max-players COUNT` | `10` | Maximum number of active, isolated player sessions. Must be at least 1. |
| `--https` | off | Generate or reuse a local self-signed certificate and serve HTTPS. |

Example:

```sh
python3 server.py --host 0.0.0.0 --port 8080 --max-players 20 --https
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

Turn4Turn asks for consent once, before creating its player cookies. Returning
players with valid ID and name cookies reconnect automatically, including after
a server restart or idle timeout. Their identity and consent are restored; an
expired or restarted in-memory game starts fresh. The dialog appears again if
the identifying cookies have expired, been cleared, or are invalid.

| Cookie | Contents |
| --- | --- |
| `turn4turn_user` | Random player ID; marked `HttpOnly` and `SameSite=Lax`. |
| `turn4turn_name` | The chosen display name. |
| `turn4turn_campaign` | Selected campaign and independent mission index / active seed for all three campaigns. Legacy Turning Point progress migrates to Medium. |
| `turn4turn_loadout` | Optional default equipment selection. |

Cookies are scoped to the game path and are not sent to third-party services.
The loadout cookie is created only when **Use this equipment selection as my
default loadout** is enabled during mission preparation. Clearing site data
resets the browser identity and saved preferences.
