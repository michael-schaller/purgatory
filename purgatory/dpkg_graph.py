"""Graph representing installed packages in the dpkg status database.

The DpkgGraph is a massively simplified graph compared to a full Apt graph.  It
only contains what is relevant for Purgatory.

Simplifications:
* Only the dpkg status database instead of the complete Apt database.
* Only installed packages. This allows to collapse a respective Package and
  Version object into a single InstalledPackageNode.
* Only PreDepends, Depends and Recommends dependency types.  The dependency are
  collapsed as much as possible.
* Only installed target versions and their respective packages.
"""

import errno
import logging
import os
import types

import purgatory.error
import purgatory.graph

import purgatory.mppa
import apt_pkg  # Always needs to be imported after purgatory.mppa.
import apt      # Always needs to be imported after purgatory.mppa.


class DpkgGraphError(purgatory.error.PurgatoryError):
    """Base class for all dpkg graph related errors."""


class EmptyAptCacheError(DpkgGraphError):
    """Raised if the Apt cache doesn't contain installed packages."""

    def __init__(self):
        msg = "The Apt cache doesn't contain any installed packages!"
        super().__init__(msg)


class PackageIsNotInstalledError(DpkgGraphError):
    """Raised if a package that is expected to be installed isn't."""

    def __init__(self, pkg):  # pragma: no cover
        msg = ("The package '%s' was expected to be installed but it "
               "currently isn't installed!") % (pkg)
        super().__init__(msg)


class DependencyIsNotInstalledError(DpkgGraphError):
    """Raised if a dependency that is expected to be installed isn't."""

    def __init__(self, dep):
        msg = ("The dependency '%s' was expected to be installed but it "
               "currently isn't installed!") % (dep)
        super().__init__(msg)


class UnsupportedDependencyTypeError(DpkgGraphError):
    """Raised if a dependency has an unsupported type."""

    def __init__(self, dep):  # pragma: no cover
        msg = ("The dependency '%s' has the unsupported type '%s'!") % (
            dep.rawstr, dep.rawtype)
        super().__init__(msg)


class DpkgGraph(purgatory.graph.Graph):
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
        self.__installed_package_nodes = {}  # uid:node
        self.__installed_dependency_nodes = {}  # uid:node
        self.__dependency_edges = {}  # uid:edge
        self.__target_edges = {}  # uid:edge

        # Protected
        self._ignore_recommends = ignore_recommends

        # Init
        self.__init_cache()
        super().__init__()  # Calls _init_nodes and _init_edges.

        # Log
        logging.debug("dpkg graph contains:")
        logging.debug("  Installed package nodes: %d",
                      len(self.__installed_package_nodes))
        logging.debug("  Installed dependency nodes: %d",
                      len(self.__installed_dependency_nodes))
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
        else:  # pragma: no cover
            conf["Dir::State::status"] = dpkg_db
        self.__dpkg_db = conf["Dir::State::status"]
        logging.debug("dpkg status database: %s", self.__dpkg_db)

        # As Purgatory uses a special configuration the Apt cache will be
        # built in a temporary directory so that the valid cache on disk for
        # the full configuration isn't overwritten.
        purgatory_tmpdir = "/tmp/.purgatory"
        try:
            os.mkdir(purgatory_tmpdir)
        except OSError as ex:  # pragma: no cover
            if ex.errno != errno.EEXIST:
                raise
        os.chmod(purgatory_tmpdir, 0o777)  # Writable for all users
        tmp_pkgcache_prefix = self.__dpkg_db.replace("/", "_").strip("_")
        tmp_pkgcache = os.path.join(
            purgatory_tmpdir, tmp_pkgcache_prefix + "_pkgcache.bin")
        tmp_srcpkgcache = os.path.join(
            purgatory_tmpdir, tmp_pkgcache_prefix + "_srcpkgcache.bin")
        conf["Dir::Cache::pkgcache"] = tmp_pkgcache
        conf["Dir::Cache::srcpkgcache"] = tmp_srcpkgcache

        # Initialize Apt with the given config.
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
            raise EmptyAptCacheError()
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
            ipn = InstalledPackageNode(pkg)
            self._add_node(ipn)
            self.__installed_package_nodes[ipn.uid] = ipn

            # Add installed dependency nodes and dependency edges
            if self._ignore_recommends:
                deps = ipn.version.get_dependencies("PreDepends", "Depends")
            else:
                deps = ipn.version.get_dependencies(
                    "PreDepends", "Depends", "Recommends")
            for dep in deps:  # apt.package.Dependency
                # Add installed dependency node.
                try:
                    idn = InstalledDependencyNode(dep)
                except DependencyIsNotInstalledError:
                    if dep.rawtype == "Recommends":
                        # Recommended packages don't need to be installed.
                        continue
                idn, dup = self._add_node_dedup(idn)
                if not dup:
                    self.__installed_dependency_nodes[idn.uid] = idn

                # Add dependency edge from the installed package node to the
                # installed dependency node.
                de = DependencyEdge(ipn, idn)
                self._add_edge(de)
                self.__dependency_edges[de.uid] = de

        # Freeze all dicts that have been filled so far.
        self.__installed_package_nodes = types.MappingProxyType(
            self.__installed_package_nodes)
        self.__installed_dependency_nodes = types.MappingProxyType(
            self.__installed_dependency_nodes)
        self.__dependency_edges = types.MappingProxyType(
            self.__dependency_edges)

    def __init_nodes_and_edges_phase2(self):
        """Phase 1 of the initialization of the dpkg graph.

        Phase 2 of the initialization adds the following to the graph:
        * Target edges (between installed dependency nodes and packages nodes)
        """
        for idn in self.__installed_dependency_nodes.values():
            # Add target edges from the installed dependency node to the
            # installed package node.
            for itver in idn.installed_target_versions:
                itpkg = itver.package
                itpkg_uid = InstalledPackageNode.pkg_to_uid(itpkg)
                itpn = self.__installed_package_nodes[itpkg_uid]

                te = TargetEdge(idn, itpn)
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
    def installed_dependency_nodes(self):
        """Returns a dict view (uid:node) of the installed dependency nodes.

        The dict view is unfiltered and thus contains deleted nodes.
        """
        return self.__installed_dependency_nodes

    @property
    def installed_package_nodes(self):
        """Returns a dict view (uid:node) of the installed package nodes.

        The dict view is unfiltered and thus contains deleted nodes.
        """
        return self.__installed_package_nodes

    @property
    def dependency_edges(self):
        """Returns a dict view (uid:node) of the dependency edges.

        The dict view is unfiltered and thus contains deleted edges.
        """
        return self.__dependency_edges

    @property
    def target_edges(self):
        """Returns a dict view (uid:node) of the target edges in the graph.

        The dict view is unfiltered and thus contains deleted edges.
        """
        return self.__target_edges


class InstalledPackageNode(purgatory.graph.Node):
    """A graph node that represents an installed package.

    The InstalledPackageNode is a simplification of the graph as it merges
    package and version information into one node. This is possible because
    only one version (or none) of a package can be installed.
    """

    def __init__(self, pkg):
        """InstalledPackageNode constructor.

        Args:
            pkg: apt.package.Package object.
        """
        # Check
        if not pkg.is_installed:  # pragma: no cover
            raise PackageIsNotInstalledError(pkg)

        # Private
        self.__pkg = pkg
        self.__ver = pkg.installed

        # Init
        super().__init__(InstalledPackageNode.pkg_to_uid(pkg))

    @staticmethod
    def pkg_to_uid(pkg):
        """Returns the uid for an apt.package.Package object."""
        return str(pkg)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self.uid

    @property
    def package(self):
        """Returns the apt.package.Package object for this node."""
        return self.__pkg

    @property
    def version(self):
        """Returns the apt.package.Version object for this node."""
        return self.__ver


class InstalledDependencyNode(purgatory.graph.Node):
    """A graph node that represents an installed dependency.

    In the resulting graph installed dependency nodes are collapsed/reused as
    much as possible.  Because of this a dependency node doesn't belong to a
    specific installed package node but rather is defined by its rawstr and its
    installed target package nodes.  The rawtype of an installed dependency
    will be reflected by the edge between an installed package node and an
    installed dependency node.
    """

    def __init__(self, dep):
        """InstalledPackageNode constructor.

        Args:
            dep: apt.package.Dependency object.
        """
        # Private
        self.__dep = dep
        self.__dep_rawstr = dep.rawstr
        self.__itvers = frozenset(dep.installed_target_versions)

        # Check
        if not self.__itvers:
            raise DependencyIsNotInstalledError(dep)

        # Init
        uid = "%s --> %s" % (self.__dep_rawstr, self.__itvers)
        super().__init__(uid)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = "%s: %s" % (self.__dep.rawtype, self.__dep_rawstr)

    @property
    def dependency(self):
        """Returns the apt.package.Dependency object for this node."""
        return self.__dep

    @property
    def installed_target_versions(self):
        """Returns the set of installed target apt.package.Version objects."""
        return self.__itvers


class DependencyEdge(purgatory.graph.Edge):
    """A dependency edge between an installed package and dependency node.

    Please note that the probability of a dependency edge is always 1.0.

    PreDepends and Depends dependency types are hard dependencies and there
    is always only one InstalledDependencyNode which can fulfill a
    dependency - hence the static probability of 1.0.

    Recommends dependency types are optional dependencies.  There would be
    no DepedencyEdge if the corresponding package or dependency wouldn't be
    installed.  There is again only one InstalledDependencyNode which can
    fulfill a recommends dependency - hence the probability of 1.0.
    """

    def __init__(self, from_node, to_node):
        """DependencyEdge constructor.

        Args:
            from_node: InstalledPackageNode object.
            to_node: InstalledDependencyNode object.
        """
        # Check
        # If this check is changed to support more dependency types the
        # probability property needs to be checked if it is still correct.
        if to_node.dependency.rawtype not in [
                "PreDepends", "Depends", "Recommends"]:  # pragma: no cover
            raise UnsupportedDependencyTypeError(to_node.dependency)

        # Init
        super().__init__(from_node, to_node)

    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""
        dep = to_node.dependency
        return "%s --%s--> %s" % (from_node.uid, dep.rawtype, dep.rawstr)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self.uid


class TargetEdge(purgatory.graph.OrEdge):
    """A target edge between an installed dependency and package node."""

    def __init__(self, from_node, to_node):
        """TargetEdge constructor.

        Args:
            from_node: InstalledDependencyNode object.
            to_node:  InstalledPackageNode object.
        """
        super().__init__(from_node, to_node)

    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""
        return "%s --> %s" % (from_node.uid, to_node.uid)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        pass  # TargetEdge implements its own __str__ method

    def __str__(self):
        probability = self.probability
        if abs(probability - 1.0) < purgatory.graph.EPSILON:
            return "%s --> %s" % (
                self.from_node, self.to_node)
        else:
            return "%s --p=%.3f--> %s" % (
                self.from_node, probability, self.to_node)
