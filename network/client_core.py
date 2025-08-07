# External Imports
import socket

# Internal Imports
from network.protocol import send_obj, recv_obj

# Allow for connecting to the server
def connect_to_server(host: str, port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock

# Ensure all connections are safe for sending and recieving
def safe_send(conn, obj):
    send_obj(conn, obj)

def safe_recv(conn):
    return recv_obj(conn)