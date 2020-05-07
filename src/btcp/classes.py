from btcp.enums import Flag


class Payload:
    """ Object that represents the segment with its meta data """

    def __init__(self, identifier, data, sent=False, is_acked=False, timer=0, start_time=0):
        self.id = identifier
        self.sent = sent
        self.is_acked = is_acked
        self.timer = timer
        self.start_time = start_time
        self.data = data


class Segment:
    """ Object that represents the received segment, usually called message """

    def __init__(self, unpacked: dict):
        self.seq_nr = unpacked['seq_nr']
        self.ack_nr = unpacked['ack_nr']
        self.flag = Flag(unpacked['flag'])
        self.win = unpacked['win']
        self.dlen = unpacked['dlen']
        self.cksum = unpacked['cksum']
        self.data = unpacked['data']
        self.address = None


class BadState(Exception):
    """ Custom exception used in function guards when the function call happened with the wrong state """
    pass


class WrongFlag(Exception):
    """ Custom exception used in function guards when the input message is of the wrong type """
    pass
