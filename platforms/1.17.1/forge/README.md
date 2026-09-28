# Forge 1.17.1 adapter

This independent target uses Forge 37.1.1 with the parent Architectury Loom build,
Java 16 bytecode and runtime, and GPL-3.0-only first-party sources. Forge 37's
`fmllegacy.network` and `fmlserverevents` API names are intentional.

The payload listener captures the original connection and packet listener before
queueing work. Server handling and delayed client reports require those exact
objects to remain current and connected. Both directions retain the raw
`qzguard:main` bytes, capped at 30,000 bytes. Client classes are registered only by
Forge's physical-client event subscriber. Command isolation uses the parent's
required `CommandGate117Mixin` and a generated refmap.

`check` runs the parent's command parser smoke plus this target's 15 production
connection-dispatch checks and actual legacy custom-payload packet writers.
These checks do not establish dedicated-server, rendered-client, or gameplay
compatibility; those require separate runs against the exact remapped JAR.
