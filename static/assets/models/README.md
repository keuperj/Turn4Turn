# Character asset

`soldier.glb` is the shared comparison soldier, converted from Quaternius
Soldier_Male.fbx in the CC0 Ultimate Animated Character Pack:
https://quaternius.com/packs/ultimatedanimatedcharacter.html

Converted with Three.js FBXLoader/GLTFExporter during asset authoring (not runtime).
Materials converted to rough PBR, dark cloth colors brightened; FBX skinning
weights limited to four per vertex. Source and authoring utility remain under
`static/comparison/`. Babylon.js renders and animates this asset in the game.

The soldier is stylized. Idle/walk clips are authored skeletal animations;
kneeling and prone are adapted poses, not bespoke motion-captured animations.
Team tints and separately modeled equipped weapons are applied at runtime.
