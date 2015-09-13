"""Abstract Graph base class with nodes and directed edges."""


import abc
import types

from . import const
from . import error


class Graph(abc.ABC):
    """Abstract Graph base class with nodes and directed edges.

    All Nodes and Edges of the Graph are derived from the respective abstract
    base classes in this module.
    """

    def __init__(self):
        """Graph constructor."""
        # Protected
        self._nodes = {}  # uid:node
        self._edges = {}  # uid:edge
        self._nodes_set = None
        self._edges_set = None
        self._deleted_nodes = set()
        self._deleted_edges = set()
        self._mark_deleted_incoming_cache_level = 0
        self._mark_deleted_outgoing_cache_level = 0

        # Init and check
        super().__init__()
        self._init_nodes_and_edges()
        for edge in self._edges.values():
            if abs(edge.probability - 0.0) < const.EPSILON:
                raise error.EdgeWithZeroProbabilityError(edge)

        # Freeze
        self._nodes = types.MappingProxyType(self._nodes)
        self._edges = types.MappingProxyType(self._edges)
        self._nodes_set = frozenset(self._nodes.values())
        self._edges_set = frozenset(self._edges.values())
        self.__freeze_nodes_incoming_and_outgoing_edges_and_nodes()

    @abc.abstractmethod
    def _init_nodes_and_edges(self):
        """Initializes the nodes of the graph."""

    def __freeze_nodes_incoming_and_outgoing_edges_and_nodes(self):
        """Freezes the incoming and outgoing edges and node sets."""
        for node in self._nodes.values():
            node._freeze_incoming_edges_and_nodes()  # noqa  # pylint: disable=protected-access
            node._freeze_outgoing_edges_and_nodes()  # noqa  # pylint: disable=protected-access

    def _add_edge(self, edge):
        """Adds an edge to the self._edges dict."""
        if not edge.is_edge_instance:
            raise error.NotAnEdgeError(edge)
        if edge.uid in self._edges:
            raise error.MemberAlreadyRegisteredError(edge)
        edge.graph = self
        self._edges[edge.uid] = edge

    def _add_node(self, node):
        """Adds a node to the self._nodes dict."""
        if not node.is_node_instance:
            raise error.NotANodeError(node)
        if node.uid in self._nodes:
            raise error.MemberAlreadyRegisteredError(node)
        node.graph = self
        self._nodes[node.uid] = node

    def _add_node_dedup(self, node):
        """Add the given node to the self._nodes dict if it isn't tracked yet.

        This method checks if the given node is already in the self._nodes
        dict.  If it is the existing node is returned (dedup).  If it isn't
        the given node is added and returned (no-dup).

        Returns:
          Tupel of the node in the self._nodes dict and a boolean if the
          given node was a duplicate.
        """
        dict_node = self._nodes.get(node.uid)
        if dict_node:
            return (dict_node, True)  # Deduplicate
        else:
            self._add_node(node)
            return (node, False)  # Not a duplicate

    @property
    def deleted_edges(self):
        """Returns a set of the edges in the graph marked as deleted."""
        return frozenset(self._deleted_edges)

    @property
    def deleted_nodes(self):
        """Returns a set of the nodes in the graph marked as deleted."""
        return frozenset(self._deleted_nodes)

    @property
    def edges(self):
        """Returns a set of the edges in the graph.

        This set doesn't include the edges that have been marked as deleted.

        Returns:
            Set of edges in the graph.
        """
        return self._edges_set - self._deleted_edges

    @property
    def leafs(self):
        """Returns the leaf nodes of the graph.

        The graph can contain leaf nodes and leaf cycles.  Leaf nodes are nodes
        without incoming edges.  Leaf cycles are nodes in a cycle without
        incoming edges other the ones needed to form the cycle.

        The return value is a set of set of nodes.  The inner sets contain a
        single node for leaf nodes or multiple nodes in case of a leaf cycle.
        The outer set contains all inner sets.
        """
        stage1_nodes_to_visit = set(self._nodes.values())
        stage2_nodes_to_visit = set()
        stage3_nodes_to_visit = set()
        leafs = set()  # Return value

        # Stage 1 - Identify single leaf nodes.
        # A leaf node is a node that has no incoming edges.  As a leaf node has
        # no incoming edges it also can't be in a cycle.
        while stage1_nodes_to_visit:
            node = stage1_nodes_to_visit.pop()
            if node.deleted:
                continue

            if node.incoming_edges:
                # Node isn't a leaf node but it could potentially be part of a
                # leaf cycle - hence it will be revisited in stage 2.
                stage2_nodes_to_visit.add(node)
            else:
                # Node is a leaf node.
                leafs.add(frozenset((node,)))

                # Remove all nodes below this leaf node as these can't be leaf
                # nodes/cycles and hence don't need to be visited in stage 1 or
                # stage 2.
                onrs = node.outgoing_nodes_recursive
                stage1_nodes_to_visit -= onrs
                stage2_nodes_to_visit -= onrs

        # Stage 2 - Determine if a node could potentially be a leaf cycle.
        while stage2_nodes_to_visit:
            node = stage2_nodes_to_visit.pop()

            onrs = node.outgoing_nodes_recursive
            if node.in_cycle:
                # Node is in a cycle.  Don't visit any further nodes of this
                # cycle or nodes below this cycle in stage 2.
                stage2_nodes_to_visit -= onrs

                # Remove all nodes below this cycle as these can't be leaf
                # nodes/cycles and thus don't need to be visited in stage 3.
                # Also don't visit any further nodes of this cycle as one node
                # of the cycle is enough to track the whole cycle.
                stage3_nodes_to_visit -= onrs
                stage3_nodes_to_visit |= set((node,))
            else:
                # Node isn't in a cycle and isn't a leaf node.  This node and
                # all nodes below it can't be leaf nodes/cycles and hence don't
                # need to be visited in stage 2 or 3.
                stage2_nodes_to_visit -= onrs
                stage3_nodes_to_visit -= onrs

        # Stage 3 - Determine leaf cycles.
        # All the nodes that are left are part of leaf cycles.  All that's left
        # to do is to add the cycle_nodes sets to the leafs set.
        for node in stage3_nodes_to_visit:
            leafs |= set((node.cycle_nodes,))

        return frozenset(leafs)

    @property
    def leafs_flat(self):
        """Returns the leaf nodes of the graph in a flattened set.

        This property behaves the same as the leafs property with the only
        difference that the return value is a flattened set that only contains
        nodes that are either leaf nodes or belong to a leaf cycle.
        """
        leafs = self.leafs
        return {node for leaf in leafs for node in leaf}

    def mark_members_deleted(self, members):
        """Marks the given graph members as deleted."""
        for m in members:
            if m.graph != self:
                raise error.NotMemberOfGraphError(m)
            m.mark_deleted()

    def mark_members_including_obsolete_deleted(self, members):
        """Marks the given graph members and obsoleted members as deleted.

        This method marks the given graph members and the obsoleted members by
        the mark deleted operation of the given members recursively as deleted.
        A node is considered obsolete if it had only incoming edges from the
        nodes so far marked as deleted.  Furthermore cycles are counted as a
        single graph member and hence whole cycles can be obsolete as well.

        Example:
        n1 --\
        n2 --> n4 --\
        n3 ---------> n5

        If n1 and n2 in the example will be marked as deleted then n4 is marked
        as deleted as well as n4 was only there as foundation for n1 and n2 but
        it is obsolete as these have been marked as deleted - hence n4 is
        marked as deleted as well.  n5 isn't marked as deleted as it is still
        needed as foundation for n3.
        """
        # Ensure that all members are part of this graph.
        for m in members:
            if m.graph != self:
                raise error.NotMemberOfGraphError(m)

        to_process = set(members)
        all_deleted = None  # All nodes marked as deleted.
        prev_deleted = self.deleted_nodes  # Previously marked as deleted.
        while to_process:
            # Mark all the members to process as deleted.  This doesn't use
            # Graph.mark_members_deleted as it would needlessly check if the
            # members are members of this Graph.
            for m in to_process:
                m.mark_deleted()

            # Determine the nodes that have been marked as deleted in this
            # round.  The number of nodes marked as deleted can differ from the
            # number of nodes in the to_process set.
            all_deleted = self.deleted_nodes
            round_deleted = all_deleted - prev_deleted
            prev_deleted = all_deleted

            # Determine all outgoing nodes that are below the nodes that have
            # been marked as deleted.  The read only set node._outgoing_nodes
            # is used as the node.outgoing_nodes property can't be used on
            # nodes that have been marked as deleted.
            outgoing_nodes = set()
            for node in round_deleted:
                outgoing_nodes |= node._outgoing_nodes  # noqa  # pylint: disable=protected-access

            # Determine new set of nodes to process which also need to be
            # marked as deleted.  For this each outgoing node's incoming nodes
            # will be checked and if the node was only needed by nodes that
            # have been marked as deleted (processed) then it is obsolete and
            # will be processed (marked as deleted) in the next round.
            to_process = set()
            while outgoing_nodes:
                node = outgoing_nodes.pop()
                if node._deleted:  # pylint: disable=protected-access
                    continue  # Already processed. Continue with next node.
                if node.in_cycle:
                    # Node is part of a cycle.  Process the whole cycle as a
                    # single member.
                    cycle_nodes = node.cycle_nodes
                    outgoing_nodes -= cycle_nodes
                    incoming_nodes = node.incoming_cycle_nodes
                    if incoming_nodes - all_deleted:
                        # Cycle is still needed and hence not obsolete.
                        continue

                    # Cycle was only needed by nodes that have been already
                    # marked as deleted and hence it is obsolete.
                    to_process |= cycle_nodes

                else:
                    # Single node.
                    if node._incoming_nodes - all_deleted:  # noqa  # pylint: disable=protected-access
                        # Node is still needed and hence not obsolete.
                        continue

                    # Node was only needed by nodes that have been already
                    # marked as deleted and hence it is obsolete.
                    to_process |= set((node,))

    @property
    def nodes(self):
        """Returns a set of the nodes in the graph.

        This set doesn't include the nodes that have been marked as deleted.

        Returns:
            Set of edges in the graph.
        """
        return self._nodes_set - self._deleted_nodes

    def unmark_deleted(self):
        """Unmarks all graph members as deleted."""
        # Signal the incoming and outgoing nodes recursive properties that
        # the cached result might be invalid and needs to be rechecked.
        self._mark_deleted_incoming_cache_level += 1
        graph_in_cl = self._mark_deleted_incoming_cache_level
        self._mark_deleted_outgoing_cache_level += 1
        graph_out_cl = self._mark_deleted_outgoing_cache_level

        # Unmark the as deleted marked nodes and reset the deleted nodes set.
        for node in self._deleted_nodes:
            node._deleted = False  # pylint: disable=protected-access
        self._deleted_nodes = set()

        # Unmark the as deleted marked edges and reset the deleted edges set.
        for edge in self._deleted_edges:
            edge._deleted = False  # pylint: disable=protected-access
            from_node = edge.from_node
            to_node = edge.to_node

            # If the incoming edges and nodes of the destination node have been
            # touched reset them and mark the incoming nodes recursive cache as
            # invalid as it could be invalid.
            # The _incoming_nodes_recursive_get_cache method checks then if the
            # cached result is actually invalid.
            if to_node._incoming_without_deleted_touched:  # noqa  # pylint: disable=protected-access
                to_node._incoming_without_deleted_touched = False  # noqa  # pylint: disable=protected-access
                to_node._incoming_edges_without_deleted = None  # noqa  # pylint: disable=protected-access
                to_node._incoming_nodes_without_deleted = None  # noqa  # pylint: disable=protected-access
                to_node._incoming_nodes_recursive_invalidated_at_cl = graph_in_cl  # noqa  # pylint: disable=protected-access,line-too-long

            # If the outgoing edges and nodes of the source node have been
            # touched reset them and mark the outgoing nodes recursive cache as
            # invalid as it could be invalid.
            # The _outgoing_nodes_recursive_get_cache method checks then if the
            # cached result is actually invalid.
            if from_node._outgoing_without_deleted_touched:  # noqa  # pylint: disable=protected-access
                from_node._outgoing_without_deleted_touched = False  # noqa  # pylint: disable=protected-access
                from_node._outgoing_edges_without_deleted = None  # noqa  # pylint: disable=protected-access
                from_node._outgoing_nodes_without_deleted = None  # noqa  # pylint: disable=protected-access
                from_node._outgoing_nodes_recursive_invalidated_at_cl = graph_out_cl  # noqa  # pylint: disable=protected-access,line-too-long
        self._deleted_edges = set()
