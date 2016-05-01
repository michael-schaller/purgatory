"""A dependency edge between an installed package and dependency node."""


from . import error

from .. import graph


class DependencyEdge(graph.Edge):
    """A dependency edge between a package and target versions node.

    Please note that the probability of a dependency edge is always 1.0.

    PreDepends and Depends dependency types are hard dependencies and there
    is always only one TargetVersionsNode which can fulfill a dependency, hence
    the static probability of 1.0.

    Recommends dependency types are optional dependencies.  There would be
    no DepedencyEdge if the corresponding package or dependency wouldn't be
    installed.  There is again only one TargetVersionsNode which can fulfill a
    recommends dependency, hence the static probability of 1.0.
    """

    def __init__(self, from_node, to_node, dep):
        """DependencyEdge constructor.

        Args:
            from_node: PackageNode object.
            to_node: TargetVersionsNode object.
        """
        # Private
        self.__dep = dep

        # Check
        # If this check is changed to support more dependency types the
        # probability property needs to be checked if it is still correct.
        if dep.rawtype not in [
                "PreDepends", "Depends", "Recommends"]:
            raise error.UnsupportedDependencyTypeError(dep)

        # Init
        super().__init__(from_node, to_node)

    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""
        dep = self.__dep  # Initialized by the DependencyEdge constructur.
        return "%s --%s--> %s" % (from_node.uid, dep.rawtype, dep.rawstr)

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = self.uid

    @property
    def graphviz_attributes(self):
        """Returns the attributes dict for the respective GraphViz member."""
        dep = self.__dep
        attrs = {
            "arrowsize": 0.8,  # Compensate for the penwidth.
            "label": "",
            "penwidth": 2.5,
            "tooltip": "%s: %s" % (dep.rawtype, dep.rawstr),
        }
        if dep.rawtype == "Recommends":
            attrs["style"] = "dashed"
        return attrs
