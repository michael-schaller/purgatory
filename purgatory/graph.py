"""A hierarchical Graph with nodes and directed edges that have probabilities.

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

As a Graph is hierachical the mark_deleted methods on Nodes and Edges behave
differently than with classical/generic Graph implementations.  Marking a Node
as deleted also marks its incoming and outgoing edges as deleted as edges can't
exist without their nodes existing.  Marking an Edge as deleted typically marks
everything above the from-node of the Edge as deleted as the Nodes and Edges
can't exist anymore without their foundation.  The only exception to this rule
is made if the hierarchie isn't violated due to edges in an or-relationship.
"""

import abc
import types

import purgatory.error


EPSILON = 0.00001


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

        # Init
        super().__init__()
        self._init_nodes_and_edges()

        # Freeze
        self.__nodes = types.MappingProxyType(self.__nodes)
        self.__edges = types.MappingProxyType(self.__edges)
        self.__freeze_nodes_incoming_outgoing_edges()

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
        """Returns a dict view (uid:edge) of the edges in the graph."""
        return self.__edges

    @property
    def nodes(self):
        """Returns a dict view (uid:node) of the nodes in the graph."""
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
        for edge in self.__edges.values():
            edge._deleted = False  # pylint: disable=protected-access
        for node in self.__nodes.values():
            node._deleted = False  # pylint: disable=protected-access


class Member(abc.ABC):
    """Abstract base class for members (nodes, edges) of a Graph."""

    def __init__(self, uid):
        # Private
        self.__hash = hash(uid)
        self.__uid = uid
        self.__graph = None

        # Protected
        self._str = None
        self._deleted = False

        # Init
        super().__init__()
        self._init_str()

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False
        if self.__hash != hash(other):
            return False
        return self.__uid == other.uid

    def __hash__(self):
        return self.__hash

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self._str

    def __repr__(self):
        return "%s(uid='%s')" % (self.__class__.__name__, self.__uid)

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
        if not self.__graph:
            raise UnregisteredMemberInUseError(self)
        return self.__graph

    @graph.setter
    def graph(self, graph):
        """Sets the graph to which this member belongs.

        The graph can only be set once.
        """
        if self.__graph:
            raise MemberAlreadyRegisteredError(self)
        self.__graph = graph

    @property
    def uid(self):
        """Returns the uid of the graph member."""
        return self.__uid

    @abc.abstractmethod
    def mark_deleted(self):
        """Marks the graph member as deleted."""


class Node(Member):  # pylint: disable=abstract-method
    """Abstract Node base class."""

    def __init__(self, uid):
        # Private
        self.__incoming_edges = set()
        self.__outgoing_edges = set()

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
    def incoming_edges(self):
        """Returns set of all directly incoming edges.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)
        edges = set()
        for edge in self.__incoming_edges:
            if not edge.deleted:
                edges.add(edge)
        return frozenset(edges)

    @property
    def incoming_nodes(self):
        """Returns set of all directly incoming nodes.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        nodes = set()
        for edge in self.incoming_edges:
            # Node can't be deleted as edge isn't deleted either.
            nodes.add(edge.from_node)
        return frozenset(nodes)

    @property
    def outgoing_edges(self):
        """Returns set of all directly outgoing edges.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        if self._deleted:
            raise DeletedMemberInUseError(self)
        edges = set()
        for edge in self.__outgoing_edges:
            if not edge.deleted:
                edges.add(edge)
        return frozenset(edges)

    @property
    def outgoing_nodes(self):
        """Returns set of all directly outgoing nodes.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        nodes = set()
        for edge in self.outgoing_edges:
            # Node can't be deleted as edge isn't deleted either.
            nodes.add(edge.to_node)
        return frozenset(nodes)

    def mark_deleted(self):
        """Marks the node and its incoming and outgoing edges as deleted."""
        if self._deleted:
            return  # Stop recursion

        # Get all needed data from the node and then mark it as deleted.
        incoming_edges = self.incoming_edges
        outgoing_edges = self.outgoing_edges
        self._deleted = True

        # Mark the incoming/outgoing edges as deleted as edges can't exist
        # without their nodes.
        for edge in incoming_edges:
            edge.mark_deleted()
        for edge in outgoing_edges:
            edge.mark_deleted()


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
        if self._deleted:
            return  # Stop recursion

        # Get all needed data from the edge and then mark it as deleted.
        probability = self.probability
        from_node = self.from_node
        self._deleted = True

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
