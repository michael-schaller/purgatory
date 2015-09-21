"""Graph representing installed packages in the dpkg status database."""


import logging
import types

import apt_pkg
import apt

from . import dependency_edge
from . import dependency_node
from . import error
from . import package_node
from . import target_edge

from .. import graph


class DpkgGraph(graph.Graph):
    """Graph representing installed packages in the dpkg status database."""

    def __init__(self, ignore_recommends=False, dpkg_db=None):
        """DpkgGraph constructor.

        Args:
            ignore_recommends: Ignores all dependencies of type Recommends.
                Defaults to False.
            dpkg_db: Absolute path to a dpkg status database file. Defaults to
                the system's dpkg status database file.
        """
        # Private
        self.__dpkg_db = dpkg_db
        self.__cache = None
        self.__package_nodes = {}  # uid:node
        self.__dependency_nodes = {}  # uid:node
        self.__dependency_edges = {}  # uid:edge
        self.__target_edges = {}  # uid:edge

        # Protected
        self._ignore_recommends = ignore_recommends

        # Init
        self.__init_cache()
        logging.debug("Initializing dpkg graph ...")
        super().__init__()  # Calls _init_nodes and _init_edges.

        # Log
        logging.debug("dpkg graph contains:")
        logging.debug("  Installed package nodes: %d",
                      len(self.__package_nodes))
        logging.debug("  Installed dependency nodes: %d",
                      len(self.__dependency_nodes))
        logging.debug("  Dependency edges: %d",
                      len(self.__dependency_edges))
        logging.debug("  Target edges: %d",
                      len(self.__target_edges))

    def __init_cache(self):
        """Initializes the Apt cache in use by the DpkgGraph."""
        # Read the system's Apt configuration.
        logging.debug("Initializing Apt configuration ...")
        apt_pkg.init_config()  # pylint: disable=no-member
        conf = apt_pkg.config  # pylint: disable=no-member

        # Tweak the system's Apt configuration to only read the dpkg status
        # database as Purgatory is only interested in the installed packages.
        # This has the nice sideffect that this cuts down the Apt cache opening
        # time drastically as less files need to be parsed.
        dpkg_db = conf["Dir::State::status"]
        conf.clear("Dir::State")
        if self.__dpkg_db:
            conf["Dir::State::status"] = self.__dpkg_db
        else:
            conf["Dir::State::status"] = dpkg_db
        self.__dpkg_db = conf["Dir::State::status"]
        logging.debug("dpkg status database: %s", self.__dpkg_db)

        # As Purgatory uses a special configuration the Apt cache will be
        # built in memory so that the valid cache on disk for the full
        # configuration isn't overwritten.
        conf["Dir::Cache::pkgcache"] = ""
        conf["Dir::Cache::srcpkgcache"] = ""

        # Initialize Apt with the tweaked config.
        logging.debug("Initializing Apt system ...")
        apt_pkg.init_system()  # pylint: disable=no-member

        # Opening Apt cache. This step actually reads the dpkg status database.
        logging.debug("Opening Apt cache ...")
        cache = apt.cache.Cache()

        # Filter Apt cache to only contain installed packages.
        filtered_cache = apt.cache.FilteredCache(cache)
        filtered_cache.set_filter(apt.cache.InstalledFilter())
        logging.debug("%d installed packages in the Apt cache",
                      len(filtered_cache))

        if not len(filtered_cache):
            raise error.EmptyAptCacheError()
        self.__cache = filtered_cache

    def __init_nodes_and_edges_phase1(self):
        """Phase 1 of the initialization of the dpkg graph.

        Phase 1 of the initialization adds the following to the graph:
        * Installed package nodes
        * Installed dependency nodes
        * Dependency edges (between installed package and dependency nodes)
        """
        # Add installed package nodes.
        for pkg in self.__cache:
            ipn = package_node.PackageNode(pkg)
            self._add_node(ipn)
            self.__package_nodes[ipn.uid] = ipn

            # Add installed dependency nodes and dependency edges
            if self._ignore_recommends:
                deps = ipn.version.get_dependencies("PreDepends", "Depends")
            else:
                deps = ipn.version.get_dependencies(
                    "PreDepends", "Depends", "Recommends")
            for dep in deps:  # apt.package.Dependency
                # Add installed dependency node.
                try:
                    idn = dependency_node.DependencyNode(dep)
                except error.DependencyIsNotInstalledError:
                    if dep.rawtype == "Recommends":
                        # Recommended packages don't need to be installed.
                        continue
                idn, dup = self._add_node_dedup(idn)
                if not dup:
                    self.__dependency_nodes[idn.uid] = idn

                # Add dependency edge from the installed package node to the
                # installed dependency node.
                de = dependency_edge.DependencyEdge(ipn, idn)
                self._add_edge(de)
                self.__dependency_edges[de.uid] = de

        # Freeze all dicts that have been filled so far.
        self.__package_nodes = types.MappingProxyType(
            self.__package_nodes)
        self.__dependency_nodes = types.MappingProxyType(
            self.__dependency_nodes)
        self.__dependency_edges = types.MappingProxyType(
            self.__dependency_edges)

    def __init_nodes_and_edges_phase2(self):
        """Phase 1 of the initialization of the dpkg graph.

        Phase 2 of the initialization adds the following to the graph:
        * Target edges (between installed dependency nodes and packages nodes)
        """
        pkg_to_uid = package_node.PackageNode.pkg_to_uid
        for idn in self.__dependency_nodes.values():
            # Add target edges from the installed dependency node to the
            # installed package node.
            for itver in idn.installed_target_versions:
                itpkg = itver.package
                itpkg_uid = pkg_to_uid(itpkg)
                itpn = self.__package_nodes[itpkg_uid]

                te = target_edge.TargetEdge(idn, itpn)
                self._add_edge(te)
                self.__target_edges[te.uid] = te

        # Freeze the target edges dict.
        self.__target_edges = types.MappingProxyType(self.__target_edges)

    def _init_nodes_and_edges(self):
        """Initializes the nodes and edges of the DpkgGraph."""
        self.__init_nodes_and_edges_phase1()
        self.__init_nodes_and_edges_phase2()

    @property
    def cache(self):
        """Returns the Apt Cache object in use by this DpkgGraph object."""
        return self.__cache

    @property
    def dependency_nodes(self):
        """Returns a set of the installed dependency nodes.

        The set doesn't include dependency nodes that have been marked deleted.
        """
        return {node for node in self.__dependency_nodes.values()
                if not node.deleted}

    @property
    def package_nodes(self):
        """Returns a set of the installed package nodes.

        The set doesn't include package nodes that have been marked deleted.
        """
        return {node for node in self.__package_nodes.values()
                if not node.deleted}

    @property
    def dependency_edges(self):
        """Returns a set of the dependency edges.

        The set doesn't include dependency edges that have been marked deleted.
        """
        return {edge for edge in self.__dependency_edges.values()
                if not edge.deleted}

    @property
    def target_edges(self):
        """Returns a set of the target edges in the graph.

        The set doesn't include target edges that have been marked deleted.
        """
        return {edge for edge in self.__target_edges.values()
                if not edge.deleted}
