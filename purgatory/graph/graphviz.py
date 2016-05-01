"""Generate a GraphViz graph (pygraphviz.AGraph) from Purgatory's graph."""


def _edged_to_weight(node_to_layer, from_node, to_node):
    """Returns the edge weight depending on the layer distance."""
    from_layer = node_to_layer[from_node]
    to_layer = node_to_layer[to_node]
    layer_diff = to_layer - from_layer
    weight = 4  # Default edge weight for GraphViz's dot is 1.
    if layer_diff == 0:
        weight = 36
    elif layer_diff == 1:
        weight = 25
    elif layer_diff == 2:
        weight = 16
    elif layer_diff == 3:
        weight = 9
    return weight


def graph_to_agraph(graph):
    """Returns the GraphViz graph for the given Purgatory graph.

    This function will reset all graph members marked as deleted and hence the
    resulting GraphViz graph will contain all graph members.

    Args:
        graph: Purgatory graph (purgatory.graph.Graph).

    Returns:
        GraphViz graph (pygraphviz.AGraph).
    """
    # Try to import pygraphviz.
    try:
        import pygraphviz
    except ImportError:  # pragma: no cover
        raise ImportError(
            "No module named 'pygraphviz'. To install 'pygraphviz' run "
            "'sudo apt install python3-pygraphviz'.")

    # Use the full graph. Laying out partial graphs is currently not supported.
    graph.unmark_deleted()

    # Identify the layers of the graph and then reset the graph again.
    # Note: This also build an index of nodes to the respective layer.
    # TODO(MS): Move the disection into layers to a separate method of the
    # graph object.
    layers = []
    layer_index = 0
    node_to_layer = {}
    while graph.nodes:
        layer = list(graph.leafs_flat)
        layer.sort()
        if layer:
            layers.append(layer)
        for node in layer:
            node.mark_deleted()
            node_to_layer[node] = layer_index
        layer_index += 1

    # Reset the graph for the clustering of the graph.
    graph.unmark_deleted()

    # Cluster the graph by taking the leafs, simulating the removal for each
    # leaf and then ignoring all the nodes that would have been removed for the
    # next round. This way cluster layer by cluster layer will be ignored until
    # the whole graph has been clustered.
    # TODO(MS): Move the disection into clusters to a separate method of the
    # graph object.
    clusters = []  # [(index, nodes, leaf_nodes, leaf_cluster), ...]
    cluster_index = 0
    ignore = frozenset()  # Nodes that will be ignored in the current round.
    ignore_next_round = set()  # Nodes that will be ignored in the next round.
    node_to_cluster_index = {}
    while graph.nodes:
        # Step #1 - Get leafs of the current graph (graph - ignore).
        leafs = list(graph.leafs)
        for index in range(len(leafs)):  # noqa  # pylint: disable=consider-using-enumerate
            leafs[index] = list(leafs[index])  # Set to list conversion.
            leafs[index].sort()
        leafs.sort()

        # Step #2 - Simulate the removal for each leaf. The graph will be reset
        # to the current graph (graph - ignore) after each simulated removal.
        # All the nodes identified during the simulated removal for a leaf form
        # a cluster.
        # Note #1: All nodes identified during the simulated removal will be
        # ignored in the next round.
        # Note #2: This also builds an index of the nodes to the respective
        # cluster they are in.
        for leaf_nodes in leafs:
            before_deleted = graph.deleted_nodes
            # TODO(MS): Add proper exceptions.
            if set(leaf_nodes) & before_deleted:  # pragma: no cover
                raise RuntimeError("Leaf node already marked deleted!")
            if set(leaf_nodes) & ignore_next_round:  # pragma: no cover
                raise RuntimeError(
                    "Leaf node already identified for next round!")
            graph.mark_members_including_obsolete_deleted(leaf_nodes)
            after_deleted = graph.deleted_nodes
            cluster_nodes = after_deleted - before_deleted
            ignore_next_round |= cluster_nodes

            cluster_nodes = list(cluster_nodes)
            cluster_nodes.sort()
            leaf_nodes = list(leaf_nodes)
            leaf_nodes.sort()
            clusters.append(
                (cluster_index, cluster_nodes, leaf_nodes))
            for node in cluster_nodes:
                node_to_cluster_index[node] = cluster_index
            cluster_index += 1

            # Reset graph for the next leaf / cluster (not the next round).
            graph.unmark_deleted()
            graph.mark_members_deleted(ignore)

        # Reset graph for the next round (not the next leaf / cluster).
        # Note #1: Only the clusters identified during the first round are
        # leaf clusters.
        ignore = frozenset(ignore_next_round)  # Copy
        graph.unmark_deleted()
        graph.mark_members_deleted(ignore)

    # Reset the graph for the actual AGraph generation.
    graph.unmark_deleted()

    # Build the GraphViz AGraph.
    # TODO(MS): Re-evaluate options if they are really needed.
    agraph = pygraphviz.AGraph(
        directed=True, strict=True, name="dpkg graph", nodesep=0.5,
        outputorder="edgesfirst", ordering="out", ranksep="2.0 equally",
        remincross=True)

    # Step #1 - Add to the AGraph layer subgraphs (non-cluster subgraphs) for
    # each layer the graph has. The layers are connected by strong edges to
    # make sure that the layers are in the correct order. Each layer has rank
    # same to ensure that all nodes in a subgraph are on the same level.
    layer_subgraphs = []
    for i in range(layer_index):
        layer_subgraph = agraph.add_subgraph(
            name="layer-%d" % i, rank="same", ordering="out")
        layer_subgraphs.append(layer_subgraph)
        layer_subgraph.add_node(
            "layer-%d-node" % i, rank="same", label="", style="invis")
        if i > 0:
            agraph.add_edge(
                "layer-%d-node" % (i-1), "layer-%d-node" % i, weight=9999999,
                headport="n", tailport="s", style="invis")

    # Step #2 - Add the clusters of the Graph as cluster subgraphs. Each
    # cluster subgraph has its own layer subgraphs (non-cluster). The layer
    # subgraphs within the cluster are bound to the layer subgraphs of the
    # general graph via strong edges between anchor nodes so that the layers
    # are properly ordered and the layers are consistent throughout the whole
    # graph.
    cluster_subgraphs = {}
    for cluster in clusters:
        cluster_index, cluster_nodes, leaf_nodes = cluster

        # Step #2.1 - Add the cluster subgraph with a desriptive label.
        leaf_nodes_str = [str(node) for node in leaf_nodes]
        cluster_label = "Cluster leaf node%s: %s\nCluster node count: %d" % (
            "s" if len(leaf_nodes) > 1 else "", ", ".join(leaf_nodes_str),
            len(cluster_nodes))
        cluster_tooltip = "Cluster leaf node%s: %s; Cluster node count: %d" % (
            "s" if len(leaf_nodes) > 1 else "", ", ".join(leaf_nodes_str),
            len(cluster_nodes))
        cluster_subgraph = agraph.add_subgraph(
            name="cluster-%d" % cluster_index, label=cluster_label,
            tooltip=cluster_tooltip, ordering="out", clusterrank="local")
        cluster_subgraphs[cluster_index] = cluster_subgraph

        # Step #2.2 - Determine layers in the cluster.
        cluster_layer_indexes = set()  # Set to remove duplicates.
        for cluster_node in cluster_nodes:
            cluster_layer_indexes.add(node_to_layer[cluster_node])
        cluster_layer_indexes = list(cluster_layer_indexes)  # noqa  # pylint: disable=redefined-variable-type
        cluster_layer_indexes.sort()

        # Step #2.3 - Add layers subgraphs to the cluster subgraph.
        cluster_layer_subgraphs = {}
        for index, cluster_layer_index in enumerate(cluster_layer_indexes):
            cluster_layer_subgraph = cluster_subgraph.add_subgraph(
                name="layer-%d-cluster-%d" % (
                    cluster_layer_index, cluster_index),
                rank="same", ordering="out")
            cluster_layer_subgraphs[cluster_layer_index] = (
                cluster_layer_subgraph)
            # Anchor node within the cluster layer subgraph.
            cluster_layer_subgraph.add_node(
                "layer-%d-cluster-%d-node" % (
                    cluster_layer_index, cluster_index),
                rank="same", label="", style="invis")
            # Anchor node withint the layer of the general graoh.
            layer_subgraph = layer_subgraphs[cluster_layer_index]
            layer_subgraph.add_node(
                "layer-%d-cluster-%d-anchor-node" % (
                    cluster_layer_index, cluster_index),
                rank="same", label="", style="invis")
            # Strong edge between the anchor nodes of the layers within the
            # cluster subgraph and the general graph.
            # Note #1: Increading the weight too high on this edge tends to
            # let GraphViz's dot segfault (seen with version 2.38).
            agraph.add_edge(
                "layer-%d-cluster-%d-anchor-node" % (
                    cluster_layer_index, cluster_index),
                "layer-%d-cluster-%d-node" % (
                    cluster_layer_index, cluster_index),
                headport="n", tailport="s", weight=99999, style="invis")

            # Similarly to the layers of the general graph connect the layers
            # of the cluster graph with strong edges to make sure that the
            # layers are in the correct order.
            if index > 0:
                previous_cluster_layer_index = cluster_layer_indexes[index-1]
                agraph.add_edge(
                    "layer-%d-cluster-%d-node" % (
                        previous_cluster_layer_index, cluster_index),
                    "layer-%d-cluster-%d-node" % (
                        cluster_layer_index, cluster_index),
                    headport="n", tailport="s", weight=9999999, style="invis")

        # Step #2.4 - Add the nodes to the respective layer subgraphs of the
        # cluster subgraph.
        for cluster_node in cluster_nodes:
            cluster_layer_index = node_to_layer[cluster_node]
            cluster_layer_subgraph = cluster_layer_subgraphs[
                cluster_layer_index]
            node_attrs = cluster_node.graphviz_attributes
            cluster_layer_subgraph.add_node(cluster_node.uid, **node_attrs)

    # Step #3 - Add the edges to the AGraph. This will be done node for node
    # as depending on the type of edge (intra- or inter-cluster) the handling
    # will be different. Intra-cluster edges will be added as is. Inter-cluster
    # edges will be folded together as much as possible with the help of helper
    # nodes in order to avoid a graph cluttered with inter-cluster edges.
    nodes = list(graph.nodes)
    nodes.sort()
    for node in nodes:
        edges = list(node.incoming_edges)
        if len(edges) == 0:
            continue
        edges.sort()
        remaining_edges = []

        # Step #3.1 - Handle intra-cluster edges.
        for edge in edges:
            # Check if edge is within the same cluster.
            from_cluster_index = node_to_cluster_index[edge.from_node]
            to_cluster_index = node_to_cluster_index[edge.to_node]
            same_cluster = from_cluster_index == to_cluster_index
            if not same_cluster:
                remaining_edges.append(edge)
                continue

            # Add intra-cluster edge.
            cluster_subgraph = cluster_subgraphs[from_cluster_index]
            weight = _edged_to_weight(
                node_to_layer, edge.from_node, edge.to_node)
            attrs = edge.graphviz_attributes
            cluster_subgraph.add_edge(
                 edge.from_node.uid, edge.to_node.uid, weight=weight,
                 headport="n", tailport="s", **attrs)

        # Check if there are remaining edges. If not continue with the
        # incoming edges of the next node.
        edges = remaining_edges
        if len(edges) == 0:
            continue

        # Step #3.2 - Handle singular incoming inter-cluster edges.
        if len(edges) == 1:
            edge = edges[0]
            weight = _edged_to_weight(
                node_to_layer, edge.from_node, edge.to_node)
            attrs = edge.graphviz_attributes
            agraph.add_edge(
                 edge.from_node.uid, edge.to_node.uid, weight=weight,
                 headport="n", tailport="s", **attrs)
            continue

        # Step #3.3 - Handle multiple incoming inter-cluster edges. These edges
        # will be folded together as much as possible with the help of helper
        # nodes in order to avoid a graph cluttered with inter-cluster edges.
        # There will be one helper node per layer in which two or more edges
        # can be folded together.

        # Step #3.3.1 - Sort the edges by the layer index of the from nodes in
        # ascending order. You can think of it as sorting by edge length in
        # descending order.
        edges = sorted(edges, key=lambda edge: node_to_layer[edge.from_node])

        # Step #3.3.2 - Determine for each from node if and which helper node
        # it targets.
        # Note #1: If a from node doesn't target a helper node then it targets
        # the to node.
        from_to_helper_target = {}
        to_node = edges[0].to_node
        to_node_attrs = to_node.graphviz_attributes
        last_layer = node_to_layer[to_node]
        for edge_index, edge in enumerate(edges):
            # Determine the layer of the target node.
            from_layer = node_to_layer[edge.from_node]
            target_layer = from_layer + 1
            if edge_index == 0:
                # Special case for the from node with the lowest layer index.
                # The first from node and the second from node will always
                # target the same helper or to node. Hence the target layer of
                # the second from node will be used instead.
                target_layer = node_to_layer[edges[1].from_node] + 1
            if target_layer > last_layer:  # pragma: no cover
                target_layer = last_layer

            # Determine the target helper node. If the target layer isn't the
            # layer of the to node then the target is a helper node.
            if target_layer != last_layer:
                target = "%s-helper-%d" % (edge.to_node.uid, target_layer)
                from_to_helper_target[edge.from_node.uid] = (
                    target_layer, target)

        # Step #3.3.3 - Add helper nodes and edges to connect the helper nodes
        # down to the to node.
        # Note: The weight of these edges is higher which straightens out the
        # graph by keeping these edges even shorter than all other edges.
        helper_targets = set(from_to_helper_target.values())  # Remove dupes.
        helper_targets = list(helper_targets)  # noqa  # pylint: disable=redefined-variable-type
        helper_targets.sort()
        for helper_target_index, (helper_target_layer, helper_target) in (
                enumerate(helper_targets)):

            # Add helper nodes and also note on which layer this helper node is
            # so that a proper weight can be calculated for edges to helper
            # nodes.
            layer_subgraph = layer_subgraphs[helper_target_layer + 1]
            layer_subgraph.add_node(
                helper_target, shape="point", label="",
                tooltip=to_node_attrs["tooltip"])
            node_to_layer[helper_target] = helper_target_layer

            # Add edges between all the helper nodes.
            if helper_target_index > 0:
                previous_helper_target = (
                    helper_targets[helper_target_index - 1][1])
                weight = 2 * _edged_to_weight(
                    node_to_layer, previous_helper_target, helper_target)
                # TODO(MS): Add the right edge attributes - especially tooltip.
                agraph.add_edge(
                    previous_helper_target, helper_target, weight=weight,
                    headport="n", tailport="s", arrowsize=0.0, penwidth=2.5,
                    label="", tooltip=to_node_attrs["tooltip"])

        # Add edge from last helper target to the to node.
        if helper_targets:
            last_helper_target = helper_targets[-1][1]
            to_node = edges[0].to_node
            weight = 2 * _edged_to_weight(
                    node_to_layer, last_helper_target, to_node)
            # TODO(MS): Add the right edge attributes - especially tooltip.
            agraph.add_edge(
                last_helper_target, to_node.uid, weight=weight,
                headport="n", tailport="s", penwidth=2.5,
                label="", tooltip=to_node_attrs["tooltip"])

        # Step 3.3.4 - Add the edges with either the helper or the to node as
        # target.
        for edge in edges:
            attrs = edge.graphviz_attributes
            helper_target = from_to_helper_target.get(edge.from_node.uid)
            if helper_target:
                target = helper_target[1]
                target_uid = helper_target[1]
                attrs["arrowsize"] = 0.0  # No arrow.
            else:
                target = edge.to_node
                target_uid = edge.to_node.uid

            weight = _edged_to_weight(node_to_layer, edge.from_node, target)
            agraph.add_edge(
                edge.from_node.uid, target_uid, weight=weight,
                headport="n", tailport="s", **attrs)

    return agraph
