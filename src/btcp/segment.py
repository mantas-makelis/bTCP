class Segment:
    def __init__(self,
     sent=False, 
     seq=None, 
     exp_ack=None, 
     is_ack=False, 
     timer=0, 
     start_time=0, 
     packed=None):
        self.sent = sent
        self.seq = seq
        self.exp_ack = exp_ack
        self.is_ack = is_ack
        self.timer = timer 
        self.start_time = start_time
        self.packed = packed


        