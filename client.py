# External Imports
import sys
import os
import pygame

# Allow running from this folder by putting parent on the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Internal imports
from network.client_core import connect_to_server, safe_send, safe_recv
from ui.deck_selection import choose_deck
from utils import setup_logging
from ui.display import render_state

# Override the bind-all host so clients connect to localhost on Windows
from config import SERVER_PORT
SERVER_HOST = "127.0.0.1"

def main():
    setup_logging()

    # Connect to the locally-bound server
    sock = connect_to_server(SERVER_HOST, SERVER_PORT)

    # Deck selection
    deck_options = safe_recv(sock)
    choice = choose_deck(deck_options)
    safe_send(sock, {'deck_choice': choice})

    # Enter main game loop
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    player_id = None
    running = True

    while running:
        data = safe_recv(sock)
        if not data:
            continue

        # Full-state updates: redraw board
        if data.get('type') == 'state_update':
            state = data['state']
            # Assign and filter by player_id
            if 'player' in data:
                if player_id is None:
                    player_id = data['player']
                if data['player'] != player_id:
                    continue
            render_state(screen, state)
            pygame.display.flip()

        # Game end notification
        elif data.get('type') == 'game_end':
            winner = data.get('winner')
            phase = data.get('phase')
            print(f"Game over! Winner: {winner} (Phase: {phase})")
            running = False

        # Phase‐specific prompts
        elif 'phase' in data:
            phase = data['phase']
            step = data.get('step')

            if phase == 'explore' and step == 'placement':
                choice_msg = {}
                state_obj = data.get('state')
                if state_obj:
                    if player_id == "Player1" and state_obj.players[0].hand:
                        choice_msg = {
                            "card_index": 0,
                            "pos": (state_obj.rows - 2, state_obj.cols // 2)
                        }
                    elif player_id == "Player2" and state_obj.players[1].hand:
                        choice_msg = {
                            "card_index": 0,
                            "pos": (1, state_obj.cols // 2)
                        }
                if not choice_msg:
                    choice_msg = {"pass": True}
                safe_send(sock, choice_msg)

            # Adventure Phase: summoning step
            elif phase == 'adventure' and step == 'summoning' and state_obj:
                summon_msg = {}
                ps = state_obj.players[0] if player_id == "Player1" else state_obj.players[1]
                for idx, card in enumerate(ps.hand):
                    cost = getattr(card, "cost", 0)
                    if ps.echoes >= cost:
                        summon_msg = {"card_index": idx}
                        break
                safe_send(sock, summon_msg)

            # Adventure Phase: movement step
            elif phase == 'adventure' and step == 'movement' and state_obj:
                move_msg = {"moves": []}
                hero = state_obj.board[player_id]["hero"]
                hero_pos = None
                for pos, occ in state_obj.occupants.items():
                    for owner, unit in occ:
                        if owner == player_id and unit is hero:
                            hero_pos = pos
                            break
                    if hero_pos:
                        break
                if hero_pos:
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        tgt = (hero_pos[0] + dr, hero_pos[1] + dc)
                        if tgt in state_obj.map:
                            move_msg["moves"].append({"from": hero_pos, "to": tgt})
                            break
                safe_send(sock, move_msg)

            # Adventure Phase: combat step
            elif phase == 'adventure' and step == 'combat' and state_obj:
                combat_msg = {"attacks": []}
                hero = state_obj.board[player_id]["hero"]
                hero_pos = None
                for pos, occ in state_obj.occupants.items():
                    for owner, unit in occ:
                        if owner == player_id and unit is hero:
                            hero_pos = pos
                            break
                    if hero_pos:
                        break
                if hero_pos:
                    for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                        neigh = (hero_pos[0] + dr, hero_pos[1] + dc)
                        if neigh in state_obj.occupants:
                            for owner, unit in state_obj.occupants[neigh]:
                                if owner != player_id:
                                    combat_msg["attacks"].append({"from": hero_pos, "to": neigh})
                                    break
                            if combat_msg["attacks"]:
                                break
                safe_send(sock, combat_msg)

        # Allow window close
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()
    input("Press Enter to close window…")

if __name__ == '__main__':
    main()