"""A graph node that represents an installed dependency."""


from . import error

from .. import graph


class TargetVersionsNode(graph.Node):
    """A node that represents the target versions that fulfills depencencies.

    In the resulting graph target version nodes are collapsed/reused as much as
    possible.  Because of this a target versions node is solely defined by the
    target versions that at least one dependency resolves to. This means
    especially that a target versions node doesn't belong to a specific package
    node or a specific dependency of a package node. In the end several
    dependency edges point to the same target versions node as long as a
    dependency is resolved by the same set of target versions a target versions
    node represents.
    """

    def __init__(self, dep):
        """PackageNode constructor.

        Args:
            dep: apt.package.Dependency object.
        """
        # Private
        self.__itvers = frozenset(dep.installed_target_versions)

        # Check
        if not self.__itvers:
            raise error.DependencyIsNotInstalledError(dep)

        # Init
        # Generate uid as decribed in the TargetVersionsNode docstring.
        itpkgs_str_set = {str(ver.package) for ver in self.__itvers}
        itpkgs_str_list = list(itpkgs_str_set)
        itpkgs_str_list.sort()
        uid = "<" + "|".join(itpkgs_str_list) + ">"
        super().__init__(uid)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self._uid

    @property
    def graphviz_attributes(self):
        """Returns the attributes dict for the respective GraphViz member."""
        itpkgs_str_set = {str(ver.package) for ver in self.__itvers}
        itpkgs_str_list = list(itpkgs_str_set)
        itpkgs_str_list.sort()

        attrs = {
            "label": "Possible targets:\n%s" % "\n".join(itpkgs_str_list),
            "penwidth": 2.5,
            "shape": "rectangle",
            "style": "rounded",
            "tooltip": "Possible targets: %s" % self.uid,
        }
        return attrs

    @property
    def installed_target_versions(self):
        """Returns the set of installed target apt.package.Version objects."""
        return self.__itvers
