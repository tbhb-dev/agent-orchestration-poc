---
title: Send to delivery stages diagram
summary: "The six proposed stages from authenticated send through commit, notification, delivery, and seen or replied evidence."
type: design
status: draft
tags:
  - area/messaging
  - scope/destination
updated: 2026-09-27
excalidraw-plugin: parsed
---
Diagram for [Messaging data flow](../messaging-data-flow.md). It illustrates the page's content as of 2026-09-27, which is mostly **proposed**; the linked page is authoritative for what is decided. Claude drew it at the operator's request. Open it in Obsidian with the Excalidraw plugin to view or edit.

# Excalidraw Data

## Text Elements
Send to delivery: six stages ^t

1. Send
agentw + client_message_id ^s1-lbl

2. Authenticate
+ authorize ^s2-lbl

3. Resolve + commit
one transaction ^s3-lbl

4. Notify after commit
(hints only) ^s4-lbl

5. Deliver
adapter or receive ^s5-lbl

6. Seen + replied
evidence-backed ^s6-lbl

Lost response? Retry
with the same key ^n1-lbl

No side effects
before commit ^n2-lbl

Seen only with evidence
the message was turn input ^n3-lbl

Push and pull share
one dispatcher ^n4-lbl

Wakeups are hints.
Crash? Reconcile pending rows ^n5-lbl

Accepted means durable. It does not mean delivered, seen, or acted on. ^f

%%
## Drawing
```json
{"type":"excalidraw","version":2,"source":"https://github.com/zsviczian/obsidian-excalidraw-plugin","elements":[{"id":"t","type":"text","x":230,"y":20,"width":338.8,"height":27.5,"text":"Send to delivery: six stages","fontSize":22,"fontFamily":5,"textAlign":"left","verticalAlign":"top"},{"id":"s1","type":"rectangle","x":30,"y":80,"width":210,"height":80,"backgroundColor":"#a5d8ff","roundness":{"type":3},"boundElements":[{"id":"s1-lbl","type":"text"}]},{"id":"s1-lbl","type":"text","x":20.6,"y":100.0,"width":228.8,"height":40.0,"text":"1. Send\nagentw + client_message_id","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s1"},{"id":"a1","type":"arrow","x":240,"y":120,"width":55,"height":0,"points":[[0,0],[55,0]],"endArrowhead":"arrow"},{"id":"s2","type":"rectangle","x":295,"y":80,"width":210,"height":80,"backgroundColor":"#ffd8a8","roundness":{"type":3},"boundElements":[{"id":"s2-lbl","type":"text"}]},{"id":"s2-lbl","type":"text","x":334.0,"y":100.0,"width":132.0,"height":40.0,"text":"2. Authenticate\n+ authorize","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s2"},{"id":"a2","type":"arrow","x":505,"y":120,"width":55,"height":0,"points":[[0,0],[55,0]],"endArrowhead":"arrow"},{"id":"s3","type":"rectangle","x":560,"y":80,"width":210,"height":80,"backgroundColor":"#d0bfff","roundness":{"type":3},"boundElements":[{"id":"s3-lbl","type":"text"}]},{"id":"s3-lbl","type":"text","x":581.4,"y":100.0,"width":167.2,"height":40.0,"text":"3. Resolve + commit\none transaction","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s3"},{"id":"a3","type":"arrow","x":665,"y":160,"width":0,"height":120,"points":[[0,0],[0,120]],"endArrowhead":"arrow"},{"id":"s4","type":"rectangle","x":560,"y":280,"width":210,"height":80,"backgroundColor":"#c3fae8","roundness":{"type":3},"boundElements":[{"id":"s4-lbl","type":"text"}]},{"id":"s4-lbl","type":"text","x":568.2,"y":300.0,"width":193.6,"height":40.0,"text":"4. Notify after commit\n(hints only)","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s4"},{"id":"a4","type":"arrow","x":560,"y":320,"width":55,"height":0,"points":[[0,0],[-55,0]],"endArrowhead":"arrow"},{"id":"s5","type":"rectangle","x":295,"y":280,"width":210,"height":80,"backgroundColor":"#b2f2bb","roundness":{"type":3},"boundElements":[{"id":"s5-lbl","type":"text"}]},{"id":"s5-lbl","type":"text","x":320.8,"y":300.0,"width":158.4,"height":40.0,"text":"5. Deliver\nadapter or receive","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s5"},{"id":"a5","type":"arrow","x":295,"y":320,"width":55,"height":0,"points":[[0,0],[-55,0]],"endArrowhead":"arrow"},{"id":"s6","type":"rectangle","x":30,"y":280,"width":210,"height":80,"backgroundColor":"#fff3bf","roundness":{"type":3},"boundElements":[{"id":"s6-lbl","type":"text"}]},{"id":"s6-lbl","type":"text","x":60.2,"y":300.0,"width":149.6,"height":40.0,"text":"6. Seen + replied\nevidence-backed","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"s6"},{"id":"n1","type":"rectangle","x":20,"y":180,"width":230,"height":60,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"n1-lbl","type":"text"}]},{"id":"n1-lbl","type":"text","x":47.0,"y":190.0,"width":176.0,"height":40.0,"text":"Lost response? Retry\nwith the same key","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"n1"},{"id":"n2","type":"rectangle","x":285,"y":180,"width":230,"height":60,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"n2-lbl","type":"text"}]},{"id":"n2-lbl","type":"text","x":334.0,"y":190.0,"width":132.0,"height":40.0,"text":"No side effects\nbefore commit","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"n2"},{"id":"n3","type":"rectangle","x":20,"y":390,"width":230,"height":70,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"n3-lbl","type":"text"}]},{"id":"n3-lbl","type":"text","x":20.6,"y":405.0,"width":228.8,"height":40.0,"text":"Seen only with evidence\nthe message was turn input","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"n3"},{"id":"n4","type":"rectangle","x":285,"y":390,"width":230,"height":70,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"n4-lbl","type":"text"}]},{"id":"n4-lbl","type":"text","x":316.4,"y":405.0,"width":167.2,"height":40.0,"text":"Push and pull share\none dispatcher","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"n4"},{"id":"n5","type":"rectangle","x":550,"y":390,"width":230,"height":70,"strokeColor":"#f59e0b","strokeWidth":1,"roundness":{"type":3},"boundElements":[{"id":"n5-lbl","type":"text"}]},{"id":"n5-lbl","type":"text","x":537.4,"y":405.0,"width":255.2,"height":40.0,"text":"Wakeups are hints.\nCrash? Reconcile pending rows","fontSize":16,"fontFamily":5,"textAlign":"center","verticalAlign":"middle","containerId":"n5"},{"id":"f","type":"text","x":130,"y":500,"width":616.0,"height":20.0,"strokeColor":"#757575","text":"Accepted means durable. It does not mean delivered, seen, or acted on.","fontSize":16,"fontFamily":5,"textAlign":"left","verticalAlign":"top"}],"appState":{"gridSize":null,"viewBackgroundColor":"#ffffff"},"files":{}}
```
%%
