# External Imports
import pickle

MESSAGE_PREFIX = b"ROR"

# Convert a Python object to bytes and prepend the protocol prefix.
def serialize_message(obj) -> bytes:
    data = pickle.dumps(obj)
    return MESSAGE_PREFIX + data

# Verify the prefix, then reconstruct the original object from bytes.
def deserialize_message(raw: bytes):
    if not raw.startswith(MESSAGE_PREFIX):
        raise ValueError('Invalid message prefix')
    return pickle.loads(raw[len(MESSAGE_PREFIX):])

# Serialize an object and send it with a 4-byte length header.
def send_obj(conn, obj):
    msg = serialize_message(obj)
    conn.sendall(len(msg).to_bytes(4, 'big') + msg)

# Read the length header, receive the exact payload, then deserialize it.
def recv_obj(conn):
    length_data = conn.recv(4)
    length = int.from_bytes(length_data, 'big')
    raw = conn.recv(length)
    return deserialize_message(raw)