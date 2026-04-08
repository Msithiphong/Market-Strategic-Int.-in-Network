# Market Strategy in Networks

Bipartite market equilibrium analysis using preferred-seller graphs and constricted-set price updates.

## Requirements

- Python 3.7+
- `networkx`
- `matplotlib` (for `--plot`)

## Install

```bash
pip install networkx matplotlib
```

## Run

```bash
python ./market_strategy.py market.gml --plot --interactive
```

## Flags

| Flag | Description |
|---|---|
| `--plot` | Visualize the graph (and each round if combined with `--interactive`) |
| `--interactive` | Run auction rounds: build preferred-seller graph, find constricted sets, raise prices until equilibrium |

## Graph Assumptions

- GML bipartite graph with two node sets: **sellers** and **buyers**
- Seller nodes must have a `price` attribute (numeric)
- Edges connect buyers to sellers and must have a `valuation` (or `weight`) attribute
- No intra-set edges

## Error Handling

The program exits with a clear message for: missing file, invalid GML, empty graph, non-bipartite structure, and missing attributes.
