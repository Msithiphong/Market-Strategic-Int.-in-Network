# Market Strategy in Networks

## Requirements

- Python 3.7+
- `networkx`
- `matplotlib` (for `--plot`)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python ./market_strategy.py market.gml --plot --interactive
```

## Flags

- `--plot`: Visualize the graph (and each round if combined with `--interactive`)
- `--interactive`: Run auction rounds: build preferred-seller graph, find constricted sets, raise prices until equilibrium

