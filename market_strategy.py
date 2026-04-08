#!/usr/bin/env python3
"""Market strategy analysis on bipartite seller-buyer GML graphs."""

import argparse
import sys
import os

try:
    import networkx as nx
except ImportError:
    print("Error: networkx is required. Install with: pip install networkx")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


def parse_args():
    p = argparse.ArgumentParser(description="Bipartite market strategy analysis")
    p.add_argument("gml", help="Path to a GML bipartite graph file")
    p.add_argument("--plot", action="store_true", help="Plot the graph")
    p.add_argument("--interactive", action="store_true", help="Run interactive auction rounds")
    return p.parse_args()


def load_graph(path):
    if not os.path.isfile(path):
        print(f"Error: file not found: {path}")
        sys.exit(1)
    try:
        G = nx.read_gml(path)
    except Exception as e:
        print(f"Error: could not parse GML file: {e}")
        sys.exit(1)
    if G.number_of_nodes() == 0:
        print("Error: graph is empty")
        sys.exit(1)
    return G


def validate_bipartite(G):
    """Identify sellers (set A) and buyers (set B). Sellers have a 'price' attribute."""
    sellers = set()
    buyers = set()
    for n, data in G.nodes(data=True):
        if "price" in data:
            sellers.add(n)
        else:
            buyers.add(n)
    if not sellers:
        print("Error: no seller nodes found (nodes must have a 'price' attribute)")
        sys.exit(1)
    if not buyers:
        print("Error: no buyer nodes found (nodes without 'price' attribute)")
        sys.exit(1)
    # Verify bipartite structure: edges should go between sellers and buyers
    for u, v in G.edges():
        if not ((u in sellers and v in buyers) or (u in buyers and v in sellers)):
            print(f"Error: edge ({u}, {v}) connects nodes in the same set; expected bipartite graph")
            sys.exit(1)
    return sellers, buyers


def get_prices(G, sellers):
    """Return dict of seller -> current price."""
    return {s: G.nodes[s]["price"] for s in sellers}


def get_valuations(G, buyers, sellers):
    """Return dict of (buyer, seller) -> valuation from edge attributes."""
    vals = {}
    for u, v, data in G.edges(data=True):
        if u in buyers and v in sellers:
            buyer, seller = u, v
        elif v in buyers and u in sellers:
            buyer, seller = v, u
        else:
            continue
        # Use 'valuation' or 'weight' edge attribute
        val = data.get("valuation", data.get("weight", None))
        if val is None:
            print(f"Error: edge ({u}, {v}) missing 'valuation' or 'weight' attribute")
            sys.exit(1)
        vals[(buyer, seller)] = float(val)
    return vals


def preferred_seller_graph(buyers, sellers, valuations, prices):
    """Build preferred-seller graph: each buyer connects to sellers maximizing (valuation - price).
    Returns a dict buyer -> set of preferred sellers."""
    psg = {}
    for b in buyers:
        best_payoff = -float("inf")
        best_sellers = set()
        for s in sellers:
            key = (b, s)
            if key not in valuations:
                continue
            payoff = valuations[key] - prices[s]
            if payoff > best_payoff:
                best_payoff = payoff
                best_sellers = {s}
            elif payoff == best_payoff:
                best_sellers.add(s)
        if best_payoff >= 0:
            psg[b] = best_sellers
        else:
            psg[b] = set()
    return psg


def find_constricted_set(psg, sellers):
    """Find a constricted set S ⊆ buyers such that |N(S)| < |S| using maximum matching.
    Returns (constricted_buyers, their_neighbors) or (None, None) if none exists."""
    # Build a bipartite graph from the preferred-seller graph
    H = nx.Graph()
    buyer_nodes = set()
    seller_nodes = set()
    for b, ss in psg.items():
        if ss:
            buyer_nodes.add(b)
            for s in ss:
                seller_nodes.add(s)
                H.add_edge(b, s)
    if not buyer_nodes:
        return None, None
    # Compute maximum matching
    matching = nx.bipartite.maximum_matching(H, top_nodes=buyer_nodes)
    # Unmatched buyers
    unmatched = buyer_nodes - set(matching.keys())
    if not unmatched:
        return None, None  # Perfect matching exists for preferred-seller graph
    # BFS/DFS from unmatched buyers via alternating paths to find constricted set
    # König's theorem: find the set of buyers reachable from unmatched buyers via alternating paths
    visited_buyers = set()
    visited_sellers = set()
    queue = list(unmatched)
    visited_buyers.update(unmatched)
    while queue:
        node = queue.pop()
        if node in buyer_nodes:
            # Follow unmatched edges to sellers
            for s in psg.get(node, set()):
                if s not in visited_sellers:
                    visited_sellers.add(s)
                    queue.append(s)
        elif node in seller_nodes:
            # Follow matched edge back to buyer
            matched_buyer = matching.get(node)
            if matched_buyer is not None and matched_buyer not in visited_buyers:
                visited_buyers.add(matched_buyer)
                queue.append(matched_buyer)

    # The constricted set is visited_buyers, their neighborhood is visited_sellers
    # Verify constriction: |visited_buyers| > |visited_sellers|
    if len(visited_buyers) > len(visited_sellers):
        return visited_buyers, visited_sellers
    return None, None


def run_interactive(G, sellers, buyers, valuations, do_plot):
    """Run auction rounds: build preferred-seller graph, find constricted sets, raise prices."""
    prices = get_prices(G, sellers)
    round_num = 0
    print("\n=== Initial State ===")
    print_state(sellers, buyers, prices, valuations)
    if do_plot:
        plot_round(G, sellers, buyers, prices, {}, round_num)

    while True:
        round_num += 1
        psg = preferred_seller_graph(buyers, sellers, valuations, prices)
        print(f"\n=== Round {round_num} ===")
        print("Preferred-seller graph:")
        for b in sorted(psg.keys(), key=str):
            prefs = sorted(psg[b], key=str) if psg[b] else ["(none)"]
            print(f"  {b} -> {', '.join(str(x) for x in prefs)}")

        constricted, neighbors = find_constricted_set(psg, sellers)
        if constricted is None:
            print("No constricted set found. Market-clearing prices reached.")
            # Show final matching
            H = nx.Graph()
            for b, ss in psg.items():
                for s in ss:
                    H.add_edge(b, s)
            b_set = {b for b in psg if psg[b]}
            if b_set:
                matching = nx.bipartite.maximum_matching(H, top_nodes=b_set)
                print("\nFinal matching:")
                shown = set()
                for k, v in matching.items():
                    pair = tuple(sorted([str(k), str(v)]))
                    if pair not in shown:
                        shown.add(pair)
                        print(f"  {k} <-> {v}")
            break

        print(f"Constricted set (buyers): {sorted(constricted, key=str)}")
        print(f"Neighbors (sellers):      {sorted(neighbors, key=str)}")

        # Raise prices of neighbor sellers by 1
        for s in neighbors:
            prices[s] += 1
        print("Prices after raise:")
        for s in sorted(sellers, key=str):
            print(f"  {s}: {prices[s]}")

        if do_plot:
            plot_round(G, sellers, buyers, prices, psg, round_num)

    print("\n=== Final Prices ===")
    for s in sorted(sellers, key=str):
        print(f"  {s}: {prices[s]}")

    if do_plot:
        plot_round(G, sellers, buyers, prices, psg, round_num, title="Final")


def print_state(sellers, buyers, prices, valuations):
    print("Sellers and prices:")
    for s in sorted(sellers, key=str):
        print(f"  {s}: price={prices[s]}")
    print("Buyers:")
    for b in sorted(buyers, key=str):
        edges = [(s, valuations[(b, s)]) for s in sorted(sellers, key=str) if (b, s) in valuations]
        edge_str = ", ".join(f"{s}(val={v})" for s, v in edges)
        print(f"  {b}: {edge_str}")


def plot_round(G, sellers, buyers, prices, psg, round_num, title=None):
    if plt is None:
        print("Warning: matplotlib not available, skipping plot")
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    title_str = title or f"Round {round_num}"
    ax.set_title(title_str)

    # Layout: sellers on left, buyers on right
    pos = {}
    s_list = sorted(sellers, key=str)
    b_list = sorted(buyers, key=str)
    for i, s in enumerate(s_list):
        pos[s] = (0, -i)
    for i, b in enumerate(b_list):
        pos[b] = (2, -i)

    # Draw all edges lightly
    nx.draw_networkx_edges(G, pos, alpha=0.2, ax=ax)

    # Highlight preferred-seller edges
    if psg:
        psg_edges = []
        for b, ss in psg.items():
            for s in ss:
                psg_edges.append((b, s))
        if psg_edges:
            nx.draw_networkx_edges(G, pos, edgelist=psg_edges, edge_color="red", width=2, ax=ax)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, nodelist=list(sellers), node_color="lightblue",
                           node_size=600, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=list(buyers), node_color="lightgreen",
                           node_size=600, ax=ax)

    # Labels: sellers show price
    s_labels = {s: f"{s}\np={prices[s]}" for s in sellers}
    b_labels = {b: str(b) for b in buyers}
    labels = {**s_labels, **b_labels}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)

    # Edge labels: valuations
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        val = data.get("valuation", data.get("weight", ""))
        if val != "":
            edge_labels[(u, v)] = str(val)
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7, ax=ax)

    ax.axis("off")
    plt.tight_layout()
    plt.show()


def print_summary(G, sellers, buyers, valuations, prices):
    print(f"Nodes: {G.number_of_nodes()} ({len(sellers)} sellers, {len(buyers)} buyers)")
    print(f"Edges: {G.number_of_edges()}")
    print_state(sellers, buyers, prices, valuations)


def main():
    args = parse_args()
    G = load_graph(args.gml)
    sellers, buyers = validate_bipartite(G)
    valuations = get_valuations(G, buyers, sellers)
    prices = get_prices(G, sellers)

    if args.interactive:
        run_interactive(G, sellers, buyers, valuations, args.plot)
    else:
        print_summary(G, sellers, buyers, valuations, prices)
        if args.plot:
            psg = preferred_seller_graph(buyers, sellers, valuations, prices)
            plot_round(G, sellers, buyers, prices, psg, 0, title="Market Graph")


if __name__ == "__main__":
    main()
