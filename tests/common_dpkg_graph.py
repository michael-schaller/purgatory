"""Common code for all test dpkg_graph_*.py files."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import itertools
import logging
import unittest

import purgatory.dpkg_graph


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

    def test_in_cycle(self):
        # Tests the assumption that if a node is in its recursive incoming
        # nodes set that it also has to be in its recursive outgoing nodes set.
        # A node is in both sets if it is part of a cycle.
        for node in self.graph.nodes:
            i = node in node.incoming_nodes_recursive
            o = node in node.outgoing_nodes_recursive
            self.assertEquals(i, o)

    def test_leafs(self):
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

    def test_outgoing_nodes_recursive_get_cache(self):
        graph = self.graph
        dynamic = purgatory.graph.Node.dynamic_result_type
        static = purgatory.graph.Node.static_result_type
        graph_cl = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access

        # By default no node has a cache and the cache type is always dynamic.
        for node in graph.nodes:
            cr, ct = node._outgoing_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                graph_cl=graph_cl)
            self.assertEquals(cr, None)
            self.assertEquals(ct, dynamic)

        # Generate outgoing nodes recursive caches for all nodes and check
        # the cache type.
        for node in graph.nodes:
            node.outgoing_nodes_recursive  # noqa  # pylint: disable=pointless-statement
            cr, ct = node._outgoing_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                graph_cl=graph_cl)

            # The cache type must be for all nodes either default or static.
            self.assertNotEquals(ct, dynamic)

            # If the cache type is static then all nodes of the cache result
            # must be also of type static.
            if ct == static:
                for cr_node in cr:
                    _, ct2 = cr_node._outgoing_nodes_recursive_get_cache(  # noqa  # pylint: disable=protected-access
                        graph_cl=graph_cl)
                    self.assertEquals(ct2, static)

    def test_mark_members_including_obsolete_deleted(self):
        graph = self.graph

        # For each leaf calculate the nodes that would be marked removed if
        # the leaf would be removed including the obsolete nodes.  This is the
        # typical workload in case Purgatory shows the leaf nodes and details.
        deleted_clusters = set()
        for leaf in graph.leafs:
            graph.mark_members_including_obsolete_deleted(leaf)
            deleted_clusters.add(graph.deleted_nodes)
            graph.unmark_deleted()  # Reset graph.

        # Each of the clusters of deleted nodes must be disjunct or otherwise
        # mark_members_including_obsolete_deleted would have marked nodes as
        # deleted that are still needed by other leaf nodes/cycles.
        for c1, c2 in itertools.permutations(deleted_clusters, 2):
            self.assertFalse(c1 & c2)
