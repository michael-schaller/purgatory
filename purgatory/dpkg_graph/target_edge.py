"""A target edge between an installed dependency and package node."""


from .. import graph


class TargetEdge(graph.OrEdge):
    """A target edge between a target versions node and package node."""

    def __init__(self, from_node, to_node):
        """TargetEdge constructor.

        Args:
            from_node: TargetVersionsNode object.
            to_node:  PackageNode object.
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
        if abs(probability - 1.0) < graph.EPSILON:
            return "%s --> %s" % (
                self.from_node, self.to_node)
        else:
            return "%s --p=%.3f--> %s" % (
                self.from_node, probability, self.to_node)

    @property
    def graphviz_attributes(self):
        """Returns the attributes dict for the respective GraphViz member."""
        attrs = {
            "arrowsize": 0.8,  # Compensate for the penwidth.
            "label": "",
            "penwidth": 2.5,
            "tooltip": str(self),
        }
        if self.probability < 1.0:  # pragma: no cover
            attrs["style"] = "dashed"
        return attrs
