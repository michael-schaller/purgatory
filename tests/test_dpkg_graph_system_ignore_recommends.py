"""Tests for purgatory.dpkg_graph with the system dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import logging

import purgatory.dpkg_graph
import purgatory.logging

import tests.common
import tests.common_dpkg_graph


class TestSystemIgnoreRecommendsDpkgGraph(
        tests.common.PurgatoryTestCase,
        tests.common_dpkg_graph.CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with the system's dpkg database."""

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
                "Initializing DpkgGraph (local system amd64 minbase no "
                "recommends) ...")
            self.__graph = purgatory.dpkg_graph.DpkgGraph(
                ignore_recommends=True, dpkg_db="/var/lib/dpkg/status")
            logging.debug("DpkgGraph initialized")
        return self.__graph
