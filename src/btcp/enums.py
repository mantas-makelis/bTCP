from enum import Enum, unique


@unique
class Flag(Enum):
    """ Different flags for bTCP header """
    NONE = 0
    ACK = 1
    SYN = 2
    SYNACK = 3
    FIN = 4
    FINACK = 5


@unique
class State(Enum):
    """ States of a bTCP socket """
    OPEN = 0
    CONN_EST = 1
