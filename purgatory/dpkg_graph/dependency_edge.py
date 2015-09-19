"""A dependency edge between an installed package and dependency node."""


from . import error

from .. import graph


class DependencyEdge(graph.Edge):
    """A dependency edge between an installed package and dependency node.

    Please note that the probability of a dependency edge is always 1.0.

    PreDepends and Depends dependency types are hard dependencies and there
    is always only one DependencyNode which can fulfill a dependency - hence
    the static probability of 1.0.

    Recommends dependency types are optional dependencies.  There would be
    no DepedencyEdge if the corresponding package or dependency wouldn't be
    installed.  There is again only one DependencyNode which can fulfill a
    recommends dependency - hence the probability of 1.0.
    """

    def __init__(self, from_node, to_node):
        """DependencyEdge constructor.

        Args:
            from_node: PackageNode object.
            to_node: DependencyNode object.
        """
        # Check
        # If this check is changed to support more dependency types the
        # probability property needs to be checked if it is still correct.
        if to_node.dependency.rawtype not in [
                "PreDepends", "Depends", "Recommends"]:
            raise error.UnsupportedDependencyTypeError(to_node.dependency)

        # Init
        super().__init__(from_node, to_node)

    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""
        dep = to_node.dependency
        return "%s --%s--> %s" % (from_node.uid, dep.rawtype, dep.rawstr)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self.uid
