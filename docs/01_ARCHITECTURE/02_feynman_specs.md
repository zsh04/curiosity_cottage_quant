# Service Specification: Feynman (The Wolf)

**Type:** FastStream Application (Docker)
**Role:** The Physics Engine (Kinematics & Thermodynamics)
**Cycle:** <5ms

## Interface

* **Input Topic:** `market.tick.{symbol}` (Websocket Stream)
* **Output Topic:** `physics.forces` (Publishes `ForceVector`)

## Data Structures

### ForceVector Schema

```json
{
  "symbol": "string",
  "timestamp": "integer (unix ms)",
  "mass": "float",
  "friction": "float",
  "entropy": "float",
  "nash_distance": "float",
  "regime": "enum(TRENDING, MEAN_REVERTING)"
}
```

## Memory Strategy (Zero-Allocation)

* **Ring Buffer:** Fixed-size `numpy` arrays (Size=1000) for Price, Volume, and Trade Count.
* **Protocol:**
  * Pre-allocate arrays at `startup`.
  * Use `numpy.roll` to shift data.
  * **NEVER** use `list.append()` or `pd.concat()` in the hot path.
