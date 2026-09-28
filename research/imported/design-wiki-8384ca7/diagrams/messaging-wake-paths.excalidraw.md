---
title: Notification-first wake paths diagram
summary: "Proposed harness wake paths for Codex, Claude hooks, Claude MCP channels, and pull-only backends."
type: design
status: draft
tags:
  - area/messaging
  - area/orchestration
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [Harness delivery and push fallbacks](../messaging-delivery.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Notification-first wake paths (proposed) ^t

agentd
dispatcher ^dp-lbl

Codex native queue
next turn after busy turn ^p1-lbl

hint ^a1-lbl

Claude asyncRewake hook
joins turn at tool boundary ^p2-lbl

Claude MCP channel
allowlist or dev flag ^p3-lbl

sbx or no adapter
pull only ^p4-lbl

Model turn runs
agentw message receive ^tn-lbl

authenticated receive returns content ^r-lbl

Push only says
'check your inbox'.
Content arrives
through receive. ^nt-lbl

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":180,"y":15,"width":484.0,"height":27.5,"text":"Notification-first wake paths (proposed)","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"dp","type":"rectangle","x":20,"y":250,"width":150,"height":80,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"dp-lbl","type":"text"}]},{"id":"dp-lbl","type":"text","x":45.5,"y":267.5,"width":99.0,"height":45.0,"text":"agentd\ndispatcher","fontSize":18,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"dp"},{"id":"p1","type":"rectangle","x":250,"y":60,"width":240,"height":70,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"p1-lbl","type":"text"}]},{"id":"p1-lbl","type":"text","x":260.0,"y":75.0,"width":220.0,"height":40.0,"text":"Codex native queue\nnext turn after busy turn","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"p1"},{"id":"a1","type":"arrow","x":170,"y":275,"width":80,"height":180,"points":[[0,0],[80,-180]],"endArrowhead":"arrow","boundElements":[{"id":"a1-lbl","type":"text"}]},{"id":"a1-lbl","type":"text","x":194.6,"y":176.2,"width":30.8,"height":17.5,"text":"hint","fontSize":14,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"a1"},{"id":"p2","type":"rectangle","x":250,"y":170,"width":240,"height":70,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"p2-lbl","type":"text"}]},{"id":"p2-lbl","type":"text","x":251.2,"y":185.0,"width":237.6,"height":40.0,"text":"Claude asyncRewake hook\njoins turn at tool boundary","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"p2"},{"id":"a2","type":"arrow","x":170,"y":285,"width":80,"height":80,"points":[[0,0],[80,-80]],"endArrowhead":"arrow"},{"id":"p3","type":"rectangle","x":250,"y":280,"width":240,"height":70,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"p3-lbl","type":"text"}]},{"id":"p3-lbl","type":"text","x":277.6,"y":295.0,"width":184.8,"height":40.0,"text":"Claude MCP channel\nallowlist or dev flag","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"p3"},{"id":"a3","type":"arrow","x":170,"y":300,"width":80,"height":15,"points":[[0,0],[80,15]],"endArrowhead":"arrow"},{"id":"p4","type":"rectangle","x":250,"y":390,"width":240,"height":70,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"p4-lbl","type":"text"}]},{"id":"p4-lbl","type":"text","x":295.2,"y":405.0,"width":149.6,"height":40.0,"text":"sbx or no adapter\npull only","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"p4"},{"id":"a4","type":"arrow","x":170,"y":315,"width":80,"height":110,"strokeStyle":"dashed","points":[[0,0],[80,110]],"endArrowhead":"arrow"},{"id":"tn","type":"rectangle","x":560,"y":230,"width":210,"height":85,"backgroundColor":"#fff3bf","roundness":{"type":3},"boundElements":[{"id":"tn-lbl","type":"text"}]},{"id":"tn-lbl","type":"text","x":568.2,"y":252.5,"width":193.6,"height":40.0,"text":"Model turn runs\nagentw message receive","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"tn"},{"id":"b1","type":"arrow","x":490,"y":95,"width":90,"height":135,"points":[[0,0],[90,135]],"endArrowhead":"arrow"},{"id":"b2","type":"arrow","x":490,"y":205,"width":70,"height":40,"points":[[0,0],[70,40]],"endArrowhead":"arrow"},{"id":"b3","type":"arrow","x":490,"y":315,"width":70,"height":10,"points":[[0,0],[70,-10]],"endArrowhead":"arrow"},{"id":"b4","type":"arrow","x":490,"y":425,"width":90,"height":110,"strokeStyle":"dashed","points":[[0,0],[90,-110]],"endArrowhead":"arrow"},{"id":"r","type":"arrow","x":665,"y":315,"width":570,"height":210,"strokeColor":"#22c55e","points":[[0,0],[0,210],[-570,210],[-570,15]],"endArrowhead":"arrow","boundElements":[{"id":"r-lbl","type":"text"}]},{"id":"r-lbl","type":"text","x":237.5,"y":516.2,"width":284.9,"height":17.5,"strokeColor":"#22c55e","text":"authenticated receive returns content","fontSize":14,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"r"},{"id":"nt","type":"rectangle","x":560,"y":60,"width":210,"height":110,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"nt-lbl","type":"text"}]},{"id":"nt-lbl","type":"text","x":581.4,"y":75.0,"width":167.2,"height":80.0,"text":"Push only says\n'check your inbox'.\nContent arrives\nthrough receive.","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"nt"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
