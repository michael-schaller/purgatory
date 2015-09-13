"""Graph-specific exceptions."""


import purgatory.error


class GraphError(purgatory.error.PurgatoryError):
    """Base class for all graph related errors."""


class DeletedMemberInUseError(GraphError):
    """Raised if a deleted member is in use."""

    def __init__(self, member):
        msg = "Deleted member '%s' with uid '%s' is in use!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class EdgeWithZeroProbabilityError(GraphError):
    """Raised if an edge has the probability of 0.0."""

    def __init__(self, edge):
        msg = ("The edge '%s' has a probability of 0.0 and isn't of any use "
               "to the Graph!") % (edge)
        super().__init__(msg)


class MemberAlreadyRegisteredError(GraphError):
    """Raised if a member has been already registered in the graph."""

    def __init__(self, member):
        msg = "Member '%s' with uid '%s' has been already registered!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class NodeIsNotPartOfEdgeError(GraphError):
    """Raised if a node isn't part of an edge but should be."""
    def __init__(self, node, edge):
        msg = "Node '%s' isn't part of edge '%s' but should be!" % (
            node, edge)
        super().__init__(msg)


class NotANodeError(GraphError):
    """Raised if a node was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'Node' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class NotAnEdgeError(GraphError):
    """Raised if an edge was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'Edge' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class NotAnOrEdgeError(GraphError):
    """Raised if an or-edge was expected but something else was given."""

    def __init__(self, something):
        msg = "Expected an instance of class 'OrEdge' but got class '%s'!" % (
            something.__class__)
        super().__init__(msg)


class NotMemberOfGraphError(GraphError):
    """Raised if a member in use doesn't belong to this graph."""

    def __init__(self, member):
        msg = "Member '%s' with uid '%s' doesn't belong to this graph!" % (
            member.__class__, member.uid)
        super().__init__(msg)


class UnregisteredMemberInUseError(GraphError):
    """Raised if an unregistered member is in use."""

    def __init__(self, member):
        msg = "Unregistered member '%s' with uid '%s' is in use!" % (
            member.__class__, member.uid)
        super().__init__(msg)
