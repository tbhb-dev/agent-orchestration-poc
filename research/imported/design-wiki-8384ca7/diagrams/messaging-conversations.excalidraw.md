---
title: Conversation model diagram
summary: "Groups govern, DMs fan out on write, channels fan out on read, and threads inherit delivery from their parent."
type: design
status: draft
tags:
  - area/messaging
  - area/groups
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [Messaging schema](../messaging-schema.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Conversations: decided set, proposed mechanics ^t

Group: authority + policy scope
roles, installations, who may post ^g-lbl

DM (fixed participant set)
Fan-out on write
Everyone gets everything ^dm-lbl

policy ^a1-lbl

Channel (owned by one group)
Fan-out on read
Ambient posts, member cursors ^ch-lbl

owns ^a2-lbl

DM thread
all DM participants get replies ^dt-lbl

Channel thread
participants get inbox,
others read ambiently ^ct-lbl

Inbox: delivery rows,
receipts, wakes ^in-lbl

mentions ^a6-lbl

Ambient history
no wakes ^am-lbl

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":150,"y":15,"width":556.6,"height":27.5,"text":"Conversations: decided set, proposed mechanics","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"g","type":"rectangle","x":200,"y":60,"width":400,"height":65,"strokeColor":"#f59e0b","backgroundColor":"#fff3bf","roundness":{"type":3},"boundElements":[{"id":"g-lbl","type":"text"}]},{"id":"g-lbl","type":"text","x":250.4,"y":72.5,"width":299.2,"height":40.0,"text":"Group: authority + policy scope\nroles, installations, who may post","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"g"},{"id":"dm","type":"rectangle","x":40,"y":175,"width":320,"height":100,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"dm-lbl","type":"text"}]},{"id":"dm-lbl","type":"text","x":85.6,"y":195.0,"width":228.8,"height":60.0,"text":"DM (fixed participant set)\nFan-out on write\nEveryone gets everything","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"dm"},{"id":"a1","type":"arrow","x":300,"y":125,"width":100,"height":50,"strokeStyle":"dashed","points":[[0,0],[-100,50]],"endArrowhead":"arrow","boundElements":[{"id":"a1-lbl","type":"text"}]},{"id":"a1-lbl","type":"text","x":226.9,"y":141.2,"width":46.2,"height":17.5,"text":"policy","fontSize":14,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"a1"},{"id":"ch","type":"rectangle","x":440,"y":175,"width":320,"height":100,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"ch-lbl","type":"text"}]},{"id":"ch-lbl","type":"text","x":472.4,"y":195.0,"width":255.2,"height":60.0,"text":"Channel (owned by one group)\nFan-out on read\nAmbient posts, member cursors","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"ch"},{"id":"a2","type":"arrow","x":500,"y":125,"width":100,"height":50,"strokeStyle":"dashed","points":[[0,0],[100,50]],"endArrowhead":"arrow","boundElements":[{"id":"a2-lbl","type":"text"}]},{"id":"a2-lbl","type":"text","x":534.6,"y":141.2,"width":30.8,"height":17.5,"text":"owns","fontSize":14,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"a2"},{"id":"dt","type":"rectangle","x":60,"y":320,"width":280,"height":75,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"dt-lbl","type":"text"}]},{"id":"dt-lbl","type":"text","x":63.6,"y":337.5,"width":272.8,"height":40.0,"text":"DM thread\nall DM participants get replies","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"dt"},{"id":"a3","type":"arrow","x":200,"y":275,"width":0,"height":45,"points":[[0,0],[0,45]],"endArrowhead":"arrow"},{"id":"ct","type":"rectangle","x":460,"y":320,"width":280,"height":75,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"ct-lbl","type":"text"}]},{"id":"ct-lbl","type":"text","x":498.8,"y":327.5,"width":202.4,"height":60.0,"text":"Channel thread\nparticipants get inbox,\nothers read ambiently","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"ct"},{"id":"a4","type":"arrow","x":600,"y":275,"width":0,"height":45,"points":[[0,0],[0,45]],"endArrowhead":"arrow"},{"id":"in","type":"rectangle","x":200,"y":460,"width":300,"height":70,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"in-lbl","type":"text"}]},{"id":"in-lbl","type":"text","x":257.6,"y":475.0,"width":184.8,"height":40.0,"text":"Inbox: delivery rows,\nreceipts, wakes","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"in"},{"id":"a5","type":"arrow","x":200,"y":395,"width":100,"height":65,"strokeColor":"#f59e0b","points":[[0,0],[100,65]],"endArrowhead":"arrow"},{"id":"a6","type":"arrow","x":540,"y":395,"width":90,"height":65,"strokeColor":"#f59e0b","points":[[0,0],[-90,65]],"endArrowhead":"arrow","boundElements":[{"id":"a6-lbl","type":"text"}]},{"id":"a6-lbl","type":"text","x":464.2,"y":418.8,"width":61.6,"height":17.5,"strokeColor":"#f59e0b","text":"mentions","fontSize":14,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"a6"},{"id":"am","type":"rectangle","x":560,"y":460,"width":200,"height":70,"backgroundColor":"#c3fae8","roundness":{"type":3},"boundElements":[{"id":"am-lbl","type":"text"}]},{"id":"am-lbl","type":"text","x":594.0,"y":475.0,"width":132.0,"height":40.0,"text":"Ambient history\nno wakes","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"am"},{"id":"a7","type":"arrow","x":680,"y":395,"width":0,"height":65,"strokeColor":"#06b6d4","points":[[0,0],[0,65]],"endArrowhead":"arrow"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
