# Gameplay screenshots

The README opens with the landing page. Its mission gallery shows the airport,
factory and farm in the full game interface, including the squad, equipment,
orders, minimap and combat feed. The actual Babylon.js WebGL renderer supplies
the normal models, lighting and explosion animation.
These are staged combat views: units are placed on valid unblocked surfaces,
terrain is revealed, and a grenade blast is paused mid-animation so the action
reads clearly in a still image. No generated artwork or painted effects are added.

To reproduce the landing-page PNG and three full-page mission JPEGs
(1600-pixel-wide desktop views):

```sh
.venv/bin/python tools/capture_readme.py
```

The script requires Playwright and its Chromium browser (see
[development setup](../setup.md#setup)). It starts an isolated local server and
closes it after capture; it does not modify a running player's session.

`gameplay.png` is an older capture retained for reference.

[Documentation](../README.md) · [Game overview](../../README.md)
