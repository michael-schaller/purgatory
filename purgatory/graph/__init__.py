"""A hierarchical Graph with nodes and directed edges that have probabilities.

The Graph implementation in this module is designed for hierarchical Graphs.
The Graph can have cycles and can be disconnected.  The hierarchy is modeled
after a wodden tree with relatively many leaf nodes on the top and relatively
few leaf nodes on the bottom.

A hierarchical Graph consists of Nodes and directed Edges that have
probabilities.  An edge of type Edge has always the probability 1.0 and
represents a mandatory edge.  Furthermore edges can also be in an
or-relationship if they are of type OrEdge.  Any of the edges in an
or-relationship satisfy the hierarchie but it is not important which one.
Edges of type OrEdge have a probability depending on how many edges are in the
or-relationship.  For more details see the docstring of the OrEdge type.

A Graph's set of Nodes and Edges can't be changed after initialization.
However Nodes and Edges can be marked as deleted.  Every Graph member that is
marked as deleted will be ignored by algorithms but be warned that some
algorithms reset the deleted markers.  Whenever the deleted markers are changed
there will be a note in the respective docstring.

As a Graph is hierarchical the mark_deleted methods on Nodes and Edges behave
differently than with classical/generic Graph implementations.  Marking a Node
as deleted also marks its incoming and outgoing edges as deleted as edges can't
exist without their nodes existing.  Marking an Edge as deleted typically marks
everything above the from-node of the Edge as deleted as the Nodes and Edges
can't exist anymore without their foundation.  The only exception to this rule
is made if the hierarchie isn't violated due to edges in an or-relationship.

Cycles in the Graph are always treated as an undividable cluster of nodes.
For an instance Graph.leafs returns the leaf nodes and the nodes within
leaf cycles.  Marking a cycle as deleted will also mark all nodes and edges of
the cycle as deleted as long as there is no alternative (parallel OrEdge).

The classes in this module are very thightly tied together and protected access
between classes in this module is generally allowed and partly necessary to
speed up extremely hot code paths.  If this code would be written in C++ these
classes would be in a 'friend' relationship.
"""


# Ignore all flake8 issues because F401 issues (unused imports) can't be
# silenced otherwise.
# flake8: noqa

# Silence unused import warnings.
# pylint: disable=unused-import


# Graph-specific exceptions.
from .error import DeletedMemberInUseError
from .error import EdgeWithZeroProbabilityError
from .error import GraphError
from .error import MemberAlreadyRegisteredError
from .error import NodeIsNotPartOfEdgeError
from .error import NotANodeError
from .error import NotAnEdgeError
from .error import NotAnOrEdgeError
from .error import NotMemberOfGraphError
from .error import UnregisteredMemberInUseError


# Graph-specific constants.
from .const import EPSILON


# Graph-specific abstract base classes.
from .edge import Edge
from .graph import Graph
from .member import Member
from .node import Node
from .or_edge import OrEdge
