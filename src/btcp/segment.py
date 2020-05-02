class Segment:
    """ Object that represents the segment with its meta data """

    def __init__(self, sent=False, seq=None, exp_ack=None, is_acked=False, timer=0, start_time=0, data=None):
        self.sent = sent
        self.seq = seq
        self.exp_ack = exp_ack
        self.is_acked = is_acked
        self.timer = timer
        self.start_time = start_time
        self.data = data
