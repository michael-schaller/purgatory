"""Tests for purgatory.dpkg_graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring

# Tests are allowed to access protected members:
# pylint: disable=protected-access


import unittest.mock

import purgatory.graph
import purgatory.dpkg_graph

from . import common


class TestDpkgGraph(common.PurgatoryTestCase):
    """Tests for purgatory.dpkg_graph."""

    def test_package_node_ctor_raises_is_not_installed_error(self):
        pkg_mock = unittest.mock.Mock(is_installed=False)
        self.assertRaises(
            purgatory.dpkg_graph.PackageIsNotInstalledError,
            purgatory.dpkg_graph.PackageNode, pkg_mock)

    def test_dependency_node_ctor_raise_is_not_installed_error(self):
        # A dependency that doesn't have installed target versions isn't
        # installed either.
        dep_mock = unittest.mock.Mock(installed_target_versions=set())
        self.assertRaises(
            purgatory.dpkg_graph.DependencyIsNotInstalledError,
            purgatory.dpkg_graph.DependencyNode, dep_mock)

    def test_dep_edge_ctor_raise_unsupported_dependency_type_error(self):
        # to_node.dependency.rawtype has to be set to an unsupported dependency
        # type to trigger an UnsupportedDependencyTypeError in the
        # DependencyEdge constructor.
        dep_mock = unittest.mock.Mock(rawtype="Unsupported")
        to_node_mock = unittest.mock.Mock(dependency=dep_mock)
        from_node_mock = unittest.mock.Mock()

        self.assertRaises(
            purgatory.dpkg_graph.UnsupportedDependencyTypeError,
            purgatory.dpkg_graph.DependencyEdge, from_node_mock, to_node_mock)

    def test_target_edge_str(self):
        # Target edge with probability of 0.5.  The string representation of
        # the target edge has to include the probability.
        from_node_mock = unittest.mock.Mock(
            outgoing_edges=set((unittest.mock.Mock(), unittest.mock.Mock())))
        from_node_mock.__str__ = unittest.mock.Mock(
            return_value="from_node_mock")

        to_node_mock = unittest.mock.Mock()
        to_node_mock.__str__ = unittest.mock.Mock(
            return_value="to_node_mock")

        target_edge = purgatory.dpkg_graph.TargetEdge(
            from_node_mock, to_node_mock)
        self.assertEquals(
            str(target_edge), "from_node_mock --p=0.500--> to_node_mock")

        # Target edge with probability of 0.333.  The string representation of
        # the target edge has to include the probability.
        from_node_mock = unittest.mock.Mock(
            outgoing_edges=set(
                (unittest.mock.Mock(), unittest.mock.Mock(),
                 unittest.mock.Mock())))
        from_node_mock.__str__ = unittest.mock.Mock(
            return_value="from_node_mock")

        target_edge = purgatory.dpkg_graph.TargetEdge(
            from_node_mock, to_node_mock)
        self.assertEquals(
            str(target_edge), "from_node_mock --p=0.333--> to_node_mock")

        # Target edge with probability of 1.0.  The string representation of
        # the target edge doesn't include the probability.
        from_node_mock = unittest.mock.Mock(
            outgoing_edges=set((unittest.mock.Mock(),)))
        from_node_mock.__str__ = unittest.mock.Mock(
            return_value="from_node_mock")

        target_edge = purgatory.dpkg_graph.TargetEdge(
            from_node_mock, to_node_mock)
        self.assertEquals(
            str(target_edge), "from_node_mock --> to_node_mock")

    def test_keep_node(self):
        # A minimalistic Graph.
        class Graph(purgatory.graph.Graph):

            def __init__(self, inae_fn):
                self.__inae_fn = inae_fn
                super().__init__()

            def _init_nodes_and_edges(self):
                self.__inae_fn(self)

        # A minimalistic Node.
        class Node(purgatory.graph.Node):

            def __init__(self, uid=None):
                if uid is None:
                    uid = id(self)
                super().__init__(uid)

            def _init_str(self):
                self._str = repr(self)

        # A minimalistic Edge.
        class Edge(purgatory.graph.Edge):

            def _nodes_to_edge_uid(self, from_node, to_node):
                return "%s --> %s" % (from_node.uid, to_node.uid)

            def _init_str(self):
                self._str = self.uid

        # Minimalistic Graph layout:
        # kn --> n2
        # n1 -->/
        kn = purgatory.dpkg_graph.KeepNode()
        n1 = Node(uid="n1")
        n2 = Node(uid="n2")
        e1 = Edge(kn, n2)
        e2 = Edge(n1, n2)

        # Initialize the Nodes and Edges of the minimalisitic Graph.
        def _init_nodes_and_edges(graph):
            graph._add_node(kn)
            graph._add_node(n1)
            graph._add_node(n2)
            graph._add_edge(e1)
            graph._add_edge(e2)

            # Adding a second keep node must fail as all keep nodes have
            # the same uid.
            kn2 = purgatory.dpkg_graph.KeepNode()
            self.assertRaises(
                purgatory.graph.MemberAlreadyRegisteredError,
                graph._add_node, kn2)

            # Creating an incoming edge for a KeepNode must fail.
            self.assertRaises(
                purgatory.dpkg_graph.KeepNodeMustBeLeafError,
                Edge, n1, kn)

        # Minimalistic Graph layout:
        # kn --> n2
        # n1 -->/
        g = Graph(_init_nodes_and_edges)
        self.assertSetEqual(g.nodes, set((kn, n1, n2)))

        # Test that KeepNodes can't be directly marked deleted.
        self.assertRaises(
            purgatory.dpkg_graph.KeepNodeCanNotBeMarkedDeletedError,
            kn.mark_deleted)

        # Test that KeepNodes can't be indirectly marked deleted.
        self.assertRaises(
            purgatory.dpkg_graph.KeepNodeCanNotBeMarkedDeletedError,
            n2.mark_deleted)

        # Ensure that nodes that don't need to be kept can still be marked
        # as deleted.
        n1.mark_deleted()

        # Minimalistic Graph layout:
        # kn --> n2
        #
        self.assertSetEqual(g.nodes, set((kn, n2)))
