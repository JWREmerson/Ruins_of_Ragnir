# Internal imports
from resources.loader import (
    load_heroes, load_gates,
    load_ruins, load_minions,
    load_gears, load_spells,
    load_relics, load_glyphs
)
from network.protocol import send_obj, recv_obj
from game.state import GameState, PlayerState

# Initialize_game sets up the GameState and PlayerStates based on client choices
def initialize_game(conn1, conn2):
    # Load all card data
    heroes = load_heroes()
    gates = load_gates()
    ruins = load_ruins()
    minions = load_minions()
    gears = load_gears()
    spells = load_spells()
    relics = load_relics()
    glyphs = load_glyphs()

    # Send deck options to both clients
    deck_options = {'heroes': heroes, 'gates': gates}
    send_obj(conn1, deck_options)
    send_obj(conn2, deck_options)

    # Receive each client's deck choice
    choice1 = recv_obj(conn1)['deck_choice']
    choice2 = recv_obj(conn2)['deck_choice']

    # Construct PlayerState for each player
    p1_state = PlayerState(
        hero=choice1['hero'],
        gate=choice1['gate'],
        ruins=ruins,
        minions=minions,
        gears=gears,
        spells=spells,
        relics=relics,
        glyphs=glyphs
    )

    p2_state = PlayerState(
        hero=choice2['hero'],
        gate=choice2['gate'],
        ruins=ruins,
        minions=minions,
        gears=gears,
        spells=spells,
        relics=relics,
        glyphs=glyphs
    )

    # Create shared GameState
    state = GameState(p1_state, p2_state)

    return state, (p1_state, p2_state)