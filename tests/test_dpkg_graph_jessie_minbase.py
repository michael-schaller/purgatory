"""Tests for purgatory.dpkg_graph with a jessie dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import logging
import os.path

import purgatory.dpkg_graph
import purgatory.logging

import tests.common
import tests.common_dpkg_graph


class TestJessieDpkgGraph(
        tests.common.PurgatoryTestCase,
        tests.common_dpkg_graph.CommonDpkgGraphTestsMixin):
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
            dpkg_db = os.path.abspath(
                "test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz")
            self.__graph = purgatory.dpkg_graph.DpkgGraph(dpkg_db=dpkg_db)
            logging.debug("DpkgGraph initialized")
        return self.__graph

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
