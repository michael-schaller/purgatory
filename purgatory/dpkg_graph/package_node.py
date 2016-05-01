"""A graph node that represents an installed package."""


from . import error

from .. import graph


class PackageNode(graph.Node):
    """A graph node that represents an installed package.

    The PackageNode is a simplification of the graph as it merges package and
    version information into one node.  This is possible because only one
    version (or none) of a package can be installed.
    """

    def __init__(self, pkg):
        """PackageNode constructor.

        Args:
            pkg: apt.package.Package object.
        """
        # Check
        if not pkg.is_installed:
            raise error.PackageIsNotInstalledError(pkg)

        # Private
        self.__pkg = pkg
        self.__ver = pkg.installed

        # Init
        super().__init__(PackageNode.pkg_to_uid(pkg))

    @staticmethod
    def pkg_to_uid(pkg):
        """Returns the uid for an apt.package.Package object."""
        return str(pkg)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self.uid

    @property
    def graphviz_attributes(self):
        """Returns the attributes dict for the respective GraphViz member."""
        return {
            "label": "Package:\n%s" % self.uid,
            "penwidth": 2.5,
            "shape": "rectangle",
            "tooltip": "Package: %s" % self.uid,
        }

    @property
    def package(self):
        """Returns the apt.package.Package object for this node."""
        return self.__pkg

    @property
    def version(self):
        """Returns the apt.package.Version object for this node."""
        return self.__ver
