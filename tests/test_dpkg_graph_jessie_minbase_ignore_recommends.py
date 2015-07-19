"""Tests for purgatory.dpkg_graph with a jessie dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


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
