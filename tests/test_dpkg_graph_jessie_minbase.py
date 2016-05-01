"""Tests for purgatory.dpkg_graph with a jessie dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import gzip
import json
import logging
import tempfile

import purgatory.graph.graphviz
import purgatory.dpkg_graph

from . import common
from . import common_dpkg_graph


class TestJessieDpkgGraph(
        common.PurgatoryTestCase,
        common_dpkg_graph.CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with Jessie amd64 minbase data."""

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
                "Initializing DpkgGraph (Jessie amd64 minbase) ...")
            gz = "../test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz"
            tmp = tempfile.NamedTemporaryFile(prefix="dpkg-status-db-")
            with gzip.open(gz, "rb") as f:
                tmp.write(f.read())
            self.__graph = purgatory.dpkg_graph.DpkgGraph(dpkg_db=tmp.name)
            tmp.close()  # Deletes the temporary file.
            logging.debug("DpkgGraph initialized")
        return self.__graph

    def test_jessie_nodes_and_edges_count(self):
        graph = self.graph
        # Installed package nodes count has been taken after the debootstrap
        # run.  See test-data/dpkg/HOWTO for more details.
        self.assertEqual(len(graph.package_nodes), 101)

        # Target versions nodes count has been taken from debug log output
        # during constructor run.  The count also has to be higher or equals if
        # recommends is honored than without recommends.
        self.assertEqual(len(graph.target_versions_nodes), 85)

        # Target edges count must be the same as target versions nodes count as
        # the minbase setup has only one installed package per dependency -
        # hence the same count.
        self.assertEqual(len(graph.target_edges), 85)

    def test_jessie_layer_count(self):
        # Determines all layers of the graph by the help of the
        # Graph.leafs_flat property and Node.mark_deleted() method.
        graph = self.graph
        layer = None
        layer_counts = []
        layer_index = -1

        while layer or layer_index == -1:
            layer_index += 1
            self.assertLess(layer_index, 200)

            layer = graph.leafs_flat
            if layer:
                layer_counts.append(len(layer))
            for node in layer:
                node.mark_deleted()

        # Data has been taken from this test after all other tests passed.
        self.assertListEqual(
            layer_counts,
            [16, 7, 7, 4, 4, 8, 8, 10, 7, 10, 11, 8, 7, 7, 2, 2, 1, 1, 1, 1, 3,
             3, 6, 6, 1, 1, 5, 4, 4, 2, 1, 1, 1, 1, 1, 4, 4, 2, 2, 2, 2, 6, 1,
             1])

    def test_jessie_mark_members_including_obsolete_deleted(self):
        graph = self.graph
        result = {}

        # For each leaf calculate the nodes that would be marked removed if
        # the leaf would be removed including the obsolete nodes.
        leafs = graph.leafs
        for leaf in leafs:
            # Determine the PackageNodes that have been marked as deleted.
            graph.mark_members_including_obsolete_deleted(leaf)
            deleted = [str(node) for node in graph.deleted_nodes if isinstance(
                node, purgatory.dpkg_graph.PackageNode)]
            deleted.sort()

            leaf = [str(node) for node in leaf]
            leaf.sort()
            leaf_str = "[%s]" % ", ".join(leaf)

            result[leaf_str] = deleted  # Key must be a string for json.

            # Reset graph.
            graph.unmark_deleted()

        with open(
                "../test-data/dpkg/jessie-amd64-minbase-leafs.json", "r") as f:
            content = f.read()
        prev_result = json.loads(content)
        self.assertDictEqual(result, prev_result)

    def test_graphviz(self):
        self.graph.graphviz_graph  # pylint: disable=pointless-statement
