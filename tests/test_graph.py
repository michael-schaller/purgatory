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


class OrEdge(purgatory.graph.OrEdge):

    def __str__(self):
        return "%s --p=%.3f--> %s" % (
            self.from_node.uid, self.probability, self.to_node.uid)

    def _nodes_to_edge_uid(self, from_node, to_node):
        return "%s --> %s" % (from_node.uid, to_node.uid)

    def _init_str(self):
        pass  # Custom __str__ implementation.


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

    def test_member_comparison(self):
        m11 = Member(uid="1")
        m12 = Member(uid="1")
        m2 = Member(uid="2")
        m3 = Member(uid="3")

        self.assertTrue(m11 == m12)
        self.assertTrue(m2 != m3)
        self.assertTrue(m2 < m3)
        self.assertTrue(m2 <= m3)
        self.assertTrue(m3 <= m3)
        self.assertTrue(m2 > m11)
        self.assertTrue(m2 >= m11)
        self.assertTrue(m2 >= m2)

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

    def test_deleted_member_in_use_error_incoming_nodes(self):
        nt = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nt)

        Graph(init_nodes_and_edges)

        nt.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nt.incoming_nodes  # pylint: disable=pointless-statement

    def test_deleted_member_in_use_error_incoming_nodes_recursive(self):
        nt = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nt)

        Graph(init_nodes_and_edges)

        nt.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nt.incoming_nodes_recursive  # pylint: disable=pointless-statement

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

    def test_deleted_member_in_use_error_outgoing_nodes(self):
        nf = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nf)

        Graph(init_nodes_and_edges)

        nf.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nf.outgoing_nodes  # pylint: disable=pointless-statement

    def test_deleted_member_in_use_error_outgoing_nodes_recursive(self):
        nf = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(nf)

        Graph(init_nodes_and_edges)

        nf.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            nf.outgoing_nodes_recursive  # pylint: disable=pointless-statement

    def test_mark_deleted_node(self):
        n = Node()

        def init_nodes_and_edges(graph):
            graph._add_node(n)

        g = Graph(init_nodes_and_edges)
        self.assertFalse(n.deleted)

        n.mark_deleted()
        self.assertTrue(n.deleted)

        g.unmark_deleted()
        self.assertFalse(n.deleted)

    def test_mark_deleted_edge_and_graph(self):
        # Relationship: nf --ei--> n --eo--> nt
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

        self.assertFalse(nf.deleted)
        self.assertFalse(ei.deleted)
        self.assertFalse(n.deleted)
        self.assertFalse(eo.deleted)
        self.assertFalse(nt.deleted)

        nf.mark_deleted()

        self.assertTrue(nf.deleted)
        self.assertTrue(ei.deleted)
        self.assertFalse(n.deleted)
        self.assertFalse(eo.deleted)
        self.assertFalse(nt.deleted)

        g.unmark_deleted()

        self.assertFalse(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertFalse(ei.deleted)
        self.assertFalse(eo.deleted)

        ei.mark_deleted()

        self.assertTrue(nf.deleted)
        self.assertTrue(ei.deleted)
        self.assertFalse(n.deleted)
        self.assertFalse(eo.deleted)
        self.assertFalse(nt.deleted)

        g.unmark_deleted()

        self.assertFalse(n.deleted)
        self.assertFalse(nf.deleted)
        self.assertFalse(nt.deleted)
        self.assertFalse(ei.deleted)
        self.assertFalse(eo.deleted)

        n.mark_deleted()

        self.assertTrue(nf.deleted)
        self.assertTrue(ei.deleted)
        self.assertTrue(n.deleted)
        self.assertTrue(eo.deleted)
        self.assertFalse(nt.deleted)

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
            n._add_incoming_edge(m)

    def test_node_add_outgoing_edge_raise_not_an_edge_error(self):
        n = Node()
        m = Member()
        with self.assertRaises(purgatory.graph.NotAnEdgeError):
            n._add_outgoing_edge(m)

    def test_node_add_incoming_edge_raise_node_is_not_part_of_edge_error(self):
        n = Node()
        e = Edge(Node(), Node())
        with self.assertRaises(purgatory.graph.NodeIsNotPartOfEdgeError):
            n._add_incoming_edge(e)

    def test_node_add_outgoing_edge_raise_node_is_not_part_of_edge_error(self):
        n = Node()
        e = Edge(Node(), Node())
        with self.assertRaises(purgatory.graph.NodeIsNotPartOfEdgeError):
            n._add_outgoing_edge(e)

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
            nt._add_incoming_edge(e)

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
            nf._add_outgoing_edge(e)

    def test_edge_default_probability(self):
        e = Edge(Node(), Node())
        self.assertEquals(e.probability, 1.0)

    def test_deleted_edge_probability_raises_deleted_member_in_use_error(self):
        nf = Node()
        nt = Node()
        e = Edge(nf, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt)
            graph._add_edge(e)

        Graph(init_nodes_and_edges)

        e.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            e.probability  # pylint: disable=pointless-statement

    def test_del_or_edge_probability_raises_deleted_member_in_use_error(self):
        nf = Node()
        nt = Node()
        e = OrEdge(nf, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt)
            graph._add_edge(e)

        Graph(init_nodes_and_edges)

        e.mark_deleted()
        with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
            e.probability  # pylint: disable=pointless-statement

    def test_raise_not_an_or_edge_error(self):
        def init_nodes_and_edges(graph):
            nf = Node()
            graph._add_node(nf)

            nt = Node()
            graph._add_node(nt)

            e1 = Edge(nf, nt)
            graph._add_edge(e1)

            with self.assertRaises(purgatory.graph.NotAnEdgeError):
                OrEdge(nf, nt)

        Graph(init_nodes_and_edges)

    def test_raise_not_an_edge_error(self):

        def init_nodes_and_edges(graph):
            nf = Node()
            graph._add_node(nf)

            nt = Node()
            graph._add_node(nt)

            e1 = OrEdge(nf, nt)
            graph._add_edge(e1)

            with self.assertRaises(purgatory.graph.NotAnOrEdgeError):
                Edge(nf, nt)

        Graph(init_nodes_and_edges)

    def test_mark_delete_with_probabilties(self):
        #               /--e2(p=0.5)--> n3
        # n1 --e1--> n2
        #               \--e3(p=0.5)--> n4 --e4--> n5
        #
        # The edges e2 and e3 are in an or-relationship.  Marking n5 as deleted
        # should also mark e4, n4 and e3 as deleted.  e2 should have a
        # probability of 1.0 afterwards.
        n1 = Node()
        n2 = Node()
        n3 = Node()
        n4 = Node()
        n5 = Node()

        e1 = Edge(n1, n2)
        e2 = OrEdge(n2, n3)
        e3 = OrEdge(n2, n4)
        e4 = Edge(n4, n5)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)
            graph._add_node(n4)
            graph._add_node(n5)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)
            graph._add_edge(e4)

        Graph(init_nodes_and_edges)

        self.assertFalse(n1.deleted)
        self.assertFalse(n2.deleted)
        self.assertFalse(n3.deleted)
        self.assertFalse(n4.deleted)
        self.assertFalse(n5.deleted)

        self.assertFalse(e1.deleted)
        self.assertFalse(e2.deleted)
        self.assertFalse(e3.deleted)
        self.assertFalse(e4.deleted)

        n5.mark_deleted()

        self.assertFalse(n1.deleted)
        self.assertFalse(n2.deleted)
        self.assertFalse(n3.deleted)
        self.assertTrue(n4.deleted)
        self.assertTrue(n5.deleted)

        self.assertFalse(e1.deleted)
        self.assertFalse(e2.deleted)
        self.assertTrue(e3.deleted)
        self.assertTrue(e4.deleted)

        self.assertTrue(abs(e2.probability - 1.0) < purgatory.graph.EPSILON)

    def test_improbable_edge_raises_edge_with_zero_probability_error(self):

        class ImprobableEdge(Edge):

            @property
            def probability(self):
                return 0.0

        nf = Node()
        nt = Node()
        e = ImprobableEdge(nf, nt)

        def init_nodes_and_edges(graph):
            graph._add_node(nf)
            graph._add_node(nt)
            graph._add_edge(e)

        with self.assertRaises(purgatory.graph.EdgeWithZeroProbabilityError):
            Graph(init_nodes_and_edges)

    def test_node_incoming_nodes_recursive(self):
        # n1 --e1--\       /--e3(p=0.5)--> n4
        #           --> n3
        # n2 --e2--/       \--e4(p=0.5)--> n5
        n1 = Node()
        n2 = Node()
        n3 = Node()
        n4 = Node()
        n5 = Node()

        e1 = Edge(n1, n3)
        e2 = Edge(n2, n3)
        e3 = OrEdge(n3, n4)
        e4 = OrEdge(n3, n5)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)
            graph._add_node(n4)
            graph._add_node(n5)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)
            graph._add_edge(e4)

        Graph(init_nodes_and_edges)

        self.assertTrue(abs(e3.probability - 0.5) < purgatory.graph.EPSILON)
        self.assertTrue(abs(e4.probability - 0.5) < purgatory.graph.EPSILON)

        self.assertSetEqual(n3.incoming_nodes, set((n1, n2)))
        self.assertSetEqual(n3.incoming_nodes_recursive, set((n1, n2)))

        self.assertSetEqual(n4.incoming_nodes, set((n3,)))
        self.assertSetEqual(n4.incoming_nodes_recursive, set((n1, n2, n3)))

        self.assertSetEqual(n5.incoming_nodes, set((n3,)))
        self.assertSetEqual(n5.incoming_nodes_recursive, set((n1, n2, n3)))

        e3.mark_deleted()
        self.assertTrue(abs(e4.probability - 1.0) < purgatory.graph.EPSILON)
        self.assertSetEqual(n4.incoming_nodes, set())
        self.assertSetEqual(n4.incoming_nodes_recursive, set())

    def test_node_outgoing_nodes_recursive(self):
        # n1 --e1--\       /--e3(p=0.5)--> n4
        #           --> n3
        # n2 --e2--/       \--e4(p=0.5)--> n5
        n1 = Node()
        n2 = Node()
        n3 = Node()
        n4 = Node()
        n5 = Node()

        e1 = Edge(n1, n3)
        e2 = Edge(n2, n3)
        e3 = OrEdge(n3, n4)
        e4 = OrEdge(n3, n5)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)
            graph._add_node(n4)
            graph._add_node(n5)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)
            graph._add_edge(e4)

        g = Graph(init_nodes_and_edges)

        self.assertTrue(abs(e3.probability - 0.5) < purgatory.graph.EPSILON)
        self.assertTrue(abs(e4.probability - 0.5) < purgatory.graph.EPSILON)

        self.assertSetEqual(n3.outgoing_nodes, set((n4, n5)))
        self.assertSetEqual(n3.outgoing_nodes_recursive, set((n4, n5)))

        self.assertSetEqual(n1.outgoing_nodes, set((n3,)))
        self.assertSetEqual(n1.outgoing_nodes_recursive, set((n3, n4, n5)))

        self.assertSetEqual(n2.outgoing_nodes, set((n3,)))
        self.assertSetEqual(n2.outgoing_nodes_recursive, set((n3, n4, n5)))

        e3.mark_deleted()
        self.assertTrue(abs(e4.probability - 1.0) < purgatory.graph.EPSILON)
        self.assertSetEqual(n1.outgoing_nodes, set((n3,)))
        self.assertSetEqual(n1.outgoing_nodes_recursive, set((n3, n5)))

        # The graph consists of 3 layer.
        g.unmark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n1, n2)))  # Layer 1
        n1.mark_deleted()
        n2.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n3,)))     # Layer 2
        n3.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n4, n5)))  # Layer 3
        n4.mark_deleted()
        n5.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set())  # Nothing left

    def test_simple_self_cycle(self):
        n = Node()
        e = Edge(n, n)

        def init_nodes_and_edges(graph):
            graph._add_node(n)
            graph._add_edge(e)

        Graph(init_nodes_and_edges)
        self.assertTrue(n.in_cycle)
        self.assertSetEqual(n.cycle_nodes, set((n,)))

    def test_cycle(self):
        # n1 --e1--> n2
        #   \<--e2--/
        n1 = Node(uid="n1")
        n2 = Node(uid="n2")
        e1 = Edge(n1, n2)
        e2 = Edge(n2, n1)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)

            graph._add_edge(e1)
            graph._add_edge(e2)

        g = Graph(init_nodes_and_edges)

        self.assertTrue(n1.in_cycle)
        self.assertTrue(n2.in_cycle)
        self.assertSetEqual(n1.cycle_nodes, set((n1, n2)))
        self.assertSetEqual(n2.cycle_nodes, set((n1, n2)))

        for m in [e1, e2, n1, n2]:
            g.unmark_deleted()
            m.mark_deleted()
            self.assertTrue(n1.deleted)
            self.assertTrue(n2.deleted)
            self.assertTrue(e1.deleted)
            self.assertTrue(e2.deleted)

        # The graph consists of 1 layer.
        g.unmark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n1, n2)))
        n1.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set())  # Nothing left

    def test_two_cycles(self):
        # n1 --e1--> n2 --e2--> n3 <--e4-- n4 <--e5-- n5
        #   \<-------e3--------/  \-------e6-------->/
        n1 = Node(uid="n1")
        n2 = Node(uid="n2")
        n3 = Node(uid="n3")
        n4 = Node(uid="n4")
        n5 = Node(uid="n5")
        e1 = Edge(n1, n2)
        e2 = Edge(n2, n3)
        e3 = Edge(n3, n1)
        e4 = Edge(n4, n3)
        e5 = Edge(n5, n4)
        e6 = Edge(n3, n5)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)
            graph._add_node(n4)
            graph._add_node(n5)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)
            graph._add_edge(e4)
            graph._add_edge(e5)
            graph._add_edge(e6)

        g = Graph(init_nodes_and_edges)

        for n in [n1, n2, n3, n4, n5]:
            self.assertTrue(n.in_cycle)
            self.assertSetEqual(n.cycle_nodes, set([n1, n2, n3, n4, n5]))

        for m1 in [n1, n2, n3, n4, n5, e1, e2, e3, e4, e5, e6]:
            g.unmark_deleted()
            m1.mark_deleted()
            for m2 in [n1, n2, n3, n4, n5, e1, e2, e3, e4, e5, e6]:
                self.assertTrue(m2.deleted)

        # The graph consists of 1 layer.
        g.unmark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n1, n2, n3, n4, n5)))
        n1.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set())  # Nothing left

    def test_break_cycle(self):
        # n1 ------e1------> n2 --e2(p=0.5)--> n3
        #   \<--e3(p=0.5)--/
        n1 = Node(uid="n1")
        n2 = Node(uid="n2")
        n3 = Node(uid="n3")

        e1 = Edge(n1, n2)
        e2 = OrEdge(n2, n3)
        e3 = OrEdge(n2, n1)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)

        g = Graph(init_nodes_and_edges)

        self.assertTrue(n1.in_cycle)
        self.assertTrue(n2.in_cycle)
        self.assertFalse(n3.in_cycle)

        e3.mark_deleted()
        self.assertTrue(abs(e2.probability - 1.0) < purgatory.graph.EPSILON)
        self.assertFalse(n1.in_cycle)
        self.assertFalse(n2.in_cycle)
        self.assertFalse(n3.in_cycle)

        # The graph consists of 3 layers.
        g.unmark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n1, n2)))  # Layer 1
        n1.mark_deleted()  # Breaks cycle; doesn't mark n2 as deleted
        self.assertTrue(n1.deleted)
        self.assertFalse(n2.deleted)
        self.assertSetEqual(g.head_nodes_flat, set((n2,)))  # Layer 2
        n2.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n3,)))  # Layer 3
        n3.mark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set())  # Nothing left

    def test_two_disconnected_cycles(self):
        # n1 --e1--> n2 -> e3 -> n3 --e4--> n4
        #   \<--e2--/              \<--e5--/
        n1 = Node(uid="n1")
        n2 = Node(uid="n2")
        n3 = Node(uid="n3")
        n4 = Node(uid="n4")

        e1 = Edge(n1, n2)
        e2 = Edge(n2, n1)
        e3 = Edge(n2, n3)
        e4 = Edge(n3, n4)
        e5 = Edge(n4, n3)

        def init_nodes_and_edges(graph):
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_node(n3)
            graph._add_node(n4)

            graph._add_edge(e1)
            graph._add_edge(e2)
            graph._add_edge(e3)
            graph._add_edge(e4)
            graph._add_edge(e5)

        g = Graph(init_nodes_and_edges)

        for n in [n1, n2, n3, n4]:
            self.assertTrue(n.in_cycle)

        self.assertSetEqual(n1.cycle_nodes, set((n1, n2)))
        self.assertSetEqual(n2.cycle_nodes, set((n1, n2)))

        self.assertSetEqual(n3.cycle_nodes, set((n3, n4)))
        self.assertSetEqual(n4.cycle_nodes, set((n3, n4)))

        # n3 and n4 are in a cycle and thus are a single unit.  Marking either
        # one has to mark the other one as deleted as well and as they are the
        # foundation of the graph the rest of the graph will be marked deleted
        # as well.
        n4.mark_deleted()
        for n in [n1, n2, n3, n4, e1, e2, e3, e4, e5]:
            self.assertTrue(n.deleted)
        g.unmark_deleted()
        n3.mark_deleted()
        for n in [n1, n2, n3, n4, e1, e2, e3, e4, e5]:
            self.assertTrue(n.deleted)

        # The graph consists of 2 layers.
        g.unmark_deleted()
        self.assertSetEqual(g.head_nodes_flat, set((n1, n2)))  # Layer 1
        n1.mark_deleted()
        self.assertTrue(n2.deleted)
        self.assertSetEqual(g.head_nodes_flat, set((n3, n4)))  # Layer 2
        n3.mark_deleted()
        self.assertTrue(n4.deleted)
        self.assertSetEqual(g.head_nodes_flat, set())  # Nothing left

        # Check head_nodes (non flat)
        g.unmark_deleted()
        heads = set(g.head_nodes)
        self.assertEquals(len(heads), 1)
        head = heads.pop()
        self.assertSetEqual(head, set((n1, n2)))  # Layer 1
        n1.mark_deleted()
        heads = set(g.head_nodes)
        self.assertEquals(len(heads), 1)
        head = heads.pop()
        self.assertSetEqual(head, set((n3, n4)))  # Layer 2
        n3.mark_deleted()
        heads = set(g.head_nodes)
        self.assertEquals(len(heads), 0)  # Nothing left
