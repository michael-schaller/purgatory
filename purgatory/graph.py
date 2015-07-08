"""Graph with nodes and directed edges that have probabilities."""

import abc
import types

import purgatory.error


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

        # Caches
        self.__node_to_incoming_edges = None  # node.uid:set(incoming edges):
        self.__node_to_outgoing_edges = None  # node.uid:set(incoming edges)

        # Init and freeze
        super().__init__()
        self._init_nodes_and_edges()
        self.__nodes = types.MappingProxyType(self.__nodes)
        self.__edges = types.MappingProxyType(self.__edges)
        self._init_node_to_incoming_edges()
        self._init_node_to_outgoing_edges()

    @abc.abstractmethod
    def _init_nodes_and_edges(self):
        """Initializes the nodes of the graph."""

    def _init_node_to_incoming_edges(self):
        """Initializes the node to incoming edges cache."""
        self.__node_to_incoming_edges = {}
        for edge in self.__edges.values():
            node_uid = edge.to_node.uid
            incoming_edges = self.__node_to_incoming_edges.get(node_uid)
            if not incoming_edges:
                incoming_edges = set()
                self.__node_to_incoming_edges[node_uid] = incoming_edges
            incoming_edges.add(edge)

        # Freeze
        for node_uid, edges in self.__node_to_incoming_edges.items():
            self.__node_to_incoming_edges[node_uid] = frozenset(edges)
        self.__node_to_incoming_edges = types.MappingProxyType(
            self.__node_to_incoming_edges)

    def _init_node_to_outgoing_edges(self):
        """Initializes the node to outgoing edges cache."""
        self.__node_to_outgoing_edges = {}
        for edge in self.__edges.values():
            node_uid = edge.from_node.uid
            outgoing_edges = self.__node_to_outgoing_edges.get(node_uid)
            if not outgoing_edges:
                outgoing_edges = set()
                self.__node_to_outgoing_edges[node_uid] = outgoing_edges
            outgoing_edges.add(edge)

        # Freeze
        for node_uid, edges in self.__node_to_outgoing_edges.items():
            self.__node_to_outgoing_edges[node_uid] = frozenset(edges)
        self.__node_to_outgoing_edges = types.MappingProxyType(
            self.__node_to_outgoing_edges)

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

    def incoming_edges_for_node(self, node):
        """Returns the set of incoming edges for the given node.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        if node.deleted:
            raise DeletedMemberInUseError(node)
        incoming_edges = self.__node_to_incoming_edges.get(node.uid, None)
        if not incoming_edges:
            return EMPTY_FROZEN_SET
        edges = set()
        for edge in incoming_edges:
            if not edge.deleted:
                edges.add(edge)
        return frozenset(edges)

    def outgoing_edges_for_node(self, node):
        """Returns the set of outgoing edges for the given node.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        if node.deleted:
            raise DeletedMemberInUseError(node)
        outgoing_edges = self.__node_to_outgoing_edges.get(node.uid, None)
        if not outgoing_edges:
            return EMPTY_FROZEN_SET
        edges = set()
        for edge in outgoing_edges:
            if not edge.deleted:
                edges.add(edge)
        return frozenset(edges)

    def unmark_deleted(self):
        """Unmarks all graph members as deleted."""
        for edge in self.__edges.values():
            edge.unmark_deleted()
        for node in self.__nodes.values():
            node.unmark_deleted()


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

    @abc.abstractmethod
    def unmark_deleted(self):
        """Unmarks the graph member as deleted."""


class Node(Member):  # pylint: disable=abstract-method
    """Abstract Node base class."""

    def __init__(self, uid):
        super().__init__(uid)

    @property
    def incoming_edges(self):
        """Returns set of all incoming edges.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        return self.graph.incoming_edges_for_node(self)

    @property
    def outgoing_edges(self):
        """Returns set of all outgoing edges.

        The set is independent of the edge probability but honors the deleted
        state.
        """
        return self.graph.outgoing_edges_for_node(self)

    def mark_deleted(self):
        """Marks the node and its incoming and outgoing edges as deleted."""
        for edge in self.incoming_edges:
            edge.mark_deleted()
        for edge in self.outgoing_edges:
            edge.mark_deleted()
        self._deleted = True

    def unmark_deleted(self):
        """Unmarks the node as deleted. This doesn't affect edges."""
        self._deleted = False


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

    @abc.abstractmethod
    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""

    @abc.abstractproperty
    def probability(self):
        """Returns the probability of this edge."""

    @property
    def from_node(self):
        """Returns the source (from) node of the edge."""
        return self.__from_node

    @property
    def to_node(self):
        """Returns the destination (to) node of the edge."""
        return self.__to_node

    def mark_deleted(self):
        """Marks the edge as deleted. This doesn't affect its nodes."""
        self._deleted = True

    def unmark_deleted(self):
        """Unmarks the edge and its nodes as deleted."""
        self.from_node.unmark_deleted()
        self.to_node.unmark_deleted()
        self._deleted = False
