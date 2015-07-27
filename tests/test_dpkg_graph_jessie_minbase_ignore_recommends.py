"""Tests for purgatory.dpkg_graph with a jessie dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import json
import logging
import os.path

import purgatory.dpkg_graph
import purgatory.logging

import tests.common
import tests.common_dpkg_graph


class TestJessieIgnoreRecommendsDpkgGraph(
        tests.common.PurgatoryTestCase,
        tests.common_dpkg_graph.CommonDpkgGraphTestsMixin):
    """Tests for dpkg_graph with Jessie amd64 minbase without recommends."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__graph = None

    def setUp(self):
        super().setUp()
        self.graph.unmark_deleted()

    @property
    def graph(self):
        if self.__graph is None:
            logging.debug(
                "Initializing DpkgGraph (Jessie amd64 minbase no recommends) "
                "...")
            dpkg_db = os.path.abspath(
                "test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz")
            self.__graph = purgatory.dpkg_graph.DpkgGraph(
                ignore_recommends=True, dpkg_db=dpkg_db)
            logging.debug("DpkgGraph initialized")
        return self.__graph

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

    def test_jesse_layer_count(self):
        # Determines all layers of the graph by the help of the
        # Graph.leaf_nodes_flat property and Node.mark_deleted() method.
        graph = self.graph
        layer = None
        layer_counts = []
        layer_index = -1

        while layer or layer_index == -1:
            layer_index += 1
            self.assertLess(layer_index, 200)

            layer = graph.leaf_nodes_flat
            if layer:
                layer_counts.append(len(layer))
            for node in layer:
                node.mark_deleted()

        # Data has been taken from this test after all other tests passed.
        self.assertListEqual(
            layer_counts,
            [18, 23, 13, 14, 8, 16, 6, 17, 7, 9, 10, 4, 8, 5, 6, 4, 3, 2, 1, 1,
             1, 1, 3, 3, 10, 6, 1, 1, 2, 2, 2, 2, 1, 1, 5, 4, 3, 2, 2, 2, 1, 7,
             1, 1])

    def test_jessie_mark_members_including_obsolete_deleted(self):
        graph = self.graph
        result = {}

        # For each leaf calculate the nodes that would be marked removed if
        # the leaf would be removed including the obsolete nodes.
        leafs = graph.leaf_nodes
        for leaf in leafs:
            # Determine the InstalledPackageNodes that have been marked as
            # deleted.
            graph.mark_members_including_obsolete_deleted(leaf)
            deleted = [str(node) for node in graph.deleted_nodes if isinstance(
                node, purgatory.dpkg_graph.InstalledPackageNode)]
            deleted.sort()

            leaf = [str(node) for node in leaf]
            leaf.sort()
            leaf_str = "[%s]" % ", ".join(leaf)

            result[leaf_str] = deleted  # Key must be a string for json.

            # Reset graph.
            graph.unmark_deleted()

        with open("test-data/dpkg/jessie-amd64-minbase-leafs-" +
                  "ignore-recommends.json", "r") as f:
            content = f.read()
        prev_result = json.loads(content)
        self.assertDictEqual(result, prev_result)
