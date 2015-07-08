"""Tests for purgatory.dpkg_graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


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
            self.assertEquals(edge.probability, 1.0)

    def test_target_edge_probabilities(self):
        graph = self.graph
        for edge in graph.target_edges.values():
            edge.mark_deleted()
            with self.assertRaises(purgatory.graph.DeletedMemberInUseError):
                edge.probability  # pylint: disable=pointless-statement
            edge.unmark_deleted()

            self.assertTrue(edge.probability <= 1.0)
            self.assertTrue(edge.probability > 0.0)


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
