---
title: Participants and authority diagram
summary: "Participant kinds from SPIFFE ID paths, capabilities versus permissions, and scopes for installations."
type: design
status: draft
tags:
  - area/identity
  - area/security
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [SPIFFE workload authentication](../spiffe-mtls-authentication.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Participants and authority ^t

Kind comes from the SPIFFE ID path ^st

Workload
/workloads/... ^k1-lbl

Bot (bridges too)
/bots/... ^k2-lbl

Operator
/operators/... ^k3-lbl

Capabilities: what it CAN do
intrinsic: harness, model, backend
restricted: shell off, read-only
enforced by harness or runtime ^cap-lbl

Permissions: what it MAY do
installation = scope + grants
roles and group policy
enforced by agentd ^per-lbl

Effective ability =
capabilities AND permissions ^ef-lbl

Scopes today: host > group > conversation
Projects and collections later; containment is a function, not a tree walk ^sc-lbl

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":220,"y":10,"width":314.6,"height":27.5,"text":"Participants and authority","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"st","type":"text","x":245,"y":45,"width":299.2,"height":20.0,"strokeColor":"#757575","text":"Kind comes from the SPIFFE ID path","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"k1","type":"rectangle","x":40,"y":75,"width":200,"height":60,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"k1-lbl","type":"text"}]},{"id":"k1-lbl","type":"text","x":78.4,"y":85.0,"width":123.2,"height":40.0,"text":"Workload\n/workloads/...","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"k1"},{"id":"k2","type":"rectangle","x":300,"y":75,"width":200,"height":60,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"k2-lbl","type":"text"}]},{"id":"k2-lbl","type":"text","x":325.2,"y":85.0,"width":149.6,"height":40.0,"text":"Bot (bridges too)\n/bots/...","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"k2"},{"id":"k3","type":"rectangle","x":560,"y":75,"width":200,"height":60,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"k3-lbl","type":"text"}]},{"id":"k3-lbl","type":"text","x":598.4,"y":85.0,"width":123.2,"height":40.0,"text":"Operator\n/operators/...","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"k3"},{"id":"cap","type":"rectangle","x":40,"y":190,"width":330,"height":140,"backgroundColor":"#c3fae8","roundness":{"type":3},"boundElements":[{"id":"cap-lbl","type":"text"}]},{"id":"cap-lbl","type":"text","x":55.4,"y":220.0,"width":299.2,"height":80.0,"text":"Capabilities: what it CAN do\nintrinsic: harness, model, backend\nrestricted: shell off, read-only\nenforced by harness or runtime","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"cap"},{"id":"per","type":"rectangle","x":430,"y":190,"width":330,"height":140,"backgroundColor":"#fff3bf","roundness":{"type":3},"boundElements":[{"id":"per-lbl","type":"text"}]},{"id":"per-lbl","type":"text","x":467.4,"y":220.0,"width":255.2,"height":80.0,"text":"Permissions: what it MAY do\ninstallation = scope + grants\nroles and group policy\nenforced by agentd","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"per"},{"id":"a1","type":"arrow","x":400,"y":135,"width":195,"height":55,"points":[[0,0],[-195,55]],"endArrowhead":"arrow"},{"id":"a2","type":"arrow","x":400,"y":135,"width":195,"height":55,"points":[[0,0],[195,55]],"endArrowhead":"arrow"},{"id":"ef","type":"rectangle","x":230,"y":380,"width":340,"height":70,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"ef-lbl","type":"text"}]},{"id":"ef-lbl","type":"text","x":276.8,"y":395.0,"width":246.4,"height":40.0,"text":"Effective ability =\ncapabilities AND permissions","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"ef"},{"id":"a3","type":"arrow","x":205,"y":330,"width":110,"height":50,"strokeColor":"#06b6d4","points":[[0,0],[110,50]],"endArrowhead":"arrow"},{"id":"a4","type":"arrow","x":595,"y":330,"width":110,"height":50,"strokeColor":"#f59e0b","points":[[0,0],[-110,50]],"endArrowhead":"arrow"},{"id":"sc","type":"rectangle","x":40,"y":490,"width":720,"height":70,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"sc-lbl","type":"text"}]},{"id":"sc-lbl","type":"text","x":74.4,"y":505.0,"width":651.2,"height":40.0,"text":"Scopes today: host > group > conversation\nProjects and collections later; containment is a function, not a tree walk","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"sc"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
