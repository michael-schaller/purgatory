"""Tests for purgatory.graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring

# Tests are allowed to access protected members:
# pylint: disable=protected-access


import unittest

import purgatory.graph
import purgatory.logging


class Graph(purgatory.graph.Graph):

    def __init__(self, inae_fn):
        self.__inae_fn = inae_fn
        super().__init__()

    def _init_nodes_and_edges(self):
        self.__inae_fn(self)


class Member(purgatory.graph.Member):
    """Neither a node nor an edge."""

    def __init__(self, uid=None):
        if uid is None:
            uid = id(self)
        super().__init__(uid)

    def _init_str(self):
        self._str = repr(self)

    def mark_deleted(self):
        self._deleted = True

    def unmark_deleted(self):
        self._deleted = False


class Node(purgatory.graph.Node):
    """A node."""

    def __init__(self, uid=None):
        if uid is None:
            uid = id(self)
        super().__init__(uid)

    def _init_str(self):
        self._str = repr(self)


class Edge(purgatory.graph.Edge):

    def _nodes_to_edge_uid(self, from_node, to_node):
        return "%s --> %s" % (from_node.uid, to_node.uid)

    def _init_str(self):
        self._str = self.uid


def setUpModule():
    """Module-wide setup."""
    purgatory.logging.configure_root_logger()


class TestGraph(unittest.TestCase):
    """Tests for purgatory.graph."""

    def test_empty_graph(self):
        called = [False]

        def init_nodes_and_edges(unused_graph):
            called[0] = True

        Graph(init_nodes_and_edges)
        self.assertTrue(called[0])

    def test_not_a_node_error(self):

        def init_nodes_and_edges(graph):
            m = Member()
            with self.assertRaises(purgatory.graph.NotANodeError):
                graph._add_node(m)

        Graph(init_nodes_and_edges)

    def test_not_an_edge_error(self):

        def init_nodes_and_edges(graph):
            m = Member()
            with self.assertRaises(purgatory.graph.NotAnEdgeError):
                graph._add_edge(m)

        Graph(init_nodes_and_edges)

    def test_member_alread_registered_error_with_node(self):

        def init_nodes_and_edges(graph):
            n = Node()
            graph._add_node(n)
            with self.assertRaises(
                    purgatory.graph.MemberAlreadyRegisteredError):
                graph._add_node(n)

        Graph(init_nodes_and_edges)

    def test_member_alread_registered_error_with_edge(self):

        def init_nodes_and_edges(graph):
            n1 = Node()
            n2 = Node()
            e = Edge(n1, n2)
            graph._add_edge(e)
            with self.assertRaises(
                    purgatory.graph.MemberAlreadyRegisteredError):
                graph._add_edge(e)

        Graph(init_nodes_and_edges)

    def test_member_alread_registered_error_with_graph(self):
        n = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(n)

        Graph(init_nodes_and_edges)
        with self.assertRaises(purgatory.graph.MemberAlreadyRegisteredError):
            Graph(init_nodes_and_edges)

    def test_unregistered_member_in_use_error(self):

        def init_nodes_and_edges(unused_graph):
            m = Member()
            with self.assertRaises(
                    purgatory.graph.UnregisteredMemberInUseError):
                m.graph  # pylint: disable=pointless-statement

        Graph(init_nodes_and_edges)

    def test_add_node_dedup(self):

        def init_nodes_and_edges(graph):
            n1 = Node(uid="test")
            n2 = Node(uid="test")

            nr, dup = graph._add_node_dedup(n1)
            self.assertFalse(dup)
            self.assertEquals(id(n1), id(nr))
            self.assertNotEquals(id(n2), id(nr))

            nr, dup = graph._add_node_dedup(n1)
            self.assertTrue(dup)
            self.assertEquals(id(n1), id(nr))  # Dedup because some object
            self.assertNotEquals(id(n2), id(nr))

            nr, dup = graph._add_node_dedup(n2)
            self.assertTrue(dup)
            self.assertEquals(id(n1), id(nr))  # Dedup because same uid
            self.assertNotEquals(id(n2), id(nr))

        Graph(init_nodes_and_edges)

    def test_node_incoming_edges_and_nodes(self):
        nf1 = Node()
        nf2 = Node()
        nt = Node()

        e1 = Edge(nf1, nt)
        e2 = Edge(nf2, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf1)
            graph._add_node(nf2)
            graph._add_node(nt)

            graph._add_edge(e1)
            graph._add_edge(e2)

        Graph(init_nodes_and_edges)

        ies = nt.incoming_edges
        self.assertTrue(e1 in ies)
        self.assertTrue(e2 in ies)
        self.assertEquals(len(ies), 2)

        ins = nt.incoming_nodes
        self.assertTrue(nf1 in ins)
        self.assertTrue(nf2 in ins)
        self.assertEquals(len(ins), 2)

    def test_node_incoming_edges_empty(self):
        nt = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nt)

        Graph(init_nodes_and_edges)

        ies = nt.incoming_edges
        self.assertEquals(len(ies), 0)

    def test_deleted_member_in_use_error_incoming_edges(self):
        nt = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nt)

        Graph(init_nodes_and_edges)

        nt.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nt.incoming_edges  # pylint: disable=pointless-statement

    def test_node_outgoing_edges_and_nodes(self):
        nf = Node()
        nt1 = Node()
        nt2 = Node()

        e1 = Edge(nf, nt1)
        e2 = Edge(nf, nt2)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt1)
            graph._add_node(nt2)

            graph._add_edge(e1)
            graph._add_edge(e2)

        Graph(init_nodes_and_edges)

        oes = nf.outgoing_edges
        self.assertTrue(e1 in oes)
        self.assertTrue(e2 in oes)
        self.assertEquals(len(oes), 2)

        ons = nf.outgoing_nodes
        self.assertTrue(nt1 in ons)
        self.assertTrue(nt2 in ons)
        self.assertEquals(len(ons), 2)

    def test_node_outgoing_edges_empty(self):
        nf = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nf)

        Graph(init_nodes_and_edges)

        oes = nf.outgoing_edges
        self.assertEquals(len(oes), 0)

    def test_deleted_member_in_use_error_outgoing_edges(self):
        nf = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nf)

        Graph(init_nodes_and_edges)

        nf.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nf.outgoing_edges  # pylint: disable=pointless-statement

    def test_mark_deleted_node(self):
        n = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(n)

        Graph(init_nodes_and_edges)
        self.assertFalse(n.deleted)

        n.mark_deleted()
        self.assertTrue(n.deleted)

        n.unmark_deleted()
        self.assertFalse(n.deleted)

    def test_mark_deleted_edge_and_graph(self):
        n = Node()
        nf = Node()
        nt = Node()

        ei = Edge(nf, n)
        eo = Edge(n, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(n)
            graph._add_node(nf)
            graph._add_node(nt)

            graph._add_edge(ei)
            graph._add_edge(eo)

        g = Graph(init_nodes_and_edges)

        self.assertFalse(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertFalse(ei.deleted)
        self.assertFalse(eo.deleted)

        n.mark_deleted()

        self.assertTrue(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertTrue(ei.deleted)
        self.assertTrue(eo.deleted)

        ei.unmark_deleted()
        self.assertFalse(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertFalse(ei.deleted)
        self.assertTrue(eo.deleted)

        nf.mark_deleted()
        self.assertFalse(n.deleted)
        self.assertTrue(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertTrue(ei.deleted)
        self.assertTrue(eo.deleted)

        g.unmark_deleted()
        self.assertFalse(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertFalse(ei.deleted)
        self.assertFalse(eo.deleted)

    def test_member_init_str(self):

        class TestMember(Member):

            def _init_str(self):
                self._str = "test"

        m = TestMember()
        self.assertEquals(str(m), "test")

    def test_not_a_node_error_from_node(self):
        m = Member()
        nt = Node()
        with self.assertRaises(purgatory.graph.NotANodeError):
            Edge(m, nt)

    def test_not_a_node_error_to_node(self):
        nf = Node()
        m = Member()
        with self.assertRaises(purgatory.graph.NotANodeError):
            Edge(nf, m)

    def test_member_equals(self):
        n = Node("1")
        n1 = Node("1")
        n2 = Node("2")
        e = Edge(n1, n2)

        self.assertEquals(n, n1)
        self.assertNotEquals(n, n2)
        self.assertNotEquals(n1, n2)

        self.assertNotEquals(n, e)
        self.assertNotEquals(n1, e)
        self.assertNotEquals(n2, e)

    def test_graph_nodes_property(self):
        n1 = Node()
        n2 = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)

        graph = Graph(init_nodes_and_edges)

        nodes = graph.nodes.values()
        self.assertTrue(n1 in nodes)
        self.assertTrue(n2 in nodes)
        self.assertEquals(len(nodes), 2)

    def test_graph_edges_property(self):
        n1 = Node()
        n2 = Node()

        e1 = Edge(n1, n2)
        e2 = Edge(n2, n1)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)

            graph._add_edge(e1)
            graph._add_edge(e2)

        graph = Graph(init_nodes_and_edges)

        edges = graph.edges.values()
        self.assertTrue(e1 in edges)
        self.assertTrue(e2 in edges)
        self.assertEquals(len(edges), 2)

    def test_graph_nodes_add_node_after_init(self):

        def init_nodes_and_edges(unused_graph):
            pass

        graph = Graph(init_nodes_and_edges)
        n = Node()
        with self.assertRaises(TypeError):
            graph.nodes[n.uid] = n

    def test_graph_nodes_add_edge_after_init(self):

        def init_nodes_and_edges(unused_graph):
            pass

        graph = Graph(init_nodes_and_edges)
        e = Edge(Node(), Node())
        with self.assertRaises(TypeError):
            graph.edges[e.uid] = e

    def test_node_add_incoming_edge_raise_not_an_edge_error(self):
        n = Node()
        m = Member()
        with self.assertRaises(purgatory.graph.NotAnEdgeError):
            n.add_incoming_edge(m)

    def test_node_add_outgoing_edge_raise_not_an_edge_error(self):
        n = Node()
        m = Member()
        with self.assertRaises(purgatory.graph.NotAnEdgeError):
            n.add_outgoing_edge(m)

    def test_node_add_incoming_edge_raise_node_is_not_part_of_edge_error(self):
        n = Node()
        e = Edge(Node(), Node())
        with self.assertRaises(purgatory.graph.NodeIsNotPartOfEdgeError):
            n.add_incoming_edge(e)

    def test_node_add_outgoing_edge_raise_node_is_not_part_of_edge_error(self):
        n = Node()
        e = Edge(Node(), Node())
        with self.assertRaises(purgatory.graph.NodeIsNotPartOfEdgeError):
            n.add_outgoing_edge(e)

    def test_member_graph_property(self):
        n = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(n)

        graph = Graph(init_nodes_and_edges)
        self.assertEquals(n.graph, graph)

    def test_node_incoming_edges_frozen_after_graph_inited(self):
        nf = Node()
        nt = Node()
        e = Edge(nf, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt)
            graph._add_edge(e)

        Graph(init_nodes_and_edges)
        with self.assertRaises(AttributeError):
            nt.add_incoming_edge(e)

    def test_node_outgoing_edges_frozen_after_graph_inited(self):
        nf = Node()
        nt = Node()
        e = Edge(nf, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt)
            graph._add_edge(e)

        Graph(init_nodes_and_edges)
        with self.assertRaises(AttributeError):
            nf.add_outgoing_edge(e)

    def test_edge_default_probability(self):
        e = Edge(Node(), Node())
        self.assertEquals(e.probability, 1.0)

    def test_deleted_edge_probability_raises_deleted_member_in_use_error(self):
        e = Edge(Node(), Node())
        e.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            e.probability  # pylint: disable=pointless-statement
