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
For an instance Graph.leafs returns the leaf nodes and the nodes within
leaf cycles.  Marking a cycle as deleted will also mark all nodes and edges of
the cycle as deleted as long as there is no alternative (parallel OrEdge).

The classes in this module are very thightly tied together and protected access
between classes in this module is generally allowed and partly necessary to
speed up extremely hot code paths.  If this code would be written in C++ these
classes would be in a 'friend' relationship.
"""


import abc
import collections
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


class NotMemberOfGraphError(GraphError):
    """Raised if a member in use doesn't belong to this graph."""

    def __init__(self, member):
        msg = "Member '%s' with uid '%s' doesn't belong to this graph!" % (
            member.__class__, member.uid)
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
            if abs(edge.probability - 0.0) < EPSILON:
                raise EdgeWithZeroProbabilityError(edge)

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
            raise NotAnEdgeError(edge)
        if edge.uid in self._edges:
            raise MemberAlreadyRegisteredError(edge)
        edge.graph = self
        self._edges[edge.uid] = edge

    def _add_node(self, node):
        """Adds a node to the self._nodes dict."""
        if not node.is_node_instance:
            raise NotANodeError(node)
        if node.uid in self._nodes:
            raise MemberAlreadyRegisteredError(node)
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
                raise NotMemberOfGraphError(m)
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
                raise NotMemberOfGraphError(m)

        to_process = set(members)
        all_deleted = None  # All nodes marked as deleted.
        prev_deleted = self.deleted_nodes  # Previously marked as deleted.
        while to_process:
            # Mark all the members to process as deleted.  This doesn't use
            # Graph.mark_members_deleted as it would needlessly check if the
            # members are members of this Graph.
            for member in to_process:
                member.mark_deleted()

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
    def is_node_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is a Node instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

    @property
    def is_edge_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

    @property
    def is_oredge_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is an OrEdge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

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
            if self._graph == graph:
                raise MemberAlreadyRegisteredError(self)
            else:
                raise NotMemberOfGraphError(self)
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
            raise NotAnEdgeError(edge)
        if edge.to_node != self:
            raise NodeIsNotPartOfEdgeError(self, edge)
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
            raise NotAnEdgeError(edge)
        if edge.from_node != self:
            raise NodeIsNotPartOfEdgeError(self, edge)

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
                    raise NotAnOrEdgeError(edge)
            else:
                # Edges in the outgoing edges set are of type Edge.
                if edge.is_oredge_instance:
                    raise NotAnEdgeError(edge)

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
            return EMPTY_FROZEN_SET  # Not a cycle.

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
            raise DeletedMemberInUseError(self)

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
            raise DeletedMemberInUseError(self)

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
            raise DeletedMemberInUseError(self)
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
            raise DeletedMemberInUseError(self)

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
            raise DeletedMemberInUseError(self)

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
            raise DeletedMemberInUseError(self)
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


class Edge(Member):
    """Directed edge graph member."""

    def __init__(self, from_node, to_node):
        # Check
        if not from_node.is_node_instance:
            raise NotANodeError(from_node)
        if not to_node.is_node_instance:
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
    def is_edge_instance(self):
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

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

        # set.add and set.remove is slow. Use |= and -= and the same set as
        # much as possible.
        self_set = set((self,))

        # Get all needed data from the edge and then mark it as deleted.
        graph = self.graph
        from_node = self.__from_node
        to_node = self.__to_node
        probability = self.probability
        self._deleted = True
        graph._deleted_edges |= self_set

        # Update/invalidate incoming caches:
        # ----------------------------------

        # Update incoming edges cache set of the from node.
        if to_node._incoming_edges_without_deleted is None:  # noqa  # pylint: disable=protected-access
            to_node._incoming_edges_without_deleted = set(  # noqa  # pylint: disable=protected-access
                to_node._incoming_edges - self_set)  # noqa  # pylint: disable=protected-access
        else:
            to_node._incoming_edges_without_deleted -= self_set  # noqa  # pylint: disable=protected-access

        # Update incoming nodes cache set of the from node.
        if to_node._incoming_nodes_without_deleted is None:  # noqa  # pylint: disable=protected-access
            to_node._incoming_nodes_without_deleted = set(  # noqa  # pylint: disable=protected-access
                to_node._incoming_nodes - set((from_node,)))  # noqa  # pylint: disable=protected-access
        else:
            to_node._incoming_nodes_without_deleted -= set((from_node,))  # noqa  # pylint: disable=protected-access

        # The incoming edges and nodes sets without the deleted nodes have been
        # touched on this node.  Mark this node as touched to reset it on
        # Graph.unmark_deleted().
        to_node._incoming_without_deleted_touched = True  # noqa  # pylint: disable=protected-access

        # Increase cache level of the incoming recursive nodes to invalidate
        # these caches graph-wide.  Once a single cache will be accessed it
        # uses this information to detect that the cache could be invalid and
        # then evaluates if the cache is still valid by its built at cache
        # level and invalidated at cache level fields.  See the
        # _incoming_nodes_recursive_get_cache method for details.
        graph._mark_deleted_incoming_cache_level += 1
        graph_cl = graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
        from_node._incoming_nodes_recursive_invalidated_at_cl = graph_cl  # noqa  # pylint: disable=protected-access

        # Update/invalidate outgoing caches:
        # ----------------------------------

        # The outgoing caches only need to be recalculated if an OrEdge has
        # been marked as deleted that has other OrEdges in parallel as marking
        # an edge as deleted only affects the nodes and edges above (incoming).
        # If an Edge or OrEdge with probability 1.0 will be marked as deleted
        # then this will also mark its from node and all nodes above as deleted
        # and hence there is no node or edge above that would need their cache
        # updated/invalidated and all nodes and edges below it still have a
        # valid cache.
        if probability < 1.0:
            # Update outgoing edges cache set of the from node.
            # Note: from_node._outgoing_edges_without_deleted is always
            # initialized because checking the probability initializes it.
            from_node._outgoing_edges_without_deleted -= self_set  # noqa  # pylint: disable=protected-access

            # Update outgoing nodes cache set of the from node.
            if from_node._outgoing_nodes_without_deleted is None:  # noqa  # pylint: disable=protected-access
                from_node._outgoing_nodes_without_deleted = set(  # noqa  # pylint: disable=protected-access
                    from_node._outgoing_nodes - set((to_node,)))  # noqa  # pylint: disable=protected-access
            else:
                from_node._outgoing_nodes_without_deleted -= set((to_node,))  # noqa  # pylint: disable=protected-access

            # The incoming edges and nodes sets without the deleted nodes have
            # been touched on this node.  Mark this node as touched to reset it
            # on Graph.unmark_deleted().
            from_node._outgoing_without_deleted_touched = True  # noqa  # pylint: disable=protected-access

            # Increase cache level of the outgoing recursive nodes to
            # invalidate these caches graph-wide.  Once a single cache will be
            # accessed it uses this information to detect that the cache could
            # be invalid and then evaluates if the cache is still valid by its
            # built at cache level and invalidated at cache level fields.
            # see the _outgoing_nodes_recursive_get_cache method for details.
            graph._mark_deleted_outgoing_cache_level += 1
            graph_cl = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
            from_node._outgoing_nodes_recursive_invalidated_at_cl = graph_cl  # noqa  # pylint: disable=protected-access

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
    def is_edge_instance(self):
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

    @property
    def is_oredge_instance(self):
        """Returns True if this object is an OrEdge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

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
