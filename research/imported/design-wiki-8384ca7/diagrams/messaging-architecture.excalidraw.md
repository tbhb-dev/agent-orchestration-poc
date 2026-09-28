---
title: Messaging architecture diagram
summary: "Workloads, bots, and the operator authenticate to one agentd, which alone owns messaging storage and delivery."
type: design
status: draft
tags:
  - area/messaging
  - area/identity
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [Messaging data flow](../messaging-data-flow.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Messaging architecture (proposed) ^t

Workloads ^zlt

Harness + agentw
(host mode) ^h1-lbl

Host wrapper
X.509-SVID mTLS ^g1-lbl

sbx guest
agentw ^h2-lbl

Docker proxy
JWT-SVID bearer ^g2-lbl

agentd (one per host) ^zmt

Shared TLS listener
(mTLS or JWT bearer) ^l-lbl

Authorization: participant,
installation, group policy ^z-lbl

Acceptance transaction
message + deliveries + events ^tx-lbl

SQLite (authoritative) ^s-lbl

Dispatcher +
after-commit wakes ^d-lbl

Around agentd ^zrt

Bots and bridges
(own SVIDs) ^bot-lbl

Operator UI
+ agentctl ^op-lbl

Delivery adapters
(wake hints) ^ad-lbl

Recipient harness ^rh-lbl

Workloads never reach SQLite or a broker. agentd is the only client. ^n

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":230,"y":12,"width":399.3,"height":27.5,"text":"Messaging architecture (proposed)","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"zl","type":"rectangle","x":10,"y":50,"width":190,"height":500,"strokeColor":"#4a9eed","backgroundColor":"#dbe4ff","strokeWidth":1,"opacity":30,"roundness":{"type":3}},{"id":"zlt","type":"text","x":22,"y":58,"width":79.2,"height":20.0,"strokeColor":"#2563eb","text":"Workloads","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"h1","type":"rectangle","x":25,"y":90,"width":160,"height":55,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"h1-lbl","type":"text"}]},{"id":"h1-lbl","type":"text","x":34.6,"y":97.5,"width":140.8,"height":40.0,"text":"Harness + agentw\n(host mode)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"h1"},{"id":"g1","type":"rectangle","x":25,"y":180,"width":160,"height":65,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"g1-lbl","type":"text"}]},{"id":"g1-lbl","type":"text","x":39.0,"y":192.5,"width":132.0,"height":40.0,"text":"Host wrapper\nX.509-SVID mTLS","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"g1"},{"id":"a1","type":"arrow","x":105,"y":145,"width":0,"height":35,"points":[[0,0],[0,35]],"endArrowhead":"arrow"},{"id":"h2","type":"rectangle","x":25,"y":300,"width":160,"height":55,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"h2-lbl","type":"text"}]},{"id":"h2-lbl","type":"text","x":65.4,"y":307.5,"width":79.2,"height":40.0,"text":"sbx guest\nagentw","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"h2"},{"id":"g2","type":"rectangle","x":25,"y":390,"width":160,"height":65,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"g2-lbl","type":"text"}]},{"id":"g2-lbl","type":"text","x":39.0,"y":402.5,"width":132.0,"height":40.0,"text":"Docker proxy\nJWT-SVID bearer","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"g2"},{"id":"a2","type":"arrow","x":105,"y":355,"width":0,"height":35,"points":[[0,0],[0,35]],"endArrowhead":"arrow"},{"id":"zm","type":"rectangle","x":230,"y":50,"width":340,"height":500,"strokeColor":"#8b5cf6","backgroundColor":"#e5dbff","strokeWidth":1,"opacity":30,"roundness":{"type":3}},{"id":"zmt","type":"text","x":245,"y":58,"width":184.8,"height":20.0,"strokeColor":"#6d28d9","text":"agentd (one per host)","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"l","type":"rectangle","x":255,"y":90,"width":290,"height":55,"backgroundColor":"#fff3bf","roundness":{"type":3},"boundElements":[{"id":"l-lbl","type":"text"}]},{"id":"l-lbl","type":"text","x":312.0,"y":97.5,"width":176.0,"height":40.0,"text":"Shared TLS listener\n(mTLS or JWT bearer)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"l"},{"id":"a3","type":"arrow","x":185,"y":212,"width":70,"height":95,"strokeColor":"#8b5cf6","points":[[0,0],[70,-95]],"endArrowhead":"arrow"},{"id":"a4","type":"arrow","x":185,"y":422,"width":70,"height":305,"strokeColor":"#8b5cf6","points":[[0,0],[70,-305]],"endArrowhead":"arrow"},{"id":"z","type":"rectangle","x":255,"y":170,"width":290,"height":55,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"z-lbl","type":"text"}]},{"id":"z-lbl","type":"text","x":281.2,"y":177.5,"width":237.6,"height":40.0,"text":"Authorization: participant,\ninstallation, group policy","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"z"},{"id":"a5","type":"arrow","x":400,"y":145,"width":0,"height":25,"points":[[0,0],[0,25]],"endArrowhead":"arrow"},{"id":"tx","type":"rectangle","x":255,"y":250,"width":290,"height":55,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"tx-lbl","type":"text"}]},{"id":"tx-lbl","type":"text","x":272.4,"y":257.5,"width":255.2,"height":40.0,"text":"Acceptance transaction\nmessage + deliveries + events","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"tx"},{"id":"a6","type":"arrow","x":400,"y":225,"width":0,"height":25,"points":[[0,0],[0,25]],"endArrowhead":"arrow"},{"id":"s","type":"rectangle","x":255,"y":330,"width":290,"height":55,"backgroundColor":"#c3fae8","roundness":{"type":3},"boundElements":[{"id":"s-lbl","type":"text"}]},{"id":"s-lbl","type":"text","x":303.2,"y":347.5,"width":193.6,"height":20.0,"text":"SQLite (authoritative)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s"},{"id":"a7","type":"arrow","x":400,"y":305,"width":0,"height":25,"points":[[0,0],[0,25]],"endArrowhead":"arrow"},{"id":"d","type":"rectangle","x":255,"y":410,"width":290,"height":55,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"d-lbl","type":"text"}]},{"id":"d-lbl","type":"text","x":320.8,"y":417.5,"width":158.4,"height":40.0,"text":"Dispatcher +\nafter-commit wakes","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"d"},{"id":"a8","type":"arrow","x":400,"y":385,"width":0,"height":25,"points":[[0,0],[0,25]],"endArrowhead":"arrow"},{"id":"zr","type":"rectangle","x":600,"y":50,"width":190,"height":500,"strokeColor":"#22c55e","backgroundColor":"#d3f9d8","strokeWidth":1,"opacity":30,"roundness":{"type":3}},{"id":"zrt","type":"text","x":612,"y":58,"width":114.4,"height":20.0,"strokeColor":"#15803d","text":"Around agentd","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"bot","type":"rectangle","x":615,"y":90,"width":160,"height":55,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"bot-lbl","type":"text"}]},{"id":"bot-lbl","type":"text","x":624.6,"y":97.5,"width":140.8,"height":40.0,"text":"Bots and bridges\n(own SVIDs)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"bot"},{"id":"a9","type":"arrow","x":615,"y":117,"width":70,"height":0,"strokeColor":"#f59e0b","points":[[0,0],[-70,0]],"endArrowhead":"arrow"},{"id":"op","type":"rectangle","x":615,"y":180,"width":160,"height":55,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"op-lbl","type":"text"}]},{"id":"op-lbl","type":"text","x":646.6,"y":187.5,"width":96.8,"height":40.0,"text":"Operator UI\n+ agentctl","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"op"},{"id":"a10","type":"arrow","x":615,"y":207,"width":70,"height":77,"strokeColor":"#4a9eed","points":[[0,0],[-70,-77]],"endArrowhead":"arrow"},{"id":"ad","type":"rectangle","x":615,"y":400,"width":160,"height":65,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"ad-lbl","type":"text"}]},{"id":"ad-lbl","type":"text","x":620.2,"y":412.5,"width":149.6,"height":40.0,"text":"Delivery adapters\n(wake hints)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"ad"},{"id":"a11","type":"arrow","x":545,"y":437,"width":70,"height":0,"strokeColor":"#22c55e","points":[[0,0],[70,0]],"endArrowhead":"arrow"},{"id":"rh","type":"rectangle","x":615,"y":490,"width":160,"height":50,"roundness":{"type":3},"boundElements":[{"id":"rh-lbl","type":"text"}]},{"id":"rh-lbl","type":"text","x":620.2,"y":505.0,"width":149.6,"height":20.0,"text":"Recipient harness","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"rh"},{"id":"a12","type":"arrow","x":695,"y":465,"width":0,"height":25,"strokeColor":"#22c55e","points":[[0,0],[0,25]],"endArrowhead":"arrow"},{"id":"n","type":"text","x":150,"y":565,"width":598.4,"height":20.0,"strokeColor":"#757575","text":"Workloads never reach SQLite or a broker. agentd is the only client.","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
