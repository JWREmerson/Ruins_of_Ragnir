# External Imports
from typing import List, Deque, Tuple
from collections import deque
import random

# Internal Imports 
from resources import (
    RuinCard,
    HeroCard,
    GateCard,
    MinionCard,
    GearCard,
    SpellCard,
    RelicCard,
    GlyphCard,
)

# Tracks an individual player's state
class PlayerState:
    def __init__(
        self,
        hero: HeroCard,
        gate: GateCard,
        ruins: List[RuinCard],
        minions: List[MinionCard],
        gears: List[GearCard],
        spells: List[SpellCard],
        relics: List[RelicCard],
        glyphs: List[GlyphCard],
    ):
        self.hero = hero
        self.gate = gate
        
        # Build out and shuffle explore deck
        self.exp_deck: Deque[RuinCard] = deque(random.sample(ruins, k=40))
        self.exp_discard: Deque[RuinCard] = deque()
        
        # Build and shuffle adventure deck
        adv_pool = minions + gears + spells + relics + glyphs
        eligible = [c for c in adv_pool if not hasattr(c, 'elements') or set(c.elements).issubset(hero.elements)]
        self.adventure_deck: Deque = deque(random.sample(eligible, k=40))
        self.adventure_discard: Deque = deque()
        self.hand: List = []
        self.echoes = gate.starting_echoes
        self.turn_echo_count = 0
        self.staging_area: List = []
        self.relic_area: List = []
        self.hero_area: List = [hero]

# Tracks overall game state
class GameState:
    def __init__(self, player1: PlayerState, player2: PlayerState):
        self.players: Tuple[PlayerState, PlayerState] = (player1, player2)
        self.turn = 1
        self.active_player = 0
        
        # Map players to their hero and gate
        self.board = {
            "Player1": {"hero": player1.hero, "gate": player1.gate},
            "Player2": {"hero": player2.hero, "gate": player2.gate},
        }
        
        # Initialize board grid and occupant tracking
        self.rows = 7
        self.cols = 7
        self.map = {}
        self.occupants = {}
        self.gate_positions = {}
        
        # Track temporary buffs/effects
        self.fortified_units: List = []

    # Each player draws up to their gate's exp_hand
    def deal_starting_hands(self):
        for player in self.players:
            for _ in range(player.gate.exp_hand):
                if player.exp_deck:
                    player.hand.append(player.exp_deck.popleft())

    # Active player gains echoes equal to turn count
    def gain_echoes(self):
        player = self.players[self.active_player]
        player.echoes += self.turn
        player.turn_echo_count = self.turn

    # Active player draws from adventure deck up to their hero's Adventure Hand
    def draw_adventure_cards(self):
        player = self.players[self.active_player]
        target_hand = player.hero.adv_hand
        
        # already at or above hand size, draw one card
        if len(player.hand) >= target_hand:
            if player.adventure_deck:
                player.hand.append(player.adventure_deck.popleft())
        
        else:
            while len(player.hand) < target_hand and player.adventure_deck:
                player.hand.append(player.adventure_deck.popleft())

    # Active player pays all per-turn costs (Echoes/Health) on controlled cards
    def pay_upkeep(self):
        player = self.players[self.active_player]
        
        # Iterate hero and minions in play
        for unit in player.hero_area + player.staging_area:
            ability_text = getattr(unit, "ability", "") or ""
            text_lower = ability_text.lower()
            
            # Echo upkeep cost
            import re
            m_cost = re.search(r'pay\s+(\d+)\s+echo', text_lower)
            if m_cost:
                cost = int(m_cost.group(1))
                if player.echoes >= cost:
                    player.echoes -= cost

                # Remove unit from play if they can't pay
                else:
                    if unit in player.hero_area:
                        player.hero_area.remove(unit)
                    if unit in player.staging_area:
                        player.staging_area.remove(unit)
                    player.adventure_discard.append(unit)
                    continue

            # Health upkeep/penalty
            m_hp = re.search(r'lose\s+(\d+)\s+health', text_lower)
            if m_hp:
                dmg = int(m_hp.group(1))
                if hasattr(unit, "health"):
                    unit.health -= dmg
                    
                    # Unit dies
                    if unit.health <= 0:
                        if unit in player.hero_area:
                            player.hero_area.remove(unit)
                        if unit in player.staging_area:
                            player.staging_area.remove(unit)
                        player.adventure_discard.append(unit)
                        continue
        
        # Iterate Relics/Gears in relic_area for Upkeep costs
        for item in player.relic_area:
            ability_text = getattr(item, "ability", "") or ""
            text_lower = ability_text.lower()
            import re
            m_cost = re.search(r'pay\s+(\d+)\s+echo', text_lower)
            if m_cost:
                cost = int(m_cost.group(1))
                if player.echoes >= cost:
                    player.echoes -= cost
                else:
                    player.relic_area.remove(item)
                    player.adventure_discard.append(item)
                    continue
            m_hp = re.search(r'lose\s+(\d+)\s+health', text_lower)
            
            # Apply health loss to hero if appropriate
            if m_hp:
                dmg = int(m_hp.group(1))
                if player.hero_area:
                    hero = player.hero_area[0]
                    if hasattr(hero, "health"):
                        hero.health -= dmg
                        if hero.health <= 0:
                            player.hero_area.clear()
                            player.adventure_discard.append(hero)
                            continue

    def cleanup_end_of_turn(self):
        # Active player discards down to their hero's Adventure Hand stat
        player = self.players[self.active_player]
        while len(player.hand) > player.hero.adv_hand:
            card = player.hand.pop()
            player.adventure_discard.append(card)
        
        # Remove Fortify buffs from opponent's units (buff lasts until end of opponent's turn)
        opp_index = 1 - self.active_player
        opp_player = self.players[opp_index]
        for card in getattr(self, 'fortified_units', []):
            if (card in opp_player.staging_area) or (opp_player.hero_area and card is opp_player.hero_area[0]):
                
                # Defense buff removal
                if hasattr(card, "temp_defense_buff"):
                    delattr(card, "temp_defense_buff")
        self.fortified_units = []

    # Determine if a continuous path of face-up Ruins connects Player1's Gate to Player2's Gate
    def check_path_between_gates(self) -> bool:
        if not self.gate_positions:
            return False
        start = self.gate_positions.get("Player1")
        goal = self.gate_positions.get("Player2")
        if not start or not goal:
            return False
        from collections import deque
        visited = {start}
        queue = deque([start])
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1),           (0, 1),
                      (1, -1),  (1, 0),  (1, 1)]
        while queue:
            r, c = queue.popleft()
            if (r, c) == goal:
                return True
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                neighbor = (nr, nc)
                if neighbor in self.map and self.map[neighbor]["face_up"] and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return False

    def current_player(self) -> str:
        return f"Player{self.active_player + 1}"

    # Switch active player and increment turn counter
    def advance_turn(self): 
        self.active_player = 1 - self.active_player
        self.turn += 1

    # Check win conditions at end of Adventure turn
    def check_adventure_win(self) -> bool:
        # Gate destruction
        p1_gate = self.board["Player1"]["gate"]
        p2_gate = self.board["Player2"]["gate"]
        if getattr(p1_gate, "gate_health", 1) <= 0 or getattr(p2_gate, "gate_health", 1) <= 0:
            return True

        # Hero occupying opponent's Gate
        for player_label, opp_label in [("Player1", "Player2"), ("Player2", "Player1")]:
            hero = self.board[player_label]["hero"]
            opp_gate_pos = self.gate_positions.get(opp_label, None)
            if opp_gate_pos and hero in [u for (own, u) in self.occupants.get(opp_gate_pos, []) if own == player_label]:
                return True

        # 50 Echoes condition
        for idx, label in enumerate(["Player1", "Player2"]):
            if self.players[idx].echoes >= 50:
                return True

        # Deck exhaustion
        for idx, label in enumerate(["Player1", "Player2"]):
            if len(self.players[idx].adventure_deck) == 0:
                return True
        return False