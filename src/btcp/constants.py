# Connections
CLIENT_IP = 'localhost'
CLIENT_PORT = 20000
SERVER_IP = 'localhost'
SERVER_PORT = 30000

# Sizes
HEADER_SIZE = 10
PAYLOAD_SIZE = 1008
SEGMENT_SIZE = HEADER_SIZE + PAYLOAD_SIZE

# Communication
MAX_ATTEMPTS = 3
HEADER_TYPES = ['seq_nr', 'ack_nr', 'flag', 'window', 'data_len', 'checksum', 'data']
BUFFER_SIZE = 5