"""A graph node that represents an installed dependency."""


from . import error

from .. import graph


class DependencyNode(graph.Node):
    """A graph node that represents an installed dependency.

    In the resulting graph installed dependency nodes are collapsed/reused as
    much as possible.  Because of this a dependency node doesn't belong to a
    specific installed package node but rather is defined by its rawstr and its
    installed target package nodes.  The rawtype of an installed dependency
    will be reflected by the edge between an installed package node and an
    installed dependency node.
    """

    def __init__(self, dep):
        """PackageNode constructor.

        Args:
            dep: apt.package.Dependency object.
        """
        # Private
        self.__dep = dep
        self.__dep_rawstr = dep.rawstr
        self.__itvers = frozenset(dep.installed_target_versions)

        # Check
        if not self.__itvers:
            raise error.DependencyIsNotInstalledError(dep)

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
