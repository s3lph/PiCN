"""Internal representation of an interest packet"""

from .Packet import Packet

class Interest(Packet):
    """
    Internal representation of an interest packet
    """

    def __init__(self, name = None, wire_data = None):
        Packet.__init__(self, name)
        self._wire_data = wire_data
        assert (type(self._wire_format) in [bytes, bytearray, type(None)]), "MUST be raw bytes or None"

    def __eq__(self, other):
        if type(other) is not Interest:
            return False
        return self.name == other.name