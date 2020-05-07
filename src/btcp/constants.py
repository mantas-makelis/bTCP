# Connections
CLIENT_IP = 'localhost'
CLIENT_PORT = 20000
SERVER_IP = 'localhost'
SERVER_PORT = 30000

# Sizes
HEADER_SIZE = 10
PAYLOAD_SIZE = 1008
SEGMENT_SIZE = HEADER_SIZE + PAYLOAD_SIZE
TWO_BYTES = 2 ** 16

# Communication
HEADER_FORMAT = '!HHbbHH'
DATA_FORMAT = f'{PAYLOAD_SIZE}s'
MAX_ATTEMPTS = 10
SEGMENT_KEYS = ['seq_nr', 'ack_nr', 'flag', 'win', 'dlen', 'cksum', 'data']
BUFFER_SIZE = 5
FIN_TIMEOUT = 3000
