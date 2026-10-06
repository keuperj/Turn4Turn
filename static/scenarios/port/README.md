# Port

Select **Port** in the mission preparation screen's Theater menu. Like the other
scenarios, it supports all mission objectives, map sizes and day/night lighting.
Restart an already-running server to discover the new scenario.

Three piers connect the industrial quay to a head pier. Open water is excluded
from navigation and spawning; dock boxes and service pedestals provide cover
without closing routes. The warehouses and port offices are enterable, with
stairs and roof access. Moored and offshore watercraft are decorative.

Eleven models from [Marina and Yacht Club](https://3dassets.dev/packs/marina-and-yacht-club)
are bundled locally under CC0. See [the manifest](models/manifest.json) for
individual URLs, dimensions, provenance and checksums, and
[the license](models/LICENSE-port.txt). No asset downloads are needed during play.

Rebuild assets from the repository root:

```sh
.venv/bin/python tools/import_port.py /tmp/port-sources
```

Validate the layout and rendering:

```sh
python3 -m unittest discover -s tests -p test_port.py
.venv/bin/python tests/browser_port.py
.venv/bin/python tests/browser_port.py --webgpu
```

The WebGL browser test writes `/tmp/port.jpg`, a preview with revealed geometry.
