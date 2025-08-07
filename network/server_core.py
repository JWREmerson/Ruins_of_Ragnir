# External Imports
import socket
from typing import Tuple

# Function to bring the server side up in server.py
def start_server(host: str, port: int) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(2)
    return srv

# Function that allows clients to connect to the server
def accept_clients(srv: socket.socket) -> Tuple[socket.socket, socket.socket]:
    conn1, _ = srv.accept()
    conn2, _ = srv.accept()
    return conn1, conn2