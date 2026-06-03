# Memory OS — rulebook.md integration

> **Version 2** — amended for Execution Agent protocol compatibility.

The Hermes Agent's rulebook (`~/.hermes/rulebook.md`) uses the **Execution Agent
protocol** — a structured document with rules for execution discipline, not a
generic append-only document. Standalone sections pasted into it break the
protocol's structure.

Instead, apply the **amendments** documented in
[`modifications/execution-agent-protocol.md`](../modifications/execution-agent-protocol.md).
These are formatted as insertions at specific points in the protocol:

| Amendment | Insert after | Content |
|---|---|---|
| Memory Architecture Integration | `## Memory Architecture` | Layer lookup guide + fact feedback rule |
| Memory OS Infrastructure | `## Defaults` | Docker services, env vars, health endpoints |
| Mandatory Verifications | `## Ground Truth` | Infrastructure health checks (level 5) |

Each amendment starts with `<!-- Memory OS amendment — do not duplicate -->`.
Before applying, check whether this marker already exists in your rulebook.
If it does, skip that amendment.
