class Segment:
    """ Object that represents the segment with its meta data """

    def __init__(self, data, sent=False, seq_nr=None, exp_ack=None, is_acked=False, timer=0, start_time=0):
        self.sent = sent
        self.seq_nr = seq_nr
        self.exp_ack = exp_ack
        self.is_acked = is_acked
        self.timer = timer
        self.start_time = start_time
        self.data = data
