"""Profiling for purgatory.dpkg_graph with the system dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import logging
import unittest

import purgatory.dpkg_graph

from . import common


class TestSystemDpkgGraph(common.PurgatoryTestCase):
    """Profiling for purgatory.dpkg_graph with the system's dpkg database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__graph = None

    def setUp(self):
        super().setUp()
        self.graph.unmark_deleted()

    @property
    def graph(self):
        if self.__graph is None:
            self.__init_graph()
        return self.__graph

    def __init_graph(self):
        logging.debug(
            "Initializing DpkgGraph (local system amd64 minbase) ...")
        self.__graph = purgatory.dpkg_graph.DpkgGraph(
            dpkg_db="/var/lib/dpkg/status")
        logging.debug("DpkgGraph initialized")

    @unittest.skip
    @common.cprofile
    def test_profile_graph_init(self):
        self.__init_graph()

    @unittest.skip
    @common.cprofile
    def test_profile_in_cycle(self):
        # Tests the assumption that if a node is in its recursive incoming
        # nodes set that it also has to be in its recursive outgoing nodes set.
        # A node is in both sets if it is part of a cycle.
        for node in self.graph.nodes.values():
            i = node in node.incoming_nodes_recursive
            o = node in node.outgoing_nodes_recursive
            self.assertEqual(i, o)

    @unittest.skip
    @common.cprofile
    def test_profile_leafs(self):
        # Determines all layers of the graph by the help of the
        # Graph.leafs_flat property and Node.mark_deleted() method.
        # This test ensures that all graphs can be dissected into layers by
        # this method.  If this isn't the case within the layer_index limit
        # then something is wrong with the Graph.leafs property.
        graph = self.graph
        layer = None
        layer_index = -1

        while layer or layer_index == -1:
            layer_index += 1
            self.assertLess(layer_index, 200)

            layer = graph.leafs_flat
            for node in layer:
                node.mark_deleted()

    @unittest.skip
    @common.cprofile
    def test_profile_mark_members_including_obsolete_deleted(self):
        graph = self.graph

        # For each leaf calculate the nodes that would be marked removed if
        # the leaf would be removed including the obsolete nodes.  This is the
        # typical workload in case Purgatory shows the leaf nodes and details.
        for leaf in graph.leafs:
            graph.mark_members_including_obsolete_deleted(leaf)
            graph.deleted_nodes  # To gather details about the deleted nodes.  # noqa  # pylint: disable=pointless-statement
            graph.unmark_deleted()  # Reset graph.

    @unittest.skip
    @common.cprofile
    def test_profile_graphviz_graph(self):
        self.graph.graphviz_graph  # pylint: disable=pointless-statement
