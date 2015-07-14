"""Tests for purgatory.dpkg_graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import logging
import os.path
import tempfile
import unittest

import purgatory.dpkg_graph
import purgatory.logging

import tests.common


def setUpModule():
    """Module-wide setup."""
    purgatory.logging.configure_root_logger()


class TestEmptyDpkgGraph(unittest.TestCase):
    """Tests for purgatory.dpkg_graph with an empty dpkg status database."""

    def test_constructor(self):
        with self.assertRaises(purgatory.dpkg_graph.EmptyAptCacheError):
            with tempfile.NamedTemporaryFile() as tf:
                purgatory.dpkg_graph.DpkgGraph(dpkg_db=tf.name)


class CommonDpkgGraphTestsMixin(object):

    def test_add_installed_package_node_after_init(self):
        graph = self.graph
        ipns = graph.installed_package_nodes
        with self.assertRaises(TypeError):
            ipns["test"] = "test"

    def test_add_installed_dependency_node_after_init(self):
        graph = self.graph
        idns = graph.installed_dependency_nodes
        with self.assertRaises(TypeError):
            idns["test"] = "test"

    def test_add_dependency_edge_after_init(self):
        graph = self.graph
        des = graph.dependency_edges
        with self.assertRaises(TypeError):
            des["test"] = "test"

    def test_add_target_edge_after_init(self):
        graph = self.graph
        tes = graph.target_edges
        with self.assertRaises(TypeError):
            tes["test"] = "test"

    def test_dependency_edge_probabilities(self):
        graph = self.graph
        for edge in graph.dependency_edges.values():
            self.assertTrue(
                abs(edge.probability - 1.0) < purgatory.graph.EPSILON)

    def test_target_edge_probabilities(self):
        graph = self.graph

        # Mark all target edges of the graph as deleted.
        for edge in graph.target_edges.values():  # Random order!
            if edge.deleted:
                continue  # Already marked deleted.
            self.assertTrue(edge.probability <= 1.0)
            self.assertTrue(edge.probability > 0.0)
            edge.mark_deleted()

        # All installed dependency nodes must be marked as deleted.
        for node in graph.installed_dependency_nodes.values():
            self.assertTrue(node.deleted)

    def test_graph_mark_deleted_equals_apt_mark_delete(self):
        # Tests if Node.mark_deleted on a DpkgGraph behaves the sames as
        # Package.mark_delete on an Apt Cache.  This test only works on
        # DpkgGraph objects with ignore_recommends=True as Graph's mark_deleted
        # methods honor the hierarchy and the DependencyEdges of type
        # Recommends are part of the hierarchy.  On the other side Apt/dpkg are
        # asymmetric as installs honor Recommends but deletes don't honor
        # Recommends.
        # Furthermore this test is quite expensive and hence only the first 5
        # random package nodes are tested.  If this test fails this limitation
        # should be removed and the test should be rerun to identify the
        # failing packages.  Once the failing packages have been identified it
        # is recommends to temporarily limit this test to (some of) the failing
        # packages, fix the issue and then to retry with all packages before
        # reenabling the limitation.
        graph = self.graph
        cache = graph.cache

        if not graph._ignore_recommends:  # pylint: disable=protected-access
            return unittest.skip(
                "Graph contains DependencyEdge objects of type Recommends")

        count = 0
        for package_node1 in graph.installed_package_nodes.values():  # Random
            count += 1
            if count > 5:
                return
            logging.debug("Package: %s", package_node1.package)

            cache.clear()
            graph.unmark_deleted()

            package_node1.mark_deleted()  # Graph
            try:
                package_node1.package.mark_delete()  # Apt's Cache
            except SystemError:
                # Apt resolver error -> Try next package
                continue

            # Get set of packages that is marked for deletion from the Graph.
            graph_deleted = set()
            for package_node2 in graph.installed_package_nodes.values():
                if package_node2.deleted:
                    graph_deleted.add(package_node2.package)

            # Get set of package that are marked for change from the Cache.
            cache_changed = set(cache.get_changes())

            if graph_deleted != cache_changed:
                logging.debug("Fail Package: %s", package_node1.package)

                only_graph = graph_deleted - cache_changed
                if only_graph:
                    logging.debug("Packages marked in Graph but not in Cache:")
                    for package in only_graph:
                        logging.debug("  %s", package)

                only_cache = cache_changed - graph_deleted
                if only_cache:
                    logging.debug("Packages marked in Cache but not in Graph:")
                    for package in only_cache:
                        logging.debug("  %s", package)

                self.fail("Mark deleted mismatch!")


class TestJessieDpkgGraph(unittest.TestCase, CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with Jessie amd64 minbase data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dpkg_db = os.path.abspath(
            "test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz")
        self.graph = purgatory.dpkg_graph.DpkgGraph(dpkg_db=dpkg_db)

    def setUp(self):
        self.graph.unmark_deleted()

    def test_jessie_nodes_and_edges_count(self):
        graph = self.graph
        # Installed package nodes count has been taken after the debootstrap
        # run.  See test-data/dpkg/HOWTO for more details.
        self.assertEquals(len(graph.installed_package_nodes), 101)

        # Installed dependency nodes count has been taken from debug log output
        # during constructor run.  The count also has to be higher if
        # recommends is honored than without recommends.
        self.assertEquals(len(graph.installed_dependency_nodes), 140)

        # Target edges count must be the same as installed dependency nodes
        # count as the minbase setup has only one installed package per
        # dependency - hence the same count.
        self.assertEquals(len(graph.target_edges), 140)


class TestJessieIgnoreRecommendsDpkgGraph(
        unittest.TestCase, CommonDpkgGraphTestsMixin):
    """Tests for dpkg_graph with Jessie amd64 minbase without recommends."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dpkg_db = os.path.abspath(
            "test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz")
        self.graph = purgatory.dpkg_graph.DpkgGraph(
            ignore_recommends=True, dpkg_db=dpkg_db)

    def setUp(self):
        self.graph.unmark_deleted()

    def test_jessie_nodes_and_edges_count(self):
        graph = self.graph
        # Installed package nodes count has been taken after the debootstrap
        # run.  See test-data/dpkg/HOWTO for more details.
        self.assertEquals(len(graph.installed_package_nodes), 101)

        # Installed dependency nodes count has been taken from debug log output
        # during constructor run.  The count also has to be lower if recommends
        # is ignored than with recommends.
        self.assertEquals(len(graph.installed_dependency_nodes), 138)

        # Target edges count must be the same as installed dependency nodes
        # count as the minbase setup has only one installed package per
        # dependency - hence the same count.
        self.assertEquals(len(graph.target_edges), 138)


class TestSystemDpkgGraph(unittest.TestCase, CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with the system's dpkg database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = None
        self.__init_graph()

    def __init_graph(self):
        self.graph = purgatory.dpkg_graph.DpkgGraph(
            dpkg_db="/var/lib/dpkg/status")

    def setUp(self):
        self.graph.unmark_deleted()

    @unittest.skip
    @tests.common.cprofile
    def test_profile(self):
        self.__init_graph()

    @unittest.skip
    @tests.common.cprofile
    def test_cycle(self):
        # Tests the assumption that if a node is in its recursive incoming
        # nodes set that it also has to be in its recursive outgoing nodes set.
        # A node is in both sets if it is part of a cycle.
        for node in self.graph.nodes.values():
            i = node in node.incoming_nodes_recursive
            o = node in node.outgoing_nodes_recursive
            self.assertEquals(i, o)


class TestSystemIgnoreRecommendsDpkgGraph(
        unittest.TestCase, CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with the system's dpkg database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = None
        self.__init_graph()

    def __init_graph(self):
        self.graph = purgatory.dpkg_graph.DpkgGraph(
            ignore_recommends=True, dpkg_db="/var/lib/dpkg/status")

    def setUp(self):
        self.graph.unmark_deleted()
