# External Imports
import pygame
import sys
from typing import Tuple

def load_image(path: str) -> pygame.Surface:
    return pygame.image.load(path)

def draw_card(surface: pygame.Surface, image: pygame.Surface, position: Tuple[int, int]):
    surface.blit(image, position)

def render_text(
    surface: pygame.Surface,
    text: str,
    position: Tuple[int, int],
    font_size: int = 24,
    color: Tuple[int, int] = (255, 255, 255)
    ):

    font = pygame.font.SysFont(None, font_size)
    surface.blit(font.render(text, True, color), position)

# Original dynamic renderer 
def render_state(surface: pygame.Surface, state):
    
    # Draw grid, tiles, and units based on current state.
    surface.fill((0, 0, 0))
    tile_size = 50
    off_x = off_y = 50
    rows = getattr(state, "rows", 5)
    cols = getattr(state, "cols", 5)

    # Terrain Colors
    terrain_colors = {
    "Grasslands": (144, 238, 144),
    "Forest":     (34, 139, 34),
    "Lake":       (65, 105, 225),
    "Wetlands":   (139, 69, 19),
    "Mountains":  (169, 169, 169),
    "Depths":     (105, 105, 105),
    "Ruins":      (141, 198, 220),
    "Gate":       (36, 105, 128)
    }

    for r in range(rows):
        for c in range(cols):
            x, y = off_x + c * tile_size, off_y + r * tile_size
            rect = pygame.Rect(x, y, tile_size - 2, tile_size - 2)

            if (r, c) in state.map:
                tile = state.map[(r, c)]
                card = tile["card"]
                face_up = tile.get("face_up", True)
                if not face_up:
                    color = (80, 80, 80)
                
                else:
                    terrain = getattr(card, "terrain", "")
                    color = terrain_colors.get(terrain, (160, 160, 160))
                
                pygame.draw.rect(surface, color, rect)
                if face_up:
                    label = (getattr(card, "terrain", "") or "?")[0]
                    render_text(surface, label,
                                (x + tile_size // 2 - 8, y + tile_size // 2 - 8),
                                font_size=16)
            
            else:
                pygame.draw.rect(surface, (0, 0, 0), rect)

            pygame.draw.rect(surface, (60, 60, 60),
                             (x, y, tile_size, tile_size), 1)

    for pos, occ in state.occupants.items():
        if not occ:
            continue
        
        x, y = off_x + pos[1] * tile_size, off_y + pos[0] * tile_size
        
        for i, (owner, _unit) in enumerate(occ):
            color = (255, 0, 0) if owner == "Player1" else (0, 0, 255)
            radius = 5
            dx, dy = (i % 3) * 2 * radius, (i // 3) * 2 * radius
            pygame.draw.circle(surface, color, (x + 10 + dx, y + 10 + dy), radius)

    if hasattr(state, "players"):
        p1, p2 = state.players
        render_text(surface, f"P1: Echoes={p1.echoes} Hand={len(p1.hand)}",
                    (10, 10), font_size=20)
        render_text(surface, f"P2: Echoes={p2.echoes} Hand={len(p2.hand)}",
                    (400, 10), font_size=20)

# Static background 
BOARD_COLORS = {
    "deck":    (244, 206, 178),
    "gate":    (36, 105, 128),
    "ruins":   (141, 198, 220),
    "staging": (188, 214, 158),
    "relic":   (203, 150, 150),
    "echo":    (111, 93, 147),
    "hero":    (239, 195, 64),
}

def draw_board_background(surface: pygame.Surface):
    # Paint zones and legend
    W, H = surface.get_size()
    tile = 50
    margin = 20
    left = margin
    top = margin
    mid_x = left + tile * 1.5
    grid_w = tile * 5

    # Staging bars
    pygame.draw.rect(surface, BOARD_COLORS["staging"],
        (left, top, grid_w + tile * 2, tile))
    pygame.draw.rect(surface, BOARD_COLORS["staging"],
        (left, top + tile * 8, grid_w + tile * 2, tile))

    # Deck/Relic columns
    pygame.draw.rect(surface, BOARD_COLORS["deck"],
        (left, top + tile, tile * 2, tile * 4))
    pygame.draw.rect(surface, BOARD_COLORS["relic"],
        (left, top + tile * 7, tile * 2, tile * 2))

    # Echo/Heroes corner squares
    pygame.draw.rect(surface, BOARD_COLORS["echo"],
        (left, top + tile, tile, tile))
    pygame.draw.rect(surface, BOARD_COLORS["hero"],
        (left + tile, top + tile, tile, tile))
    pygame.draw.rect(surface, BOARD_COLORS["hero"],
        (mid_x + grid_w, top + tile * 2, tile, tile))
    pygame.draw.rect(surface, BOARD_COLORS["echo"],
        (mid_x + grid_w + tile, top + tile * 2, tile, tile))

    # Legend
    legend_w = tile * 6
    legend_left = W - legend_w - margin
    legend_top = top
    box_h = int(tile * 1.2)

    labels = [
        ("Deck/Discard Pile Area", "deck"),
        ("Gate Starting Position", "gate"),
        ("Ruins Area",             "ruins"),
        ("Staging Area",           "staging"),
        ("Relic Area",             "relic"),
        ("Echo Area",              "echo"),
        ("Hero Area",              "hero"),
    ]

    pygame.draw.rect(surface, (255, 255, 255),
        (legend_left - 5, legend_top - 5,
         legend_w + 10, box_h * len(labels) + 10), 1)

    for i, (text, key) in enumerate(labels):
        y = legend_top + i * box_h
        pygame.draw.rect(surface, BOARD_COLORS[key],
            (legend_left, y, legend_w, box_h))
        render_text(surface, text, (legend_left + 8, y + 6),
                    font_size=22, color=(0, 0, 0))

# Wrapper 
_original_render_state = render_state
def render_state(surface: pygame.Surface, state):
    surface.fill((255, 255, 255))
    draw_board_background(surface)
    _original_render_state(surface, state)

sys.modules[__name__].render_state = render_state