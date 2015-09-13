"""Abstract Node base class."""


import collections

from . import error
from . import member


class Node(member.Member):  # pylint: disable=abstract-method
    """Abstract Node base class."""

    __empty_frozen_set = frozenset()

    dynamic_result_type = collections.namedtuple("DynamicCacheResult", [])
    static_result_type = collections.namedtuple("StaticCacheResult", [])
    default_result_type = collections.namedtuple("DefaultCacheResult", [])

    def __init__(self, uid):
        # Protected data (readonly after initialization)
        self._incoming_edges = set()
        self._incoming_nodes = set()
        self._outgoing_edges = set()
        self._outgoing_or_edges = None  # True or False after initialization.
        self._outgoing_nodes = set()

        # Protected caches
        self._incoming_edges_without_deleted = None
        self._incoming_nodes_without_deleted = None
        self._incoming_without_deleted_touched = False
        self._incoming_nodes_recursive_cache = None
        self._incoming_nodes_recursive_cache_level = 0
        self._incoming_nodes_recursive_built_at_cl = 0
        self._incoming_nodes_recursive_invalidated_at_cl = 0
        self._outgoing_edges_without_deleted = None
        self._outgoing_nodes_without_deleted = None
        self._outgoing_without_deleted_touched = False
        self._outgoing_nodes_recursive_cache = None
        self._outgoing_nodes_recursive_default_cache = None
        self._outgoing_nodes_recursive_default_cache_level = 0
        self._outgoing_nodes_recursive_static = False
        self._outgoing_nodes_recursive_cache_level = 0
        self._outgoing_nodes_recursive_built_at_cl = 0
        self._outgoing_nodes_recursive_invalidated_at_cl = 0
        self._in_cycle_static = None
        self._cycle_nodes_static = None
        self._cycle_nodes_cache = None
        self._cycle_nodes_cache_built_at_cl = 0

        # Init
        super().__init__(uid)

    def _add_incoming_edge(self, edge):
        """Registers an edge as incoming edge with this node.

        This method will only be called by an Edge constructor.  No further
        edges can be added once the graph has been fully initialized as the
        set of incoming edges on this node will be frozen.
        """
        if not edge.is_edge_instance:
            raise error.NotAnEdgeError(edge)
        if edge.to_node != self:
            raise error.NodeIsNotPartOfEdgeError(self, edge)
        self._incoming_edges.add(edge)
        self._incoming_nodes.add(edge.from_node)

    def _add_outgoing_edge(self, edge):
        """Registers an edge as outgoing edge with this node.

        This method will only be called by an Edge constructor.  No further
        edges can be added once the graph has been fully initialized as the
        set of outgoing edges on this node will be frozen.

        Furthermore the outgoing edges can be either of type Edge or OrEdge.
        Mixing these types inside the outgoing edges set is not allowed!
        """
        # Basic checks.
        if not edge.is_edge_instance:
            raise error.NotAnEdgeError(edge)
        if edge.from_node != self:
            raise error.NodeIsNotPartOfEdgeError(self, edge)

        # Add edge while ensuring that all outgoing edges are either of type
        # Edge or of type OrEdge.
        if self._outgoing_or_edges is None:
            # No edges in the outgoing edges set, yet.  Determine the edge type
            # and set the self._outgoing_or_edges variable for future rounds to
            # know which edge type is accepted.
            if edge.is_oredge_instance:
                self._outgoing_or_edges = True
            else:
                self._outgoing_or_edges = False
        else:
            if self._outgoing_or_edges:
                # Edges in the outgoing edges set are of type OrEdge.
                if not edge.is_oredge_instance:
                    raise error.NotAnOrEdgeError(edge)
            else:
                # Edges in the outgoing edges set are of type Edge.
                if edge.is_oredge_instance:
                    raise error.NotAnEdgeError(edge)

        # Update the outgoing edges and nodes sets.
        self._outgoing_edges.add(edge)
        self._outgoing_nodes.add(edge.to_node)

    def _freeze_incoming_edges_and_nodes(self):
        """Freezes the set of incoming edges and nodes.

        This method will be called by the Graph constructor once the
        intialization is nearly complete.
        """
        self._incoming_edges = frozenset(self._incoming_edges)
        self._incoming_nodes = frozenset(self._incoming_nodes)

    def _freeze_outgoing_edges_and_nodes(self):
        """Freezes the set of outgoing edges and nodes.

        This method will be called by the Graph constructor once the
        intialization is nearly complete.
        """
        self._outgoing_edges = frozenset(self._outgoing_edges)
        self._outgoing_nodes = frozenset(self._outgoing_nodes)

    @property
    def cycle_nodes(self):
        """Returns the set of the nodes in the cycle if is_cycle is True.

        If this node isn't part of a cycle an empty set will be returned.
        """
        cycle_nodes_static = self._cycle_nodes_static
        if cycle_nodes_static is not None:
            return cycle_nodes_static

        graph_cl = self.graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
        cycle_nodes_cache = self._cycle_nodes_cache
        if cycle_nodes_cache is not None:
            if self._cycle_nodes_cache_built_at_cl == graph_cl:
                return cycle_nodes_cache

        # The cycle nodes are all the nodes that are in the incoming and
        # outgoing nodes recursive sets (intersection).  Typically the incoming
        # nodes recursive set hasn't been calculate yet and it is expensive
        # to calculate it just to get the cycle nodes.  Instead of calculating
        # it the incoming nodes are determined recursively for all the nodes
        # that are also in the outgoing nodes recursive set.  This way all the
        # nodes of the cycle are identified as the cycle nodes are part of both
        # the incoming and outgoing nodes recursive sets.  This is typically a
        # lot faster as the incoming nodes that are part of the cycle are a lot
        # less than the full incoming nodes recursive set.
        onrs, rt = self._outgoing_nodes_recursive
        if self not in onrs:
            return Node.__empty_frozen_set  # Not a cycle.

        to_visit = set((self,))
        visited = set()
        cycle_nodes = set()

        while to_visit:
            node = to_visit.pop()
            visited |= set((node,))

            # Only visit incoming nodes that are also in the outgoing nodes
            # recursive set.
            incoming_cycle_nodes = node.incoming_nodes & onrs
            cycle_nodes |= incoming_cycle_nodes
            to_visit |= incoming_cycle_nodes
            to_visit -= visited
        cycle_nodes = frozenset(cycle_nodes)

        # Determine if this cycle is static.  A cycle is static if and only if
        # it has no edges or type OrEdge.  As edges of type OrEdge are
        # important for the outgoing sets it is already predetermined if a node
        # has outgoing edges of type OrEdge and if such a node is part of the
        # cycle then the cycle could be broken up and hence the cycle can't be
        # static.
        static = True
        if rt != Node.static_result_type:
            for node in cycle_nodes:
                if node._outgoing_or_edges:  # noqa  # pylint: disable=protected-access
                    static = False
                    break

        if static:
            for node in cycle_nodes:
                node._in_cycle_static = True  # noqa  # pylint: disable=protected-access
                node._cycle_nodes_static = cycle_nodes  # noqa  # pylint: disable=protected-access

        self._cycle_nodes_cache = cycle_nodes
        self._cycle_nodes_cache_built_at_cl = graph_cl
        return cycle_nodes

    @property
    def in_cycle(self):
        """Returns True if this Node is part of a cycle."""
        # Check if a result that is independent of the graph state has been
        # previously determined and cached.  If yes, return the previous
        # cached result.
        in_cycle_static = self._in_cycle_static
        if in_cycle_static is not None:
            return in_cycle_static

        # Simple checks if this node is part of a cycle.
        incoming_nodes = self.incoming_nodes
        if not incoming_nodes:
            # A leaf node can't be in a cycle.
            return False
        shared_nodes = self.outgoing_nodes & incoming_nodes
        if shared_nodes:
            # There is at least one node in the incoming and outgoing nodes
            # sets and hence this node is in a cycle with this/these node(s).
            # Before returning True it'll be interesting if this result is
            # static so that there is no need to reevaluate for future calls.
            # A cycle is static if and only if it has no edges or type OrEdge.
            # As edges of type OrEdge are important for the outgoing sets it is
            # already predetermined if a node has outgoing edges of type OrEdge
            # and if such a node is part of the cycle then the cycle could be
            # broken up and hence the cycle can't be static.
            if not self._outgoing_or_edges:
                static = True
                for node in shared_nodes:
                    if node._outgoing_or_edges:  # noqa  # pylint: disable=protected-access
                        static = False
                        break
                if static:
                    self._in_cycle_static = True
                    for node in shared_nodes:
                        node._in_cycle_static = True  # noqa  # pylint: disable=protected-access
            return True

        # No more simple tests possible and hence a recusrive nodes set is
        # needed.  Result-wise it doesn't matter if this test uses the
        # recursive incoming nodes set or the recursive outgoing nodes set as
        # the result is in both cases the same.  Performance-wise the recursive
        # outgoing nodes set is typically in favor because of three reasons:
        # 1) Graphs that model a hierarchy typically have a lot more nodes on
        #    the top than the bottom and hence the recursive outgoing nodes set
        #    is often cheaper to calculate.
        # 2) The outgoing sets have a superior cache strategy and are far less
        #    often invalidated than the caches for the incomings sets.
        # 3) The outgoing sets are often already determined and cached.
        onrs, rt = self._outgoing_nodes_recursive
        in_cycle = self in onrs

        # Cache static result.
        if rt == Node.static_result_type:
            self._in_cycle_static = in_cycle
        elif rt == Node.default_result_type and not in_cycle:
            # If the result is the default result and the node isn't part of a
            # cycle then it'lll be never part of a cycle.
            self._in_cycle_static = False

        return in_cycle

    @property
    def incoming_cycle_nodes(self):
        """Returns the incoming nodes of the cycle if the node is in a cycle.

        If the node isn't in a cycle an empty set will be returned.  The
        incoming cycle nodes set doesn't include the cycle nodes itself.
        """
        incoming_cycle_nodes = set()
        cycle_nodes = self.cycle_nodes
        for cycle_node in cycle_nodes:
            incoming_cycle_nodes |= cycle_node.incoming_nodes
        incoming_cycle_nodes -= cycle_nodes
        return incoming_cycle_nodes

    @property
    def incoming_edges(self):
        """Returns the set of all possible directly incoming edges.

        The set doesn't includes edges that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)

        if self._incoming_edges_without_deleted is None:
            self._incoming_edges_without_deleted = set(self._incoming_edges)

        return frozenset(self._incoming_edges_without_deleted)

    @property
    def incoming_nodes(self):
        """Returns the set of all possible directly incoming nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)

        if self._incoming_nodes_without_deleted is None:
            self._incoming_nodes_without_deleted = set(self._incoming_nodes)

        return frozenset(self._incoming_nodes_without_deleted)

    def _incoming_nodes_recursive_get_cache(self, graph_cl):
        """Returns the valid cached result for incoming_nodes_recursive.

        If there is no cached result or it is no longer valid None is returned.

        Args:
            graph_cl: The current graph incoming cache level.
        """
        inrc = self._incoming_nodes_recursive_cache
        if inrc is None:
            return None  # No cached result.

        local_cl = self._incoming_nodes_recursive_cache_level
        if local_cl == graph_cl:
            return inrc  # Cached result is still valid.

        # Local and graph cache level differ.  Check if the cached result is
        # still valid by checking if the cached result of this and each node
        # that contributed to this cached result is still valid.
        to_check = inrc | set((self,))
        for node in to_check:
            built_at = node._incoming_nodes_recursive_built_at_cl  # noqa  # pylint: disable=protected-access
            invalidated_at = node._incoming_nodes_recursive_invalidated_at_cl  # noqa  # pylint: disable=protected-access
            if invalidated_at > built_at:
                return None  # Cached result is no longer valid!

        # Cached result is still valid.  Update the local cache level to avoid
        # needless reiteration of this check and then return the cached result.
        self._incoming_nodes_recursive_cache_level = graph_cl
        return inrc

    def _incoming_nodes_recursive(self, graph_cl):
        """Helper function to determine the incoming recursive nodes.

        Afterwards it caches the result on the node.

        Args:
            graph_cl: The current graph incoming cache level.
        """
        # Determine the incoming nodes of this node recursively.
        to_visit = set((self,))
        visited = set()
        incoming_nodes_recursive = set()
        while to_visit:
            node = to_visit.pop()
            if node in visited:  # pragma: no cover
                continue  # Node has been already visited.
            visited |= set((node,))  # Faster than visited.add(node).

            # Add all incoming nodes to the result and then handle the incoming
            # nodes one by one.
            incoming_nodes = node.incoming_nodes
            incoming_nodes_recursive |= incoming_nodes
            for cn in incoming_nodes:
                if cn in visited:
                    continue  # Child node has been already visited.

                # Determine if the child node has a valid cache and if this is
                # the case use it.
                inrc = cn._incoming_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                    graph_cl=graph_cl)
                if inrc is not None:
                    # The child node has a valid cache.  Add all child nodes to
                    # the result, update visited and to visit nodes and then
                    # continue with the next child node.
                    incoming_nodes_recursive |= inrc
                    visited |= inrc
                    to_visit -= inrc
                    continue

                # Child node doesn't have a valid cache.  Record that it still
                # needs to be visited.
                to_visit |= set((cn,))  # Faster than to_visit.add(cn).

        # Cache the result.
        incoming_nodes_recursive = frozenset(incoming_nodes_recursive)
        self._incoming_nodes_recursive_cache = incoming_nodes_recursive
        self._incoming_nodes_recursive_cache_level = graph_cl
        self._incoming_nodes_recursive_built_at_cl = graph_cl

    @property
    def incoming_nodes_recursive(self):
        """Returns the set of all possible directly and indir. incoming nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.

        If the set includes this node itself then this node is part of a cycle.

        Lastly this property is rather expensive and should be avoided if the
        outgoing_nodes_recursive property can be used instead as this property
        can't very effectively cache its results and the cache is invalidated
        more often than the cache of the outgoing_nodes_recursive property.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)
        graph_cl = self.graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access

        # Stage 1 - Idenitfy all incoming nodes that don't have their result
        # for the incoming_nodes_recursive property cached and their distance
        # to this node.
        to_visit = {self: 0}  # node:distance
        visited = set()
        missing_cache = {}  # node:distance
        while to_visit:
            node, distance = to_visit.popitem()
            if node in visited:
                continue  # Node has been already visited.
            visited |= set((node,))  # Faster than visited.add(cn)

            # Check if the node has a valid cache.
            inrc = node._incoming_nodes_recursive_get_cache(graph_cl=graph_cl)  # noqa  # pylint: disable=protected-access
            if inrc is not None:
                # The node has a valid cache and thus it and all nodes below it
                # aren't of interest to stage 1.
                continue

            # This node doesn't have the incoming_nodes_recursive property
            # cached.  Record that the node has the cache missing and for all
            # its incoming nodes record that they need to be visited.
            missing_cache[node] = distance
            for child_node in node.incoming_nodes:
                to_visit[child_node] = distance + 1

        # Stage 2 - Get a sorted list (largest distance first) of the nodes
        # that are missing the cache and then determine the incoming nodes
        # recursively via a helper function.  In the end all that's left to do
        # is to return the cached result for this node.
        missing_cache_nodes = sorted(
            missing_cache, key=missing_cache.get, reverse=True)
        for node in missing_cache_nodes:
            node._incoming_nodes_recursive(graph_cl=graph_cl)  # noqa  # pylint: disable=protected-access
        return self._incoming_nodes_recursive_cache

    @property
    def is_node_instance(self):
        """Returns True if this object is a Node instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

    @property
    def outgoing_cycle_nodes(self):
        """Returns the outgoing nodes of the cycle if the node is in a cycle.

        If the node isn't in a cycle an empty set will be returned.  The
        outgoing cycle nodes set doesn't include the cycle nodes itself.
        """
        outgoing_cycle_nodes = set()
        cycle_nodes = self.cycle_nodes
        for cycle_node in cycle_nodes:
            outgoing_cycle_nodes |= cycle_node.outgoing_nodes
        outgoing_cycle_nodes -= cycle_nodes
        return outgoing_cycle_nodes

    @property
    def outgoing_edges(self):
        """Returns the set of all possible directly outgoing edges.

        The set doesn't includes edges that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)

        if self._outgoing_edges_without_deleted is None:
            self._outgoing_edges_without_deleted = set(self._outgoing_edges)

        return frozenset(self._outgoing_edges_without_deleted)

    @property
    def outgoing_nodes(self):
        """Returns the set of all possible directly outgoing nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)

        if self._outgoing_nodes_without_deleted is None:
            self._outgoing_nodes_without_deleted = set(self._outgoing_nodes)

        return frozenset(self._outgoing_nodes_without_deleted)

    def _outgoing_nodes_recursive_get_cache(self, graph_cl):
        """Returns the valid cached result for outgoing_nodes_recursive.

        Args:
            graph_cl: The current graph outgoing cache level.

        Returns:
            Returns a tuple of cached result and cached result type.  If there
            is no cached result or it is no longer valid None is returned.
        """
        onrc = self._outgoing_nodes_recursive_cache
        if onrc is None:
            return (None, Node.dynamic_result_type)  # No cached result.

        if self._outgoing_nodes_recursive_static:
            # The outgoing nodes recursive set is static and hence can be
            # reused indefinitely.
            return (onrc, Node.static_result_type)

        default_onrc = self._outgoing_nodes_recursive_default_cache
        if default_onrc:
            # If the default cached result is valid for this outgoing graph
            # cache level then just return the default cache result.
            local_cl = self._outgoing_nodes_recursive_default_cache_level
            if local_cl == graph_cl:
                return (default_onrc, Node.default_result_type)

        # If the last cached result is still valid for this outgoing graph
        # cache level then just return the last (dynamic) cache result.
        local_cl = self._outgoing_nodes_recursive_cache_level
        if local_cl == graph_cl:
            return (onrc, Node.dynamic_result_type)

        self_set = set((self,))
        self_outgoing_nodes = self.outgoing_nodes

        if default_onrc:
            # Check if the default/untouched cached result can be used for this
            # outgoing graph cache level.
            untouched = True
            to_check = [self_set, self_outgoing_nodes, default_onrc]
            for nodes in to_check:
                if not untouched:
                    break
                for node in nodes:
                    # No need to check if the node has been marked deleted as
                    # either the node and all nodes above it are marked deleted
                    # or the node would be marked as touched.
                    if node._outgoing_without_deleted_touched:  # noqa  # pylint: disable=protected-access
                        untouched = False
                        break
            if untouched:
                self._outgoing_nodes_recursive_default_cache_level = graph_cl
                return (default_onrc, Node.default_result_type)

        # Local and graph cache level differ.  Check if the cached result is
        # still valid by checking if the cached result of this and each node
        # that contributed to this cached result is still valid.
        self_built_at = self._outgoing_nodes_recursive_built_at_cl
        to_check = [self_set, self_outgoing_nodes, onrc]
        for nodes in to_check:
            for node in nodes:
                # No need to check if the node has been marked deleted as
                # either the node and all nodes above it are marked deleted
                # or the node would be marked as touched.
                if node._outgoing_nodes_recursive_static:  # noqa  # pylint: disable=protected-access
                    # Cached result for this node and all nodes below it is
                    # static.  The nodes set isn't updated though as it would
                    # be more expensive than just checking each node.
                    continue
                built_at = node._outgoing_nodes_recursive_built_at_cl  # noqa  # pylint: disable=protected-access
                invalid_at = node._outgoing_nodes_recursive_invalidated_at_cl  # noqa  # pylint: disable=protected-access
                if invalid_at > built_at:
                    # Cached result is no longer valid because at least one
                    # part is no longer valid!
                    return (None, Node.dynamic_result_type)
                if built_at > self_built_at:
                    # Cached result is no longer valid because at least one
                    # part is newer!
                    return (None, Node.dynamic_result_type)

        # Cached result is still valid.  Update the local cache level to avoid
        # needless reiteration of this check and then return the cached result.
        self._outgoing_nodes_recursive_cache_level = graph_cl
        return (onrc, Node.dynamic_result_type)

    def _determine_outgoing_nodes_recursive(self, graph_cl):
        """Helper function to determine the outgoing recursive nodes.

        Afterwards it caches the result on the node and returns the result and
        result type.

        Args:
            graph_cl: The current graph outgoing cache level.

        Returns:
            Returns a tuple of result and result type.
        """
        # Determine the outgoing nodes of this node recursively.
        to_visit = set((self,))
        visited = set()
        outgoing_nodes_recursive = set()
        outgoing_nodes_recursive_static = True
        outgoing_nodes_recursive_default = True
        while to_visit:
            node = to_visit.pop()
            if node in visited:  # pragma: no cover
                continue  # Node has been already visited.
            visited |= set((node,))  # Faster than visited.add(node).

            # Check the type of the outgoing edges and in case of OrEdges the
            # outgoing nodes recursive set is no longer static and can't be
            # reused all the time.
            if outgoing_nodes_recursive_static and node._outgoing_or_edges:  # noqa  # pylint: disable=protected-access
                outgoing_nodes_recursive_static = False

            # Check if the node's outgoing without deleted sets have been
            # touched.  If they have been touched then the cached result is not
            # the default/untouched result.
            if (outgoing_nodes_recursive_default and
                    node._outgoing_without_deleted_touched):  # noqa  # pylint: disable=protected-access
                outgoing_nodes_recursive_default = False

            # Add all outgoing nodes to the result and then handle the outgoing
            # nodes one by one.
            outgoing_nodes = node.outgoing_nodes
            outgoing_nodes_recursive |= outgoing_nodes
            to_check = outgoing_nodes - visited
            for cn in to_check:
                # Determine if the node has a valid cache and if this is the
                # case use it.
                onrc, cr_type = cn._outgoing_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                    graph_cl=graph_cl)
                if onrc is None:
                    # Node doesn't have a valid cache.  Record that it still
                    # needs to be visited.
                    to_visit |= set((cn,))  # Faster than to_visit.add(cn).

                else:
                    # The node has a valid cache.  Check if the cached result
                    # is static and if it isn't then this result isn't static
                    # either.
                    if cr_type != Node.static_result_type:  # noqa  # pylint: disable=protected-access
                        outgoing_nodes_recursive_static = False

                    # Check if the cached result is a default/untouched or
                    # static result.  If it isn't then this result isn't a
                    # default/untouched result.
                    if (cr_type != Node.default_result_type and
                            cr_type != Node.static_result_type):
                        outgoing_nodes_recursive_default = False

                    # Add the cached result of the node to the result, update
                    # visited and to visit nodes.
                    outgoing_nodes_recursive |= onrc
                    visited |= onrc
                    to_visit -= onrc

        # Cache the result.
        frozen_onrs = frozenset(outgoing_nodes_recursive)
        self._outgoing_nodes_recursive_cache = frozen_onrs
        self._outgoing_nodes_recursive_static = outgoing_nodes_recursive_static
        if outgoing_nodes_recursive_static:
            return (frozen_onrs, Node.static_result_type)
        if outgoing_nodes_recursive_default:
            self._outgoing_nodes_recursive_default_cache = frozen_onrs
            self._outgoing_nodes_recursive_default_cache_level = graph_cl
            return (frozen_onrs, Node.default_result_type)
        self._outgoing_nodes_recursive_cache_level = graph_cl
        self._outgoing_nodes_recursive_built_at_cl = graph_cl
        return (frozen_onrs, Node.dynamic_result_type)

    @property
    def _outgoing_nodes_recursive(self):
        """Returns the outgoing recursive nodes and the result type.

        Returns:
            Returns a tuple of result and result type.
        """
        graph_cl = self.graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access

        # Stage 1 - Idenitfy all outgoing nodes that don't have their result
        # for the outgoing_nodes_recursive property cached and their distance
        # to this node.
        to_visit = {self: 0}  # node:distance
        visited = set()
        missing_cache = {}  # node:distance
        last_onrs = None
        last_rt = None
        while to_visit:
            node, distance = to_visit.popitem()
            if node in visited:
                continue  # Node has been already visited.
            visited |= set((node,))  # Faster than visited.add(cn)

            # Check if the node has a valid cache.
            last_onrs, last_rt = node._outgoing_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                graph_cl=graph_cl)
            if last_onrs is not None:
                # The node has a valid cache and thus it and all nodes below it
                # aren't of interest to stage 1.
                continue

            # This node doesn't have the outgoing_nodes_recursive property
            # cached.  Record that the node has the cache missing and for all
            # its outgoing nodes record that they need to be visited.
            missing_cache[node] = distance
            for child_node in node.outgoing_nodes:
                to_visit[child_node] = distance + 1

        # Stage 2 - Get a sorted list (largest distance first) of the nodes
        # that are missing the cache and then determine the outgoing nodes
        # recursively via a helper function.  In the end all that's left to do
        # is to return the last result as the last result is the result for
        # this node (the only node with distance 0).
        if missing_cache:
            missing_cache_nodes = sorted(
                missing_cache, key=missing_cache.get, reverse=True)
            for node in missing_cache_nodes:
                last_onrs, last_rt = node._determine_outgoing_nodes_recursive(  # noqa  # pylint: disable=protected-access
                    graph_cl=graph_cl)
        return last_onrs, last_rt

    @property
    def outgoing_nodes_recursive(self):
        """Returns the set of all possible directly and indir. outgoing nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.

        If the set includes this node itself then this node is part of a cycle.

        If possible this property should be used in favor over the incoming_
        nodes_recursive property as this property has superior caching and the
        caches are less often invalidated.  This property has 3 different
        caching types.  The cached result can be static which means the result
        is always the same independent of the Graph's state.  The cached result
        can also be the default which means that nothing marked as deleted has
        altered the result.  Lastly the current result is also cached and this
        cache type is labeled dynamic.  The dynamic cache will be marked
        invalidated in case something gets marked as deleted in the Graph.
        There is a quicker revalidation process to avoid even more needless
        recalculations of this property.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)
        onrs, _ = self._outgoing_nodes_recursive  # Throw away return type.
        return onrs

    def mark_deleted(self):
        """Marks the node and its incoming and outgoing edges as deleted."""
        if self._deleted:  # pragma: no cover
            return  # Stop recursion

        # Get all needed data from the node and copy it before anything is
        # marked deleted.  The copy is needed because these sets can be
        # recursively alterated while this method iterates over them.
        incoming_edges = frozenset(self.incoming_edges)
        outgoing_edges = frozenset(self.outgoing_edges)

        # Mark the incoming/outgoing edges as deleted as edges can't exist
        # without their nodes.  The respective caches will be update or
        # invalidated by the Edge.mark_delete() methods - if necessary.
        for edge in incoming_edges:
            edge.mark_deleted()
        for edge in outgoing_edges:
            edge.mark_deleted()

        # Finally mark the node itself as deleted.
        self._deleted = True
        self.graph._deleted_nodes |= set((self,))
