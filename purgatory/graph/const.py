"""Graph-specific constants.

Currently this only contains epsilon which is a sufficiently small epsilon to
compare edge probabilities.  Note that this is not the machine epsilon
(sys.float_info.epsilon) as rounding errors can easily exceed the machine
epsilon.  Unfortunately this constant is needed as Python's fraction
implementation (rational number arithmetic) is too slow.
"""


EPSILON = 0.00001
