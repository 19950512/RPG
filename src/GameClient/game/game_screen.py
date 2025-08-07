import pygame
import time
import uuid
from typing import Optional
from .world import GameMap
from .entities import Entity, EntityManager, EntityType, MovementState
from .ui import Camera, UI

class GameScreen:
    def __init__(self, game):
        self.game = game
        self.running = True
        
        # Initialize game systems
        self.game_map = GameMap(60, 60, 32)  # 60x60 tiles, 32px each
        self.entity_manager = EntityManager()
        self.camera = Camera(game.screen_width, game.screen_height)
        self.ui = UI(game.screen_width, game.screen_height)
        
        # Set camera bounds based on map size
        self.camera.set_bounds(
            self.game_map.width * self.game_map.tile_size,
            self.game_map.height * self.game_map.tile_size
        )
        
        # Game state
        self.selected_character = None
        self.local_player: Optional[Entity] = None
        self.last_network_sync = time.time()
        
        # Initialize world
        self._initialize_world()
    
    def _initialize_world(self):
        """Initialize the game world with player and NPCs"""
        # Create local player
        spawn_x, spawn_y = self.game_map.spawn_points[0]
        world_x, world_y = self.game_map.tile_to_world(spawn_x, spawn_y)
        
        # Use character info if available
        player_name = "Player"
        if hasattr(self.game, 'selected_character') and self.game.selected_character:
            player_name = self.game.selected_character.get('name', 'Player')
        
        self.local_player = Entity(
            entity_id=str(uuid.uuid4()),
            entity_type=EntityType.PLAYER,
            x=world_x,
            y=world_y,
            name=player_name
        )
        
        # Set camera target
        self.camera.set_target(self.local_player)
        self.entity_manager.add_entity(self.local_player)
        self.entity_manager.local_player_id = self.local_player.id
        
        # Add NPCs
        for npc_x, npc_y, npc_name in self.game_map.npc_positions:
            world_x, world_y = self.game_map.tile_to_world(npc_x, npc_y)
            npc = Entity(
                entity_id=f"npc_{npc_name.lower()}",
                entity_type=EntityType.NPC,
                x=world_x,
                y=world_y,
                name=npc_name
            )
            npc.color = (0, 200, 0)  # Green for NPCs
            self.entity_manager.add_entity(npc)
        
        # Add some monsters
        for monster_x, monster_y, monster_name in self.game_map.monster_spawns:
            world_x, world_y = self.game_map.tile_to_world(monster_x, monster_y)
            monster = Entity(
                entity_id=f"monster_{monster_name.lower()}_{monster_x}_{monster_y}",
                entity_type=EntityType.MONSTER,
                x=world_x,
                y=world_y,
                name=monster_name
            )
            monster.color = (200, 0, 0)  # Red for monsters
            monster.stats.hp = 50
            monster.stats.max_hp = 50
            monster.stats.attack = 8
            self.entity_manager.add_entity(monster)
        
        # Add welcome message
        self.ui.add_chat_message("Welcome to the RPG world!")
        self.ui.add_chat_message("Use right-click to move, left-click to select")
        self.ui.add_chat_message("Press F1 for debug, I for inventory, C for character")
    
    def handle_events(self, event):
        """Handle game events"""
        # Let UI handle events first
        action = self.ui.handle_event(event, self.camera)
        
        if action:
            self._process_action(action)
        
        # Handle game-specific events
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.switch_state("char_select")
            elif event.key == pygame.K_SPACE:
                # Quick attack nearest enemy
                if self.local_player:
                    self._attack_nearest_enemy()
    
    def _process_action(self, action: str):
        """Process UI actions"""
        if not self.local_player:
            return
        
        if action.startswith("move:"):
            # Parse move coordinates
            coords = action[5:].split(',')
            if len(coords) == 2:
                try:
                    target_x = float(coords[0])
                    target_y = float(coords[1])
                    self.local_player.set_target(target_x, target_y)
                    self.ui.add_chat_message(f"Moving to ({target_x:.0f}, {target_y:.0f})")
                except ValueError:
                    pass
        
        elif action.startswith("click:"):
            # Handle entity selection
            coords = action[6:].split(',')
            if len(coords) == 2:
                try:
                    click_x = float(coords[0])
                    click_y = float(coords[1])
                    selected_entity = self._get_entity_at_position(click_x, click_y)
                    self.ui.set_selected_entity(selected_entity)
                    
                    if selected_entity:
                        self.ui.add_chat_message(f"Selected {selected_entity.name}")
                except ValueError:
                    pass
        
        elif action == "attack":
            if self.ui.selected_entity and self.ui.selected_entity.type == EntityType.MONSTER:
                self._attack_entity(self.ui.selected_entity)
            else:
                self._attack_nearest_enemy()
        
        elif action == "heal":
            self._use_heal_potion()
        
        elif action == "run":
            self.local_player.movement_state = MovementState.RUNNING
            self.ui.add_chat_message("Running mode activated")
        
        elif action.startswith("chat:"):
            chat_message = action[5:]
            self._process_chat_command(chat_message)
    
    def _get_entity_at_position(self, x: float, y: float) -> Optional[Entity]:
        """Get entity at world position"""
        click_range = 20  # Pixels
        
        for entity in self.entity_manager.entities.values():
            distance = ((entity.x - x) ** 2 + (entity.y - y) ** 2) ** 0.5
            if distance <= click_range:
                return entity
        
        return None
    
    def _attack_entity(self, target: Entity):
        """Attack a specific entity"""
        if not self.local_player or target == self.local_player:
            return
        
        if self.local_player.attack(target):
            self.ui.add_chat_message(f"Attacking {target.name}!")
            
            # Simple AI: monster attacks back
            if target.type == EntityType.MONSTER and target.stats.hp > 0:
                damage = max(1, target.stats.attack - self.local_player.stats.defense)
                self.local_player.take_damage(damage)
                self.ui.add_chat_message(f"{target.name} hits you for {damage} damage!")
                
                if self.local_player.stats.hp <= 0:
                    self.ui.add_chat_message("You have died! Respawning...")
                    self._respawn_player()
            
            # Check if target died
            if target.stats.hp <= 0:
                self.ui.add_chat_message(f"{target.name} has been defeated!")
                if target.type == EntityType.MONSTER:
                    # Give experience
                    exp_gained = target.stats.level * 10
                    self.local_player.stats.experience += exp_gained
                    self.ui.add_chat_message(f"Gained {exp_gained} experience!")
                    
                    # Check level up
                    self._check_level_up()
        else:
            self.ui.add_chat_message("Target is too far away!")
    
    def _attack_nearest_enemy(self):
        """Attack the nearest monster"""
        if not self.local_player:
            return
        
        nearest_monster = None
        nearest_distance = float('inf')
        
        for entity in self.entity_manager.entities.values():
            if entity.type == EntityType.MONSTER and entity.stats.hp > 0:
                distance = ((entity.x - self.local_player.x) ** 2 + 
                           (entity.y - self.local_player.y) ** 2) ** 0.5
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_monster = entity
        
        if nearest_monster:
            self.ui.set_selected_entity(nearest_monster)
            self._attack_entity(nearest_monster)
        else:
            self.ui.add_chat_message("No enemies nearby!")
    
    def _use_heal_potion(self):
        """Use a heal potion"""
        if not self.local_player:
            return
        
        if self.local_player.stats.hp < self.local_player.stats.max_hp:
            heal_amount = 25
            self.local_player.heal(heal_amount)
            self.ui.add_chat_message(f"Healed for {heal_amount} HP!")
        else:
            self.ui.add_chat_message("Already at full health!")
    
    def _check_level_up(self):
        """Check if player should level up"""
        if not self.local_player:
            return
        
        exp_needed = self.local_player.stats.level * 100
        if self.local_player.stats.experience >= exp_needed:
            self.local_player.stats.level += 1
            self.local_player.stats.experience -= exp_needed
            
            # Increase stats
            self.local_player.stats.max_hp += 10
            self.local_player.stats.hp = self.local_player.stats.max_hp
            self.local_player.stats.max_mp += 5
            self.local_player.stats.mp = self.local_player.stats.max_mp
            self.local_player.stats.attack += 2
            self.local_player.stats.defense += 1
            
            self.ui.add_chat_message(f"Level up! You are now level {self.local_player.stats.level}!")
    
    def _respawn_player(self):
        """Respawn the player"""
        if not self.local_player:
            return
        
        # Reset to spawn point
        spawn_x, spawn_y = self.game_map.spawn_points[0]
        world_x, world_y = self.game_map.tile_to_world(spawn_x, spawn_y)
        
        self.local_player.x = world_x
        self.local_player.y = world_y
        self.local_player.target_x = world_x
        self.local_player.target_y = world_y
        self.local_player.stats.hp = self.local_player.stats.max_hp
        self.local_player.movement_state = MovementState.IDLE
    
    def _process_chat_command(self, command: str):
        """Process chat commands"""
        if command.startswith("/"):
            # Handle commands
            parts = command[1:].split()
            if len(parts) > 0:
                cmd = parts[0].lower()
                
                if cmd == "help":
                    self.ui.add_chat_message("Commands: /heal, /teleport x y, /spawn monster")
                elif cmd == "heal":
                    self.local_player.stats.hp = self.local_player.stats.max_hp
                    self.ui.add_chat_message("Fully healed!")
                elif cmd == "teleport" and len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        self.local_player.x = x
                        self.local_player.y = y
                        self.local_player.target_x = x
                        self.local_player.target_y = y
                        self.ui.add_chat_message(f"Teleported to ({x}, {y})")
                    except ValueError:
                        self.ui.add_chat_message("Invalid coordinates")
                elif cmd == "spawn" and len(parts) >= 2:
                    if parts[1] == "monster":
                        self._spawn_monster_near_player()
                else:
                    self.ui.add_chat_message("Unknown command. Type /help for help")
        else:
            # Regular chat message (in multiplayer would send to server)
            self.ui.add_chat_message(f"You: {command}")
    
    def _spawn_monster_near_player(self):
        """Spawn a monster near the player"""
        if not self.local_player:
            return
        
        # Spawn monster near player
        monster_x = self.local_player.x + 50
        monster_y = self.local_player.y + 50
        
        monster = Entity(
            entity_id=f"spawned_monster_{time.time()}",
            entity_type=EntityType.MONSTER,
            x=monster_x,
            y=monster_y,
            name="Spawned Orc"
        )
        monster.color = (150, 0, 150)  # Purple for spawned monsters
        monster.stats.hp = 30
        monster.stats.max_hp = 30
        monster.stats.attack = 12
        
        self.entity_manager.add_entity(monster)
        self.ui.add_chat_message("Spawned a monster nearby!")
    
    def update(self, dt: float = 0):
        """Update game state"""
        # Update camera
        self.camera.update(dt)
        
        # Update all entities
        self.entity_manager.update_all(dt, self.game_map)
        
        # Network sync (in real multiplayer)
        current_time = time.time()
        if current_time - self.last_network_sync > 0.1:  # 10 times per second
            self._network_sync()
            self.last_network_sync = current_time
    
    def _network_sync(self):
        """Handle network synchronization (placeholder for multiplayer)"""
        # In a real implementation, this would:
        # 1. Send local player updates to server
        # 2. Receive updates for other players
        # 3. Update entity positions
        # 4. Handle combat events
        # 5. Sync chat messages
        pass
    
    def draw(self, screen: pygame.Surface):
        """Draw the game world"""
        # Clear screen
        screen.fill((20, 20, 40))
        
        # Draw map
        self.game_map.draw(screen, self.camera.x, self.camera.y, 
                          self.game.screen_width, self.game.screen_height)
        
        # Draw entities
        self.entity_manager.draw_all(screen, self.camera.x, self.camera.y)
        
        # Draw UI
        self.ui.draw(screen, self.local_player, 16)  # Assuming 60 FPS
    
    def reset(self):
        """Reset game state when entering"""
        # Could reload from save or reset to initial state
        pass
