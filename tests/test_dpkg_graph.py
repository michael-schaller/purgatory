"""Tests for purgatory.dpkg_graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import unittest.mock

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

    def test_depndency_edge_ctor_raise_unsupported_dependency_type_error(self):
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
