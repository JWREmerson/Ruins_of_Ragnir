# External Imports
import sys
import os
import logging
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Internal imports
from config import SERVER_HOST, SERVER_PORT
from network.server_core import start_server, accept_clients
from network.protocol import send_obj
from utils import setup_logging
from game.init import initialize_game
from game.phases import ExplorePhase


# Set up the initial 6×5 board so clients render immediately.
def setup_initial_board(state):
    state.rows, state.cols = 6, 5

    ruins_proxy = SimpleNamespace(
        card_type="Ruin",
        name="Hidden Ruin",
        terrain="Ruins",
        ability="",
        connections=[],
    )

    slot_proxy = SimpleNamespace(
        card_type="GateSlot",
        name="Starting Slot",
        terrain="Gate",
        ability="",
        connections=[],
    )

    state.map = {}
    for r in range(state.rows):
        for c in range(state.cols):
            state.map[(r, c)] = {"card": ruins_proxy, "face_up": False}

    mid = state.cols // 2
    state.map[(1, mid)] = {"card": slot_proxy, "face_up": True}
    state.map[(4, mid)] = {"card": slot_proxy, "face_up": True}

    state.gate_positions = {}


# Main server loop.
def main():
    setup_logging()
    logger = logging.getLogger("Server")

    # Listen and accept two clients.
    server_sock = start_server(SERVER_HOST, SERVER_PORT)
    logger.info("Server listening on %s:%d", SERVER_HOST, SERVER_PORT)
    conn1, conn2 = accept_clients(server_sock)
    logger.info("Two clients connected: %s, %s", conn1.getpeername(), conn2.getpeername())

    # Build game state from deck choices and deal starting hands.
    state, _ = initialize_game(conn1, conn2)
    state.deal_starting_hands()

    # Seed the blank board.
    setup_initial_board(state)

    # Repeat Explore turns until a valid path connects Gates.
    while True:
        update = {"type": "state_update", "state": state}
        send_obj(conn1, update)
        send_obj(conn2, update)

        ExplorePhase(state, (conn1, conn2)).run()

        if state.check_path_between_gates():
            winner = state.current_player()
            end_msg = {"type": "game_end", "winner": winner, "phase": "explore"}
            send_obj(conn1, end_msg)
            send_obj(conn2, end_msg)
            break

    conn1.close()
    conn2.close()


if __name__ == "__main__":
    main()
