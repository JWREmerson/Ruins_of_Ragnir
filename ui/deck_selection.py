# External Imports
import pygame

# Internal Imports
from ui.display import render_text

def choose_deck(deck_options) -> dict:
    """
    deck_options is the dict sent by the server, with keys 'heroes' and 'gates'
    """
    heroes = deck_options['heroes']
    gates = deck_options['gates']
    decks = list(zip(heroes, gates))
    if len(decks) > 4:
        decks = decks[:4]

    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    choice = None

    width, height = screen.get_size()
    box_w, box_h = width // 2, height // 2
    positions = [(0, 0), (box_w, 0), (0, box_h), (box_w, box_h)]

    while choice is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return decks[0]
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                for i, (x, y) in enumerate(positions):
                    if x <= mx < x + box_w and y <= my < y + box_h:
                        hero_card, gate_card = decks[i]
                        choice = {"hero": hero_card, "gate": gate_card}
                        break

        # Draw the four deck options
        screen.fill((0, 0, 0))
        for i, (hero_card, gate_card) in enumerate(decks):
            x, y = positions[i]
            pygame.draw.rect(screen, (100, 100, 100),
                             (x + 10, y + 10, box_w - 20, box_h - 20), 2)
            hero_name = getattr(hero_card, "name", "Hero")
            gate_name = getattr(gate_card, "name", "Gate")
            render_text(screen, f"Hero: {hero_name}", (x + 20, y + 30), font_size=24)
            render_text(screen, f"Gate: {gate_name}", (x + 20, y + 60), font_size=24)

        pygame.display.flip()

    pygame.quit()
    return choice