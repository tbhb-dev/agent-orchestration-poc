---
title: Delivery evidence diagram
summary: "The per-recipient receipt milestones, what evidence sets each one, and why null means no evidence."
type: design
status: draft
tags:
  - area/messaging
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [Messaging schema](../messaging-schema.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Delivery evidence per recipient ^t

queued_at ^q-lbl

delivered_at ^d-lbl

seen_at ^s-lbl

replied_at ^r-lbl

agentd writes the
row when the
message is accepted ^nq-lbl

adapter accepted
it, or receive
recorded it ^nd-lbl

evidence it became
turn input
(injecting adapters) ^ns-lbl

explicit reply
with reply_to_id ^nr-lbl

Null means no evidence recorded, not 'unread'. A reply can exist without seen.
Pull delivery and sbx without an injecting adapter usually never record seen. ^f-lbl

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":200,"y":40,"width":375.1,"height":27.5,"text":"Delivery evidence per recipient","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"q","type":"rectangle","x":30,"y":130,"width":160,"height":60,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"q-lbl","type":"text"}]},{"id":"q-lbl","type":"text","x":65.4,"y":148.8,"width":89.1,"height":22.5,"text":"queued_at","fontSize":18,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"q"},{"id":"a1","type":"arrow","x":190,"y":160,"width":30,"height":0,"points":[[0,0],[30,0]],"endArrowhead":"arrow"},{"id":"d","type":"rectangle","x":220,"y":130,"width":160,"height":60,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"d-lbl","type":"text"}]},{"id":"d-lbl","type":"text","x":240.6,"y":148.8,"width":118.8,"height":22.5,"text":"delivered_at","fontSize":18,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"d"},{"id":"a2","type":"arrow","x":380,"y":160,"width":30,"height":0,"points":[[0,0],[30,0]],"endArrowhead":"arrow"},{"id":"s","type":"rectangle","x":410,"y":130,"width":160,"height":60,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"s-lbl","type":"text"}]},{"id":"s-lbl","type":"text","x":455.4,"y":148.8,"width":69.3,"height":22.5,"text":"seen_at","fontSize":18,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s"},{"id":"a3","type":"arrow","x":570,"y":160,"width":30,"height":0,"points":[[0,0],[30,0]],"endArrowhead":"arrow"},{"id":"r","type":"rectangle","x":600,"y":130,"width":160,"height":60,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"r-lbl","type":"text"}]},{"id":"r-lbl","type":"text","x":630.5,"y":148.8,"width":99.0,"height":22.5,"text":"replied_at","fontSize":18,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"r"},{"id":"nq","type":"rectangle","x":30,"y":230,"width":160,"height":110,"strokeColor":"#f59e0b","backgroundColor":"#fff3bf","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"nq-lbl","type":"text"}]},{"id":"nq-lbl","type":"text","x":26.4,"y":255.0,"width":167.2,"height":60.0,"text":"agentd writes the\nrow when the\nmessage is accepted","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"nq"},{"id":"nd","type":"rectangle","x":220,"y":230,"width":160,"height":110,"strokeColor":"#f59e0b","backgroundColor":"#fff3bf","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"nd-lbl","type":"text"}]},{"id":"nd-lbl","type":"text","x":229.6,"y":255.0,"width":140.8,"height":60.0,"text":"adapter accepted\nit, or receive\nrecorded it","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"nd"},{"id":"ns","type":"rectangle","x":410,"y":230,"width":160,"height":110,"strokeColor":"#f59e0b","backgroundColor":"#fff3bf","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"ns-lbl","type":"text"}]},{"id":"ns-lbl","type":"text","x":402.0,"y":255.0,"width":176.0,"height":60.0,"text":"evidence it became\nturn input\n(injecting adapters)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"ns"},{"id":"nr","type":"rectangle","x":600,"y":230,"width":160,"height":110,"strokeColor":"#f59e0b","backgroundColor":"#fff3bf","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"nr-lbl","type":"text"}]},{"id":"nr-lbl","type":"text","x":609.6,"y":265.0,"width":140.8,"height":40.0,"text":"explicit reply\nwith reply_to_id","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"nr"},{"id":"a4","type":"arrow","x":300,"y":195,"width":380,"height":10,"strokeColor":"#757575","strokeWidth":1,"strokeStyle":"dashed","points":[[0,0],[80,-10],[300,-10],[380,0]],"endArrowhead":"arrow"},{"id":"f","type":"rectangle","x":30,"y":390,"width":730,"height":80,"strokeColor":"#ef4444","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"f-lbl","type":"text"}]},{"id":"f-lbl","type":"text","x":51.8,"y":410.0,"width":686.4,"height":40.0,"text":"Null means no evidence recorded, not 'unread'. A reply can exist without seen.\nPull delivery and sbx without an injecting adapter usually never record seen.","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"f"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
