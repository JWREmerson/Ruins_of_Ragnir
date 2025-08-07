# External Imports
import logging
from typing import Tuple

# Internal Imports
from game.state import GameState
from models import MinionCard, HeroCard, RelicCard, GearCard, SpellCard, GlyphCard
from network.protocol import send_obj, recv_obj

class ExplorePhase:
    # Runs one full turn of the Explore Phase
    def __init__(self, state: GameState, connections: Tuple):
        self.state = state
        self.p1_conn, self.p2_conn = connections
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        self.logger.info("Explore Phase: turn %d start", self.state.turn)
        self._step_gate_placement()
        self._step_draw()
        self._step_placement()
        self._step_reveal_and_resolve()
        self._step_path_check()
        self.state.advance_turn()
        self.logger.info("Explore Phase: turn %d end", self.state.turn)

    def _step_gate_placement(self):
        # Place both Gates on the board at starting positions and notify clients
        if not self.state.map:
            # Define starting positions (Player1 bottom middle, Player2 top middle)
            rows = getattr(self.state, 'rows', 7)
            cols = getattr(self.state, 'cols', 7)
            p1_pos = (rows - 1, cols // 2)
            p2_pos = (0, cols // 2)
            self.state.map[p1_pos] = {"card": self.state.players[0].gate, "face_up": True}
            self.state.map[p2_pos] = {"card": self.state.players[1].gate, "face_up": True}
            # Place heroes at their gate positions
            self.state.occupants[p1_pos] = [("Player1", self.state.players[0].hero)]
            self.state.occupants[p2_pos] = [("Player2", self.state.players[1].hero)]
            # Record gate positions for path checking
            self.state.gate_positions = {"Player1": p1_pos, "Player2": p2_pos}
        
        # Broadcast gate placement step to both clients
        send_obj(self.p1_conn, {"phase": "explore", "step": "gate_placement"})
        send_obj(self.p2_conn, {"phase": "explore", "step": "gate_placement"})
        self.logger.debug("Both Gates placed on board")

    def _step_draw(self):
        # Each player draws cards from their explore deck up to their Gate's Explore Hand size
        for idx, (player_name, conn) in enumerate((("Player1", self.p1_conn), ("Player2", self.p2_conn))):
            player_state = self.state.players[idx]
            target_hand = player_state.gate.exp_hand
            
            # If already at or above target, draw one card; else draw up to target
            if len(player_state.hand) >= target_hand:
                # Draw one card if possible
                if player_state.exp_deck:
                    player_state.hand.append(player_state.exp_deck.popleft())
            
            else:
                while len(player_state.hand) < target_hand and player_state.exp_deck:
                    player_state.hand.append(player_state.exp_deck.popleft())
            msg = {
                "phase": "explore",
                "step": "draw",
                "player": player_name,
                "hand_size": len(player_state.hand)
            }
            send_obj(conn, msg)
        
        self.logger.debug("Explore draw step complete")

    # Alternating facedown Ruin placement until both players pass
    def _step_placement(self):
        
        # Determine player order: lead player goes first
        order = [("Player1", self.p1_conn, 0), ("Player2", self.p2_conn, 1)]
        if self.state.active_player == 1:
            order.reverse()
        
        pass_flags = [False, False]
        any_placed = True
        
        while any_placed and not (pass_flags[0] and pass_flags[1]):
            any_placed = False
            for player, conn, idx in order:
                if pass_flags[idx]:
                    continue
                send_obj(conn, {"phase": "explore", "step": "placement", "player": player})
                choice = recv_obj(conn)
                
                # Player chooses to pass placement
                if not choice or choice.get("pass"):
                    pass_flags[idx] = True
                    self.logger.debug("%s passed on placing a Ruin", player)
                
                # Validate and apply placement choice
                else:
                    card_index = choice.get("card_index", None)
                    pos = choice.get("pos", None)
                    # Invalid choice format, skip
                    if card_index is None or pos is None:
                        self.logger.warning("Invalid placement choice from %s: %s", player, choice)
                        pass_flags[idx] = True
                        continue
                    
                    # Ensure chosen card is in player's hand
                    player_state = self.state.players[idx]
                    if not (0 <= card_index < len(player_state.hand)):
                        self.logger.warning("%s chose an invalid card index %s", player, card_index)
                        pass_flags[idx] = True
                        continue
                    
                    ruin_card = player_state.hand.pop(card_index)
                    
                    # Validate position is empty and adjacent to at least one face-up tile
                    if pos in self.state.map:
                        self.logger.warning("Position %s already occupied, placement by %s rejected", pos, player)
                        continue
                    r, c = pos
                    rows = getattr(self.state, 'rows', 7)
                    cols = getattr(self.state, 'cols', 7)
                    
                    if not (0 <= r < rows and 0 <= c < cols):
                        self.logger.warning("Position %s out of bounds, placement by %s rejected", pos, player)
                        continue
                    
                    # Check for legal connection
                    connected = False
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            if dr == 0 and dc == 0:
                                continue
                            neighbor = (r+dr, c+dc)
                            
                            if neighbor in self.state.map and self.state.map[neighbor]["face_up"]:
                                connected = True
                                break
                        
                        if connected:
                            break
                    
                    if not connected:
                        # No legal connection, treat as pass (could trigger mulligan ideally)
                        self.logger.debug("%s had no legal connection for %s at %s, skipping", player, ruin_card.name, pos)
                        pass_flags[idx] = True
                        continue
                    
                    # Place ruin face down
                    self.state.map[pos] = {"card": ruin_card, "face_up": False}
                    
                    # No occupants yet for a ruin environment
                    any_placed = True
                    self.logger.debug("%s placed %s at %s face down", player, ruin_card.name, pos)
            # End for loop of one round

        # After placement, any cards remaining in hand are returned to bottom of Exp_deck (mulligan step)
        for player_state in self.state.players:
            while player_state.hand:
                card = player_state.hand.pop(0)
                player_state.exp_deck.append(card)

    # Flip all facedown Ruins face-up and resolve any connection effects
    def _step_reveal_and_resolve(self): 
        new_connections = []
        for pos, tile in list(self.state.map.items()):
            if not tile["face_up"]:
                tile["face_up"] = True
                new_connections.append((pos, tile["card"]))

        # Resolve connection effects triggered by newly revealed connections
        effects_triggered = []
        
        # Check neighbors for required terrain connections
        for pos, card in new_connections:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    neighbor_pos = (pos[0]+dr, pos[1]+dc)
                    
                    if neighbor_pos in self.state.map and self.state.map[neighbor_pos]["face_up"]:
                        neighbor_card = self.state.map[neighbor_pos]["card"]
                        if ("Legally Connects" in card.ability or "Connection:" in card.ability):
                            if neighbor_card.terrain in card.ability or (neighbor_card.sub_terrain and neighbor_card.sub_terrain in card.ability):
                                effects_triggered.append(f"{card.name} connected to {neighbor_card.terrain}")
                        
                        if ("Legally Connects" in neighbor_card.ability or "Connection:" in neighbor_card.ability):
                            if card.terrain in neighbor_card.ability or (card.sub_terrain and card.sub_terrain in neighbor_card.ability):
                                effects_triggered.append(f"{neighbor_card.name} connected to {card.terrain}")
        
        # Notify clients of reveal and any triggered effects
        reveal_msg = {"phase": "explore", "step": "reveal", "effects": effects_triggered}
        send_obj(self.p1_conn, reveal_msg)
        send_obj(self.p2_conn, reveal_msg)
        self.logger.debug("Revealed all facedown ruins, connection effects: %s", effects_triggered)

    # Check for a continuous path between Gates (To move to Adv. Phase)
    def _step_path_check(self):
        path_exists = self.state.check_path_between_gates()
        self.logger.debug("Path exists between gates: %s", path_exists)
        return path_exists

# Runs one full turn of the Adventure Phase
class AdventurePhase:
    def __init__(self, state: GameState, connection):
        self.state = state
        self.conn = connection
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self):
        active = self.state.current_player()
        self.logger.info("Adventure Phase: %s turn start", active)
        self._step_echo_gain(active)
        self._step_draw(active)
        self._step_maintenance(active)
        self._step_summoning(active)
        self._step_movement(active)
        self._step_combat(active)
        self._step_end(active)
        self.state.advance_turn()
        self.logger.info("Adventure Phase: %s turn end", active)

    # Grant echoes to the active player
    def _step_echo_gain(self, player: str): 
        send_obj(self.conn, {"phase": "adventure", "step": "echo_gain", "player": player})
        self.state.gain_echoes()
        self.logger.debug("%s gained echoes", player)

    # Draw adventure cards for the active player
    def _step_draw(self, player: str):
        send_obj(self.conn, {"phase": "adventure", "step": "draw", "player": player})
        self.state.draw_adventure_cards()
        self.logger.debug("%s drew cards", player)

    # Apply any upkeep costs or effects
    def _step_maintenance(self, player: str):
        send_obj(self.conn, {"phase": "adventure", "step": "maintenance", "player": player})
        self.state.pay_upkeep()
        self.logger.debug("%s maintenance complete", player)

    # Moves to the Summon Phase
    def _step_summoning(self, player: str):
        send_obj(self.conn, {"phase": "adventure", "step": "summoning", "player": player})
        choice = recv_obj(self.conn)
        summoned = []

        # Track units summoned this turn
        self.state.just_summoned = []
        if choice:
            cards_to_play = []
            if isinstance(choice, list):
                cards_to_play = choice
            
            elif "cards" in choice:
                cards_to_play = choice["cards"]
            
            elif "card_index" in choice:
                cards_to_play = [choice["card_index"]]
            
            for idx in cards_to_play:
                player_state = self.state.players[0] if player == "Player1" else self.state.players[1]
                if not (0 <= idx < len(player_state.hand)):
                    continue
                card = player_state.hand[idx]
                # Check cost
                cost = getattr(card, "cost", 0)
                if player_state.echoes < cost:
                    continue
                # Pay cost
                player_state.echoes -= cost
                
                # Remove from hand
                player_state.hand.pop(idx)
                
                # Summon minion to player Gate
                if isinstance(card, MinionCard):
                    player_state.staging_area.append(card)
                    gate_pos = self.state.gate_positions[player]
                    if gate_pos not in self.state.occupants:
                        self.state.occupants[gate_pos] = []
                    self.state.occupants[gate_pos].append((player, card))
                    self.state.just_summoned.append(card)
                    summoned.append(card.name)

                # Summon hero if not already active
                elif isinstance(card, HeroCard):
                    if not player_state.hero_area:
                        player_state.hero_area.append(card)
                        gate_pos = self.state.gate_positions[player]
                        self.state.occupants[gate_pos].append((player, card))
                        self.state.just_summoned.append(card)
                        summoned.append(card.name)

                # Add Relic/Gear to Relic Hold and sacrifice oldest if RH is full
                elif isinstance(card, RelicCard) or isinstance(card, GearCard):
                    if len(player_state.relic_area) >= player_state.gate.relic_hold:
                        if player_state.relic_area:
                            removed = player_state.relic_area.pop(0)
                            player_state.adventure_discard.append(removed)
                            self.logger.debug("%s relic hold full, discarded %s", player, removed.name)
                    player_state.relic_area.append(card)
                    summoned.append(card.name)

                # Cast spell/glyph and discard immediately
                elif isinstance(card, SpellCard) or isinstance(card, GlyphCard):
                    player_state.adventure_discard.append(card)
                    summoned.append(card.name)
        self.logger.debug("%s summoned: %s", player, summoned)

    # Movement Step
    def _step_movement(self, player: str):
        send_obj(self.conn, {"phase": "adventure", "step": "movement", "player": player})
        choice = recv_obj(self.conn)
        self.state.moved_units = set()
        if choice:
            moves = choice.get("moves", None) or choice
            if isinstance(moves, dict):
                moves = [moves]
            for move in moves:
                origin = move.get("from") or move.get("origin") or move.get("start")
                dest = move.get("to") or move.get("dest") or move.get("end")
                if not origin or not dest:
                    continue
                origin = tuple(origin)
                dest = tuple(dest)
                units_here = self.state.occupants.get(origin, [])
                unit = None

                # Identify unit by provided key (name)
                if "unit" in move:
                    for (owner, u) in units_here:
                        if owner == player and (move["unit"] == getattr(u, 'name', None) or move["unit"] == getattr(u, 'heroname', None)):
                            unit = u
                            break
                
                # Default: take first friendly unit at origin
                else:
                    for (owner, u) in units_here:
                        if owner == player:
                            unit = u
                            break
                if not unit:
                    continue

                # Determine movement allowance
                base_move = getattr(unit, "movement", 0)
                remaining = base_move
                origin_tile = self.state.map.get(origin, {}).get("card")
                if origin_tile and origin_tile.terrain == "Wetlands":
                    spec = getattr(unit, "spec_move", [])
                    has_swampcraft = any("craft" in sm and "Wetland" in sm for sm in spec)
                    if not has_swampcraft:
                        remaining = max(0, remaining - ((remaining + 1) // 2))
                
                # Compute movement cost for this move
                cost = 1
                dest_tile = self.state.map.get(dest, {}).get("card")

                # Check for Exit penalty
                if origin_tile and "Requires 2 Movement to exit" in origin_tile.ability:
                    spec = getattr(unit, "spec_move", [])
                    if not any("craft" in sm and origin_tile.terrain in sm for sm in spec):
                        cost = max(cost, 2)
                
                # Check for Entry penalty
                if dest_tile and "Requires 2 Movement to enter" in dest_tile.ability:
                    spec = getattr(unit, "spec_move", [])
                    if not any("craft" in sm and dest_tile.terrain in sm for sm in spec):
                        cost = max(cost, 2)
                
                # Road effect
                if origin_tile and "do not require Movement" in origin_tile.ability:
                    cost = 0
                if dest_tile and "do not require Movement" in dest_tile.ability:
                    cost = 0
                if remaining < cost:
                    continue

                if (player, unit) in units_here:
                    units_here.remove((player, unit))
                if dest not in self.state.occupants:
                    self.state.occupants[dest] = []
                self.state.occupants[dest].append((player, unit))
                self.state.moved_units.add(unit)
                self.logger.debug("%s moved %s from %s to %s", player, getattr(unit, 'name', 'unit'), origin, dest)
        else:
            self.logger.debug("%s made no movement", player)

    # Combat Step
    def _step_combat(self, player: str):
        # Prompt player to declare and resolve combat
        send_obj(self.conn, {"phase": "adventure", "step": "combat", "player": player})
        choice = recv_obj(self.conn)
        self.state.attacked_units = set()
        if choice:
            attacks = choice.get("attacks", None) or choice
            if isinstance(attacks, dict):
                attacks = [attacks]
            for attack in attacks:
                atk_from = tuple(attack.get("from") or attack.get("attacker_pos", []))
                def_from = tuple(attack.get("to") or attack.get("defender_pos", []))
                if not atk_from or not def_from:
                    continue

                # Look for Attacker and Defender objects
                attacker = None
                defender = None
                for owner, unit in self.state.occupants.get(atk_from, []):
                    if owner == player:
                        attacker = unit
                        break
                for owner, unit in self.state.occupants.get(def_from, []):
                    if owner != player:
                        defender = unit
                        break
                if not attacker:
                    continue
                if not defender:
                    
                    # If target is opponent's Gate
                    opponent = "Player1" if player == "Player2" else "Player2"
                    if def_from == self.state.gate_positions.get(opponent, None):
                        # Simulate attacking the Gate
                        atk_speed = getattr(attacker, "speed", 0)
                        atk_attack = getattr(attacker, "attack", 0)
                        gate_card = self.state.board[opponent]["gate"]
                        gate_def = getattr(gate_card, "gate_defense", 0)
                        gate_health = getattr(gate_card, "gate_health", 0)
                        
                        # Attacker always deals damage first since Gates have no speed or attack
                        dmg = 1 if atk_attack == gate_def else max(0, atk_attack - gate_def)
                        if dmg > 0:
                            gate_health -= dmg
                        if gate_health <= 0:
                            outcome = f"{getattr(attacker,'name','Attacker')} destroyed {opponent}'s Gate"
                            gate_card.gate_health = 0
                        else:
                            outcome = f"{opponent}'s Gate took {dmg} damage"
                            gate_card.gate_health = gate_health
                        self.state.attacked_units.add(attacker)
                        self.logger.debug("Combat outcome: %s", outcome)
                    continue
                # Check Bloodlust: if attacker was just summoned and doesn't have Bloodlust, skip attack
                if hasattr(self.state, 'just_summoned') and attacker in self.state.just_summoned:
                    keywords = getattr(attacker, "keywords", [])
                    if "Bloodlust" not in keywords:
                        self.logger.debug("Attacker %s summoned this turn without Bloodlust, cannot attack", getattr(attacker, 'name', 'unit'))
                        continue
                
                # Check Backline: defender cannot be targeted if another enemy occupies same Ruin
                def_keywords = getattr(defender, "keywords", [])
                if "Backline" in def_keywords:
                    # If another opponent's unit is in the same Ruin
                    same_tile = [u for (own, u) in self.state.occupants.get(def_from, []) if own != player and u is not defender]
                    if same_tile:
                        self.logger.debug("Defender %s is Backline and another unit is present, cannot target", getattr(defender, 'name', 'unit'))
                        continue
                
                # Check range: ensure attacker and defender in adjacent or same Ruin
                ar, ac = atk_from; dr, dc = def_from
                if max(abs(ar-dr), abs(ac-dc)) > 1:
                    self.logger.debug("Defender out of range for attacker, skipping combat")
                    continue
                
                # Determine combat order by speed
                atk_speed = getattr(attacker, "speed", 0)
                def_speed = getattr(defender, "speed", 0)
                atk_attack = getattr(attacker, "attack", 0)
                def_attack = getattr(defender, "attack", 0)
                atk_def = getattr(attacker, "defense", 0)
                def_def = getattr(defender, "defense", 0)
                
                # Include Fortify buffs if present
                if hasattr(defender, "temp_defense_buff"):
                    def_def += defender.temp_defense_buff
                if hasattr(attacker, "temp_defense_buff"):
                    atk_def += attacker.temp_defense_buff
                
                # Helper for damage calculation
                def calc_damage(att, deff):
                    return 1 if att == deff and att != 0 else max(0, att - deff)
                outcome = ""
                
                # Attacker strikes first
                if atk_speed >= def_speed:
                    dmg = calc_damage(atk_attack, def_def)
                    if dmg > 0 and hasattr(defender, "health"):
                        defender.health -= dmg
                    
                    # Remove defender from board
                    if getattr(defender, "health", 1) <= 0:
                        outcome = f"{getattr(attacker,'name','Attacker')} killed {getattr(defender,'name','Defender')}"    
                        self.state.occupants[def_from] = [(own, u) for (own, u) in self.state.occupants.get(def_from, []) if u is not defender]
                        
                        # Update state for defender death
                        idx = 0 if player == "Player1" else 1
                        opp_idx = 1 - idx
                        
                        # Check if defender was hero or minion
                        if defender in self.state.players[opp_idx].hero_area:
                            self.state.players[opp_idx].hero_area.clear()
                        if defender in self.state.players[opp_idx].staging_area:
                            self.state.players[opp_idx].staging_area.remove(defender)
                        self.state.players[opp_idx].adventure_discard.append(defender)
                    
                    # Defender survives, counterattack
                    else:
                        dmg2 = calc_damage(def_attack, atk_def)
                        if dmg2 > 0 and hasattr(attacker, "health"):
                            attacker.health -= dmg2
                        if getattr(attacker, "health", 1) <= 0:
                            outcome = f"{getattr(defender,'name','Defender')} killed {getattr(attacker,'name','Attacker')}"
                            
                            # Remove Attacker from board
                            self.state.occupants[atk_from] = [(own, u) for (own, u) in self.state.occupants.get(atk_from, []) if u is not attacker]
                            idx = 0 if player == "Player1" else 1
                            
                            # Check if Attacker was hero or minion
                            if attacker in self.state.players[idx].hero_area:
                                self.state.players[idx].hero_area.clear()
                            if attacker in self.state.players[idx].staging_area:
                                self.state.players[idx].staging_area.remove(attacker)
                            self.state.players[idx].adventure_discard.append(attacker)
                        else:
                            outcome = f"Both {getattr(attacker,'name','')} and {getattr(defender,'name','')} survived the combat"
                
                # Defender strikes first
                else:
                    dmg = calc_damage(def_attack, atk_def)
                    if dmg > 0 and hasattr(attacker, "health"):
                        attacker.health -= dmg
                    
                    # Remove attacker
                    if getattr(attacker, "health", 1) <= 0:
                        outcome = f"{getattr(defender,'name','Defender')} killed {getattr(attacker,'name','Attacker')}"
                        self.state.occupants[atk_from] = [(own, u) for (own, u) in self.state.occupants.get(atk_from, []) if u is not attacker]
                        idx = 0 if player == "Player1" else 1
                        if attacker in self.state.players[idx].hero_area:
                            self.state.players[idx].hero_area.clear()
                        if attacker in self.state.players[idx].staging_area:
                            self.state.players[idx].staging_area.remove(attacker)
                        self.state.players[idx].adventure_discard.append(attacker)
                    
                    # Attacker survives to hit back
                    else:
                        dmg2 = calc_damage(atk_attack, def_def)
                        if dmg2 > 0 and hasattr(defender, "health"):
                            defender.health -= dmg2
                        if getattr(defender, "health", 1) <= 0:
                            outcome = f"{getattr(attacker,'name','Attacker')} killed {getattr(defender,'name','Defender')}"
                            self.state.occupants[def_from] = [(own, u) for (own, u) in self.state.occupants.get(def_from, []) if u is not defender]
                            opp_idx = 0 if player == "Player2" else 1
                            if defender in self.state.players[opp_idx].hero_area:
                                self.state.players[opp_idx].hero_area.clear()
                            if defender in self.state.players[opp_idx].staging_area:
                                self.state.players[opp_idx].staging_area.remove(defender)
                            self.state.players[opp_idx].adventure_discard.append(defender)
                        else:
                            outcome = f"Both {getattr(attacker,'name','')} and {getattr(defender,'name','')} survived the combat"
                
                # Mark Attacker as having attacked (for Fortify check)
                self.state.attacked_units.add(attacker)
                self.logger.debug("Combat outcome: %s", outcome)
        else:
            self.logger.debug("%s did not declare any attacks", player)

    # Perform end-of-turn cleanup
    def _step_end(self, player: str):
        send_obj(self.conn, {"phase": "adventure", "step": "end", "player": player})
        # Apply Fortify: Units with Fortify that did not move or attack gain +1 Defense until end of opponent's turn
        for pos, occ in self.state.occupants.items():
            for (owner, unit) in occ:
                if owner == player and hasattr(unit, "keywords") and "Fortify" in unit.keywords:
                    moved = hasattr(self.state, 'moved_units') and unit in getattr(self.state, 'moved_units')
                    attacked = hasattr(self.state, 'attacked_units') and unit in getattr(self.state, 'attacked_units')
                    if not moved and not attacked:
                        setattr(unit, "temp_defense_buff", 1)
                        if not hasattr(self.state, 'fortified_units'):
                            self.state.fortified_units = []
                        self.state.fortified_units.append(unit)
        self.state.cleanup_end_of_turn()
        self.logger.debug("%s end of turn cleanup complete", player)