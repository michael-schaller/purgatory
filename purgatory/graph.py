"""A hierarchical Graph with nodes and directed edges that have probabilities.

The Graph implementation in this module is designed for hierarchical Graphs.
The Graph can have cycles and can be disconnected.  The hierarchy is modeled
after a wodden tree with relatively many leaf nodes on the top and relatively
few leaf nodes on the bottom.

A hierarchical Graph consists of Nodes and directed Edges that have
probabilities.  An edge of type Edge has always the probability 1.0 and
represents a mandatory edge.  Furthermore edges can also be in an
or-relationship if they are of type OrEdge.  Any of the edges in an
or-relationship satisfy the hierarchie but it is not important which one.
Edges of type OrEdge have a probability depending on how many edges are in the
or-relationship.  For more details see the docstring of the OrEdge type.

A Graph's set of Nodes and Edges can't be changed after initialization.
However Nodes and Edges can be marked as deleted.  Every Graph member that is
marked as deleted will be ignored by algorithms but be warned that some
algorithms reset the deleted markers.  Whenever the deleted markers are changed
there will be a note in the respective docstring.

As a Graph is hierarchical the mark_deleted methods on Nodes and Edges behave
differently than with classical/generic Graph implementations.  Marking a Node
as deleted also marks its incoming and outgoing edges as deleted as edges can't
exist without their nodes existing.  Marking an Edge as deleted typically marks
everything above the from-node of the Edge as deleted as the Nodes and Edges
can't exist anymore without their foundation.  The only exception to this rule
is made if the hierarchie isn't violated due to edges in an or-relationship.

Cycles in the Graph are always treated as an undividable cluster of nodes.
For an instance Graph.leaf_nodes returns the leaf nodes and the nodes within
leaf cycles.
"""

import abc
import types

import purgatory.error


EPSILON = 0.00001
EMPTY_FROZEN_SET = frozenset()


class GraphError(purgatory.error.PurgatoryError):
    """Base class for all graph related errors."""


class NotANodeError(GraphError):
    """Raised if a node was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'Node' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class NotAnEdgeError(GraphError):
    """Raised if an edge was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'Edge' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class NotAnOrEdgeError(GraphError):
    """Raised if an or-edge was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'OrEdge' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class MemberAlreadyRegisteredError(GraphError):
    """Raised if a member has been already registered in the graph."""

    def __init__(self, member):
        msg = "Member '%s' with uid '%s' has been already registered!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class UnregisteredMemberInUseError(GraphError):
    """Raised if an unregistered member is in use."""

    def __init__(self, member):
        msg = "Unregistered member '%s' with uid '%s' is in use!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class DeletedMemberInUseError(GraphError):
    """Raised if a deleted member is in use."""

    def __init__(self, member):
        msg = "Deleted member '%s' with uid '%s' is in use!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class NodeIsNotPartOfEdgeError(GraphError):
    """Raised if a node isn't part of an edge but should be."""
    def __init__(self, node, edge):
        msg = "Node '%s' isn't part of edge '%s' but should be!" % (
            node, edge)
        super().__init__(msg)


class EdgeWithZeroProbabilityError(GraphError):
    """Raised if an edge has the probability of 0.0."""

    def __init__(self, edge):
        msg = ("The edge '%s' has a probability of 0.0 and isn't of any use "
               "to the Graph!") % (edge)
        super().__init__(msg)


class Graph(abc.ABC):
    """Abstract Graph base class with nodes and directed edges.

    All Nodes and Edges of the Graph are derived from the respective abstract
    base classes in this module.
    """

    def __init__(self):
        """Graph constructor."""
        # Private
        self.__nodes = {}  # uid:node
        self.__edges = {}  # uid:edge

        # Protected
        self._mark_deleted_incoming_cache_level = 0
        self._mark_deleted_outgoing_cache_level = 0

        # Init
        super().__init__()
        self._init_nodes_and_edges()

        # Freeze
        self.__nodes = types.MappingProxyType(self.__nodes)
        self.__edges = types.MappingProxyType(self.__edges)
        self.__freeze_nodes_incoming_outgoing_edges()

        # Check
        for edge in self.__edges.values():
            if abs(edge.probability - 0.0) < EPSILON:
                raise EdgeWithZeroProbabilityError(edge)

    @abc.abstractmethod
    def _init_nodes_and_edges(self):
        """Initializes the nodes of the graph."""

    def __freeze_nodes_incoming_outgoing_edges(self):
        """Freezes the incoming and outgoing edges sets of the nodes."""
        for node in self.__nodes.values():
            node._freeze_incoming_edges()  # pylint: disable=protected-access
            node._freeze_outgoing_edges()  # pylint: disable=protected-access

    def _add_node(self, node):
        """Adds a node to the self.__nodes dict."""
        if not isinstance(node, Node):
            raise NotANodeError(node)
        if node.uid in self.__nodes:
            raise MemberAlreadyRegisteredError(node)
        self.__nodes[node.uid] = node
        node.graph = self

    def _add_node_dedup(self, node):
        """Add the given node to the self.__nodes dict if it isn't tracked yet.

        This method checks if the given node is already in the self.__nodes
        dict.  If it is the existing node is returned (dedup).  If it isn't
        the given node is added and returned (no-dup).

        Returns:
          Tupel of the node in the self.__nodes dict and a boolean if the
          given node was a duplicate.
        """
        dict_node = self.__nodes.get(node.uid)
        if dict_node:
            return (dict_node, True)  # Deduplicate
        else:
            self._add_node(node)
            return (node, False)  # Not a duplicate

    @property
    def edges(self):
        """Returns a dict view (uid:edge) of the edges in the graph.

        The dict view is unfiltered and thus contains deleted edges.
        """
        return self.__edges

    @property
    def leaf_nodes(self):
        """Returns the leaf nodes of the graph.

        The graph can contain leaf nodes and leaf cycles.  Leaf nodes are nodes
        without incoming edges.  Leaf cycles are nodes in a cycle without
        incoming edges other the ones needed to form the cycle.

        The return value is a set of set of nodes.  The inner sets contain a
        single node for leaf nodes or multiple nodes in case of a leaf cycle.
        The outer set contains all inner sets.
        """
        stage1_nodes_to_visit = set(self.__nodes.values())
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

            # Test the shortcut if the outgoing_edges set is empty

            if node.in_cycle:
                # Node is in a cycle.  Add this node to the
                # stage3_nodes_to_visit set to look at it in stage 3.
                # One node of the cycle is enough to track the whole cycle.
                stage3_nodes_to_visit.add(node)

                # Don't visit any further nodes of this cycle or nodes below
                # this cycle in stage 2.
                onrs = node.outgoing_nodes_recursive
                stage2_nodes_to_visit -= onrs

                # Remove all nodes below this cycle as these can't be leaf
                # nodes/cycles and thus don't need to be visited in stage 3.
                below = onrs - node.cycle_nodes
                stage3_nodes_to_visit -= below
            else:
                # Node isn't in a cycle and isn't a leaf node.  This node and
                # all nodes below it can't be leaf nodes/cycles and hence don't
                # need to be visited in stage 2 or 3.
                onrs = node.outgoing_nodes_recursive
                stage2_nodes_to_visit -= onrs
                stage3_nodes_to_visit -= onrs

        # Stage 3 - Determine leaf cycles.
        # All the nodes that are left are part of leaf cycles.  All that's left
        # to do is to add the cycle_nodes sets to the leafs set.
        for node in stage3_nodes_to_visit:
            leafs.add(node.cycle_nodes)

        return frozenset(leafs)

    @property
    def leaf_nodes_flat(self):
        """Returns the leaf nodes of the graph in a flattened set.

        This property behaves the same as the leaf_nodes property with the only
        difference that the return value is a flattened set that only contains
        nodes that are either leaf nodes or belong to a leaf cycle.
        """
        leafs = self.leaf_nodes
        return {node for leaf in leafs for node in leaf}

    @property
    def nodes(self):
        """Returns a dict view (uid:node) of the nodes in the graph.

        The dict view is unfiltered and thus contains deleted nodes.
        """
        return self.__nodes

    def _add_edge(self, edge):
        """Adds an edge to the self.__edges dict."""
        if not isinstance(edge, Edge):
            raise NotAnEdgeError(edge)
        if edge.uid in self.__edges:
            raise MemberAlreadyRegisteredError(edge)
        self.__edges[edge.uid] = edge
        edge.graph = self

    def unmark_deleted(self):
        """Unmarks all graph members as deleted."""
        for node in self.__nodes.values():
            node._deleted = False  # pylint: disable=protected-access
        for edge in self.__edges.values():
            edge._deleted = False  # pylint: disable=protected-access
        self._mark_deleted_incoming_cache_level += 1
        self._mark_deleted_outgoing_cache_level += 1


class Member(abc.ABC):
    """Abstract base class for members (nodes, edges) of a Graph."""

    __uid_counter = 0
    __uid_to_uid_intid = {}  # uid:uid_intid

    def __init__(self, uid):
        # Get unique integer id based on the uid
        uid_intid = Member.__uid_to_uid_intid.get(uid)
        if uid_intid is None:
            uid_intid = Member.__uid_counter
            Member.__uid_to_uid_intid[uid] = uid_intid
            Member.__uid_counter += 1

        # Protected
        self._uid = uid
        self._uid_intid = uid_intid
        self._hash = hash(uid)
        self._str = None
        self._deleted = False
        self._graph = None

        # Init
        super().__init__()
        self._init_str()

    def __eq__(self, other):
        """Equals magic method with extreme speed optimizations.

        This method is in an extreme hot code path and thus has been profiled
        and optimized heavily.  As comparing the uid or hashes takes too long
        """
        try:
            other_uid_intid = other._uid_intid  # noqa  # pylint: disable=protected-access
        except AttributeError:  # pragma: no cover
            return False  # Not a Member class
        return self._uid_intid == other_uid_intid  # Unique id for all Members.

    def __ge__(self, other):
        return self._uid >= other.uid

    def __gt__(self, other):
        return self._uid > other.uid

    def __hash__(self):
        return self._hash

    def __le__(self, other):
        return self._uid <= other.uid

    def __lt__(self, other):
        return self._uid < other.uid

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self._str

    def __repr__(self):
        return "%s(uid='%s')" % (self.__class__.__name__, self._uid)

    @abc.abstractmethod
    def _init_str(self):
        """Initializes self._str for self.__str__."""

    @property
    def deleted(self):
        """Returns True if this graph member has been marked as deleted."""
        return self._deleted

    @property
    def graph(self):
        """Returns the graph to which this member belongs."""
        if not self._graph:
            raise UnregisteredMemberInUseError(self)
        return self._graph

    @graph.setter
    def graph(self, graph):
        """Sets the graph to which this member belongs.

        The graph can only be set once.
        """
        if self._graph:
            raise MemberAlreadyRegisteredError(self)
        self._graph = graph

    @property
    def uid(self):
        """Returns the uid of the graph member."""
        return self._uid

    @abc.abstractmethod
    def mark_deleted(self):
        """Marks the graph member as deleted."""


class Node(Member):  # pylint: disable=abstract-method
    """Abstract Node base class."""

    def __init__(self, uid):
        # Private
        self.__incoming_edges = set()
        self.__outgoing_edges = set()
        self.__incoming_edges_property_cache = None
        self.__incoming_edges_property_cache_level = 0
        self.__incoming_nodes_property_cache = None
        self.__incoming_nodes_property_cache_level = 0
        self.__incoming_nodes_recursive_func_cache = None
        self.__incoming_nodes_recursive_func_cache_level = 0
        self.__outgoing_edges_property_cache = None
        self.__outgoing_edges_property_cache_level = 0
        self.__outgoing_nodes_property_cache = None
        self.__outgoing_nodes_property_cache_level = 0
        self.__outgoing_nodes_recursive_func_cache = None
        self.__outgoing_nodes_recursive_func_cache_level = 0

        # Init
        super().__init__(uid)

    def _add_incoming_edge(self, edge):
        """Registers an edge as incoming edge with this node.

        This method will only be called by an Edge constructor.  No further
        edges can be added once the graph has been fully initialized as the
        set of incoming edges on this node will be frozen.
        """
        if not isinstance(edge, Edge):
            raise NotAnEdgeError(edge)
        if edge.to_node != self:
            raise NodeIsNotPartOfEdgeError(self, edge)
        self.__incoming_edges.add(edge)

    def _add_outgoing_edge(self, edge):
        """Registers an edge as outgoing edge with this node.

        This method will only be called by an Edge constructor.  No further
        edges can be added once the graph has been fully initialized as the
        set of outgoing edges on this node will be frozen.

        Furthermore the outgoing edges can be either of type Edge or OrEdge.
        Mixing these types inside the outgoing edges set is not allowed!
        """
        # Basic checks.
        if not isinstance(edge, Edge):
            raise NotAnEdgeError(edge)
        if edge.from_node != self:
            raise NodeIsNotPartOfEdgeError(self, edge)

        # Add edge while ensuring that all outgoing edges are either of type
        # Edge or of type OrEdge.
        edge_count = 0
        or_edge_count = 0
        for outgoing_edge in self.__outgoing_edges:
            if isinstance(outgoing_edge, OrEdge):
                or_edge_count += 1
            else:
                edge_count += 1
        if isinstance(edge, OrEdge):
            # Trying to add edge of type OrEdge
            if edge_count > 0:
                raise NotAnEdgeError(edge)
        else:
            # Trying to add edge of type Edge
            if or_edge_count > 0:
                raise NotAnOrEdgeError(edge)
        self.__outgoing_edges.add(edge)

    def _freeze_incoming_edges(self):
        """Freezes the set of incoming edges.

        This method will be called by the Graph constructor once the
        intialization is nearly complete.
        """
        self.__incoming_edges = frozenset(self.__incoming_edges)

    def _freeze_outgoing_edges(self):
        """Freezes the set of incoming edges.

        This method will be called by the Graph constructor once the
        intialization is nearly complete.
        """
        self.__outgoing_edges = frozenset(self.__outgoing_edges)

    @property
    def cycle_nodes(self):
        """Returns the set of the nodes in the cycle if is_cycle is True.

        If this node isn't part of a cycle an empty set will be returned.
        """
        inrs = self.incoming_nodes_recursive
        onrs = self.outgoing_nodes_recursive
        return frozenset(inrs & onrs)

    @property
    def in_cycle(self):
        """Returns True if this Node is part of a cycle."""
        # Simple checks if this node can be part of a cycle.
        if not self.incoming_edges:
            return False
        if not self.outgoing_edges:
            return False

        # Result-wise it doesn't matter if the tests uses the recursive
        # incoming nodes set or the recursive outgoing nodes set - the result
        # is in both cases the same.
        # Performance-wise the recursive outgoing nodes set is typically in
        # favor because of two reasons:
        # 1) Graphs that model a hierarchy typically have a lot more nodes on
        #    top than the bottom and hence the recursive outgoing nodes set is
        #    often cheaper to calculate.
        # 2) The caches for the outgoing sets are less often invalidated than
        #    the caches for the incomings sets.
        if self in self.outgoing_nodes_recursive:
            return True
        return False

    @property
    def incoming_edges(self):
        """Returns the set of all possible directly incoming edges.

        The set doesn't includes edges that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cache_level = graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
        if self.__incoming_edges_property_cache is not None:
            local_cache_level = self.__incoming_edges_property_cache_level
            if local_cache_level == graph_cache_level:
                # Return still valid cached result
                return self.__incoming_edges_property_cache

        # Calculate, cache and return result
        ies = {edge for edge in self.__incoming_edges if not edge._deleted}  # noqa  # pylint: disable=protected-access
        ies = frozenset(ies)
        self.__incoming_edges_property_cache = ies
        self.__incoming_edges_property_cache_level = graph_cache_level
        return ies

    @property
    def incoming_nodes(self):
        """Returns the set of all possible directly incoming nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cache_level = graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
        if self.__incoming_nodes_property_cache is not None:
            local_cache_level = self.__incoming_nodes_property_cache_level
            if local_cache_level == graph_cache_level:
                # Return still valid cached result
                return self.__incoming_nodes_property_cache

        # Calculate, cache and return result
        ins = {edge.from_node for edge in self.incoming_edges}
        ins = frozenset(ins)
        self.__incoming_nodes_property_cache = ins
        self.__incoming_nodes_property_cache_level = graph_cache_level
        return ins

    def _incoming_nodes_recursive(self, visited_nodes):
        """Recursive helper method for the incoming_nodes_recursive prop."""
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cl = graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
        if self.__incoming_nodes_recursive_func_cache is not None:
            local_cl = self.__incoming_nodes_recursive_func_cache_level
            if local_cl == graph_cl:
                # Return still valid cached result and allow further caching.
                return self.__incoming_nodes_recursive_func_cache, True

        # Check/update visited nodes
        if self in visited_nodes:
            # This node has been already visited and hence this node is part of
            # a cycle.  Return an empty set to break the recursion.
            # Furthermore disallow caching of this result as only the final
            # result and not the intermediary results are cachable.
            return EMPTY_FROZEN_SET, False
        else:
            visited_nodes |= set((self,))  # |= is faster than set.add

        # Calculate result.
        cache_result = True
        incoming_nodes = self.incoming_nodes
        incoming_nodes_recursive = incoming_nodes.copy()
        for incoming_node in incoming_nodes:
            if self == incoming_node:
                continue  # Self-cycle -> No need to visit again
            _result, _cache_result = incoming_node._incoming_nodes_recursive(  # noqa  # pylint: disable=protected-access
                visited_nodes=visited_nodes)
            if not _cache_result:
                # The result wasn't cached because a cycle is somehow involved.
                # As the incoming_node didn't cache its result don't cache this
                # result either.  The result will then be cached once the final
                # result has been determined.
                cache_result = False
            incoming_nodes_recursive |= _result

        # Cache (if allowed) and return result
        result = frozenset(incoming_nodes_recursive)
        if cache_result:
            self.__incoming_nodes_recursive_func_cache = result
            self.__incoming_nodes_recursive_func_cache_level = graph_cl
        return result, cache_result

    @property
    def incoming_nodes_recursive(self):
        """Returns the set of all possible directly and indir. incoming nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.

        If the set includes this node itself then this node is part of a cycle.
        """
        result, cache_result = self._incoming_nodes_recursive(
            visited_nodes=set())
        if not cache_result:
            # Result hasn't been cached yet.  Cache the result as the overall
            # result is always valid.
            self.__incoming_nodes_recursive_func_cache = result
            gcl = self.graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
            self.__incoming_nodes_recursive_func_cache_level = gcl
        return result

    @property
    def outgoing_edges(self):
        """Returns the set of all possible directly outgoing edges.

        The set doesn't includes edges that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cache_level = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
        if self.__outgoing_edges_property_cache is not None:
            local_cache_level = self.__outgoing_edges_property_cache_level
            if local_cache_level == graph_cache_level:
                # Return still valid cached result
                return self.__outgoing_edges_property_cache

        # Calculate, cache and return result
        oes = {edge for edge in self.__outgoing_edges if not edge._deleted}  # noqa  # pylint: disable=protected-access
        oes = frozenset(oes)
        self.__outgoing_edges_property_cache = oes
        self.__outgoing_edges_property_cache_level = graph_cache_level
        return oes

    @property
    def outgoing_nodes(self):
        """Returns the set of all possible directly outgoing nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cache_level = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
        if self.__outgoing_nodes_property_cache is not None:
            local_cache_level = self.__outgoing_nodes_property_cache_level
            if local_cache_level == graph_cache_level:
                # Return still valid cached result
                return self.__outgoing_nodes_property_cache

        # Calculate, cache and return result
        ons = {edge.to_node for edge in self.outgoing_edges}
        ons = frozenset(ons)
        self.__outgoing_nodes_property_cache = ons
        self.__outgoing_nodes_property_cache_level = graph_cache_level
        return ons

    def _outgoing_nodes_recursive(self, visited_nodes):
        """Recursive helper method for the outgoing_nodes_recursive prop."""
        if self._deleted:
            raise DeletedMemberInUseError(self)

        # Speed optimization because this is an extremely hot code path.
        try:
            graph = self._graph  # Direct access
        except AttributeError:  # pragma: no cover
            graph = self.graph  # Property

        # Check if cached data is available and still valid
        graph_cl = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
        if self.__outgoing_nodes_recursive_func_cache is not None:
            local_cl = self.__outgoing_nodes_recursive_func_cache_level
            if local_cl == graph_cl:
                # Return still valid cached result and allow further caching.
                return self.__outgoing_nodes_recursive_func_cache, True

        # Check/update visited nodes
        if self in visited_nodes:
            # This node has been already visited and hence this node is part of
            # a cycle.  Return an empty set to break the recursion.
            # Furthermore disallow caching of this result as only the final
            # result and not the intermediary results are cachable.
            return EMPTY_FROZEN_SET, False
        else:
            visited_nodes |= set((self,))  # |= is faster than set.add

        # Calculate result.
        cache_result = True
        outgoing_nodes = self.outgoing_nodes
        outgoing_nodes_recursive = outgoing_nodes.copy()
        for outgoing_node in outgoing_nodes:
            if self == outgoing_node:
                continue  # Self-cycle -> No need to visit again
            _result, _cache_result = outgoing_node._outgoing_nodes_recursive(  # noqa  # pylint: disable=protected-access
                visited_nodes=visited_nodes)
            if not _cache_result:
                # The result wasn't cached because a cycle is somehow involved.
                # As the incoming_node didn't cache its result don't cache this
                # result either.  The result will then be cached once the final
                # result has been determined.
                cache_result = False
            outgoing_nodes_recursive |= _result

        # Cache (if allowed) and return result
        result = frozenset(outgoing_nodes_recursive)
        if cache_result:
            self.__outgoing_nodes_recursive_func_cache = result
            self.__outgoing_nodes_recursive_func_cache_level = graph_cl
        return result, cache_result

    @property
    def outgoing_nodes_recursive(self):
        """Returns the set of all possible directly and indir. outgoing nodes.

        The set doesn't includes nodes that are marked as deleted.  The set is
        independent of the edge probability because any edge with a probability
        greater 0.0 are included and edges with probability 0.0 can't be in the
        graph.

        If the set includes this node itself then this node is part of a cycle.
        """
        result, cache_result = self._outgoing_nodes_recursive(
            visited_nodes=set())
        if not cache_result:
            # Result hasn't been cached yet.  Cache the result as the overall
            # result is always valid.
            self.__outgoing_nodes_recursive_func_cache = result
            gcl = self.graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
            self.__outgoing_nodes_recursive_func_cache_level = gcl
        return result

    def mark_deleted(self):
        """Marks the node and its incoming and outgoing edges as deleted."""
        if self._deleted:  # pragma: no cover
            return  # Stop recursion

        # Get all needed data from the node before anything is marked deleted.
        incoming_edges = self.incoming_edges
        outgoing_edges = self.outgoing_edges

        # Mark the incoming/outgoing edges as deleted as edges can't exist
        # without their nodes.  The respective cache level will be increased
        # by the Edge.mark_delete() methods - if necessary.
        for edge in incoming_edges:
            edge.mark_deleted()
        for edge in outgoing_edges:
            edge.mark_deleted()

        # Finally mark the node itself as deleted.
        self._deleted = True


class Edge(Member):
    """Directed edge graph member."""

    def __init__(self, from_node, to_node):
        # Check
        if not isinstance(from_node, Node):
            raise NotANodeError(from_node)
        if not isinstance(to_node, Node):
            raise NotANodeError(to_node)

        # Private
        self.__from_node = from_node
        self.__to_node = to_node

        # Init
        uid = self._nodes_to_edge_uid(from_node, to_node)
        super().__init__(uid)
        from_node._add_outgoing_edge(self)  # pylint: disable=protected-access
        to_node._add_incoming_edge(self)  # pylint: disable=protected-access

    @abc.abstractmethod
    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""

    @property
    def probability(self):
        """Returns the probability of this edge. Defaults to 1.0."""
        if self._deleted:
            raise DeletedMemberInUseError(self)
        return 1.0

    @property
    def from_node(self):
        """Returns the source (from) node of the edge."""
        return self.__from_node

    @property
    def to_node(self):
        """Returns the destination (to) node of the edge."""
        return self.__to_node

    def mark_deleted(self):
        """Marks the edge as deleted. This might also affect its outgoing node.

        As a graph represents a hierarchie the nodes that are above a node also
        need to be marked as deleted as long as there is no alternative edge
        that ensures that the hierarchie isn't violated.
        """
        if self._deleted:  # pragma: no cover
            return  # Stop recursion

        # Get all needed data from the edge and then mark it as deleted.
        probability = self.probability
        from_node = self.from_node
        self._deleted = True

        # Increase cache levels to invalidate the respective caches.  The
        # outgoing caches only need to be recalculated if an OrEdge has been
        # marked as deleted as marking an edge as deleted only affects the
        # nodes and edges above (incoming).  In case of marking an OrEdge as
        # deleted the outgoing_edges set of a node needs an update and hence
        # the outgoing cache level needs to be bumped.
        self.graph._mark_deleted_incoming_cache_level += 1
        if probability < 1.0:
            self.graph._mark_deleted_outgoing_cache_level += 1

        # Check if the hierarchy is violated and mark the from-node as deleted
        # if necessary.
        if abs(probability - 1.0) < EPSILON:
            from_node.mark_deleted()


class OrEdge(Edge):  # pylint: disable=abstract-method
    """Represents an or-relationship between edges.

    OrEdge represents edges that are in an or-relationship.  This means that
    any of the edges in the or-relationship satisfies the hierarchie but it is
    not important which one.  One can also think of the or-relationship as a
    single edge with one from-node but multiple to-nodes.  Because of this Edge
    and OrEdge can't be mixed in the outgoing edges set of a node!

    Edges of type OrEdge have a probability depending on how many edges are
    in the or-relationship.  If there is one OrEdge then it has a probability
    of 1/1.  If there are two edges in the or-relationship both have a
    probability of 1/2.  If there are three edges they all have 1/3 and so on.
    """

    @property
    def probability(self):
        """Returns the probability of this edge.

        The probability is based on the edges in parallel to this edge.  Each
        one has the same probability to be choosen.
        """
        if self._deleted:
            raise purgatory.graph.DeletedMemberInUseError(self)
        outgoing_edges = self.from_node.outgoing_edges

        # Division by zero should be impossible as there is always at least
        # the current edge and hence len(outgoing_edges) should be >= 1.
        return 1 / len(outgoing_edges)
