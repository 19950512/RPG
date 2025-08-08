import pygame
import time
import uuid
import queue
import threading
from typing import Optional
from .world import GameMap
from .entities import Entity, EntityManager, EntityType, MovementState
from .ui import Camera, UI
from ..grpc_client import grpc_client

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
        
        # Auto-sync settings - sync player data every 5 seconds
        self.auto_sync_interval = 5.0  # Sync every 5 seconds
        self.last_auto_sync = 0
        
        # Flag to track if we've joined the world
        self.world_joined = False
        
        # Thread-safe queue for world updates
        self.world_updates_queue = queue.Queue()
        
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
        self.ui.add_chat_message("Use ARROW KEYS to move, or right-click on map")
        self.ui.add_chat_message("Hold SHIFT + arrows to run")
        self.ui.add_chat_message("Press F1 for debug, I for inventory, C for character")
        
        # JoinWorld will be called after the game state is properly initialized
    
    def reset(self):
        """Called when switching to this state"""
        print("🔍 DEBUG: GameScreen reset() called")
        # Join world when entering the game state
        self._join_world_on_server()
    
    def handle_events(self, event):
        """Handle game events"""
        # Let UI handle events first
        action = self.ui.handle_event(event, self.camera)
        
        if action:
            self._process_action(action)
        
        # Handle game-specific events
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Leave world before going back to character selection
                if hasattr(self.game, 'auth_token') and self.game.auth_token:
                    try:
                        response = grpc_client.leave_world(self.game.auth_token)
                        if response.success:
                            self.ui.add_chat_message(f"🚪 {response.message}")
                            print(f"🚪 Left world: {response.message}")
                        else:
                            self.ui.add_chat_message(f"⚠️ Failed to leave: {response.message}")
                            print(f"⚠️ Failed to leave world: {response.message}")
                    except Exception as e:
                        self.ui.add_chat_message(f"❌ Error leaving world: {str(e)}")
                        print(f"❌ Error leaving world: {e}")
                
                self.game.switch_state("char_select")
            elif event.key == pygame.K_SPACE:
                # Quick attack nearest enemy
                if self.local_player:
                    self._attack_nearest_enemy()
            elif event.key == pygame.K_x:
                # Debug: Add experience for testing
                if self.local_player:
                    self.local_player.stats.experience += 50
                    self.ui.add_chat_message("Debug: Added 50 XP!")
                    # Auto-sync debug XP to server
                    self._sync_player_stats_to_server()
                    self._check_level_up()
            
            # Movement with arrow keys
            elif event.key == pygame.K_UP:
                self._move_player_by_direction(0, -1)
            elif event.key == pygame.K_DOWN:
                self._move_player_by_direction(0, 1)
            elif event.key == pygame.K_LEFT:
                self._move_player_by_direction(-1, 0)
            elif event.key == pygame.K_RIGHT:
                self._move_player_by_direction(1, 0)
    
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
                    
                    # Determine movement type based on current state
                    movement_type = "run" if self.local_player.movement_state == MovementState.RUNNING else "walk"
                    
                    # Use unified movement processing
                    self._process_movement(target_x, target_y, movement_type)
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
                
                # Auto-sync HP changes after taking damage
                self._sync_player_stats_to_server()
                
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
                    
                    # Auto-sync experience gained to server
                    self._sync_player_stats_to_server()
                    
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
            old_level = self.local_player.stats.level
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
            
            # Sync with server
            self._sync_player_stats_to_server()
            print(f"📊 Level up synced: {old_level} -> {self.local_player.stats.level}")
    
    def _sync_player_stats_to_server(self):
        """Sync current player stats to server"""
        if not self.local_player or not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
        
        try:
            grpc_client.update_player_stats(
                self.game.auth_token,
                level=self.local_player.stats.level,
                experience=self.local_player.stats.experience,
                hp=self.local_player.stats.hp,
                mp=self.local_player.stats.mp
            )
            print(f"📊 Stats synced to server: Level {self.local_player.stats.level}, EXP {self.local_player.stats.experience}, HP {self.local_player.stats.hp}/{self.local_player.stats.max_hp}")
        except Exception as e:
            print(f"Error syncing stats to server: {e}")
    
    def _sync_player_position_to_server(self):
        """Sync current player position and state to server"""
        if not self.local_player or not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
        
        try:
            # Send position and all relevant state info
            grpc_client.update_player_position(
                self.game.auth_token,
                position_x=self.local_player.x,
                position_y=self.local_player.y,
                facing_direction=self.local_player.facing_direction,
                movement_state=self.local_player.movement_state
            )
            print(f"📍 Position synced to server: ({self.local_player.x:.0f}, {self.local_player.y:.0f}), facing={self.local_player.facing_direction}, state={self.local_player.movement_state}")
        except Exception as e:
            print(f"Error syncing position to server: {e}")
    
    def _sync_all_player_data_to_server(self):
        """Sync all player data to server (comprehensive sync)"""
        if not self.local_player or not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
        
        try:
            # Sync stats and position together
            self._sync_player_stats_to_server()
            self._sync_player_position_to_server()
            print(f"🔄 Complete player data synced to server")
        except Exception as e:
            print(f"Error syncing all player data to server: {e}")
    
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
        
        # Auto-sync respawn to server
        self._sync_all_player_data_to_server()
        self.ui.add_chat_message("Respawned and synced to server!")
    
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
                    # Auto-sync healing to server
                    self._sync_player_stats_to_server()
                elif cmd == "teleport" and len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        self.local_player.x = x
                        self.local_player.y = y
                        self.local_player.target_x = x
                        self.local_player.target_y = y
                        self.ui.add_chat_message(f"Teleported to ({x}, {y})")
                        # Auto-sync teleport position to server
                        self._sync_player_position_to_server()
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
        # Join world once when auth token is available
        if not self.world_joined and hasattr(self.game, 'auth_token') and self.game.auth_token:
            self._join_world_on_server()
            self.world_joined = True

        # Process world updates from streaming thread
        self._process_world_updates_queue()
        
        # Update camera
        self.camera.update(dt)
        
        # Update all entities
        self.entity_manager.update_all(dt, self.game_map)
        
        # Auto-sync player data to server periodically
        current_time = time.time()
        if current_time - self.last_auto_sync > self.auto_sync_interval:
            if self.local_player and hasattr(self.game, 'auth_token') and self.game.auth_token:
                self._sync_all_player_data_to_server()
                self.ui.add_chat_message("🔄 Auto-sync: Player data saved to server")
                print(f"🕐 Auto-sync triggered: {current_time:.1f}")
            self.last_auto_sync = current_time
        
        # Network sync (in real multiplayer)
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
    
    def _join_world_on_server(self):
        """Join the world on the server"""
        print("🔍 DEBUG: _join_world_on_server called")
        try:
            if hasattr(self.game, 'auth_token') and self.game.auth_token:
                print(f"🔍 DEBUG: Auth token exists, calling join_world...")
                response = grpc_client.join_world(self.game.auth_token)
                print(f"🔍 DEBUG: join_world response: success={response.success}, message={response.message}")
                if response.success:
                    self.ui.add_chat_message(f"🌍 {response.message}")
                    
                    # Update local player data from server
                    if response.player:
                        # Sync position
                        self.local_player.x = response.player.position_x
                        self.local_player.y = response.player.position_y
                        self.local_player.name = response.player.name
                        
                        # Sync stats from server (this overwrites local data with server data)
                        self.local_player.stats.level = response.player.level
                        self.local_player.stats.experience = response.player.experience
                        self.local_player.stats.hp = response.player.current_hp
                        self.local_player.stats.max_hp = response.player.max_hp
                        self.local_player.stats.mp = response.player.current_mp
                        self.local_player.stats.max_mp = response.player.max_mp
                        self.local_player.stats.attack = response.player.attack
                        self.local_player.stats.defense = response.player.defense
                        self.local_player.facing_direction = response.player.facing_direction
                        self.local_player.movement_state = response.player.movement_state
                        
                        self.ui.add_chat_message(f"📍 Position: ({response.player.position_x:.0f}, {response.player.position_y:.0f})")
                        self.ui.add_chat_message(f"📊 Server Data: Level {response.player.level}, EXP {response.player.experience}")
                        print(f"📊 Player data synced from server: Level {response.player.level}, EXP {response.player.experience}")
                    
                    # Show other online players
                    if response.other_players:
                        self.ui.add_chat_message(f"👥 {len(response.other_players)} other players online")
                        # Add other players as entities
                        self._add_other_players(response.other_players)
                    
                    # Start world updates stream for real-time multiplayer
                    self._start_world_updates_stream()
                else:
                    self.ui.add_chat_message(f"❌ Failed to join world: {response.message}")
                    print(f"❌ DEBUG: Failed to join world: {response.message}")
            else:
                self.ui.add_chat_message("❌ No authentication token available")
                print(f"❌ DEBUG: No auth token - hasattr: {hasattr(self.game, 'auth_token')}, token: {getattr(self.game, 'auth_token', None)}")
        except Exception as e:
            self.ui.add_chat_message(f"❌ Error joining world: {str(e)}")
            print(f"❌ DEBUG: Exception in join_world: {e}")
            print(f"Error joining world: {e}")
    
    def _move_player_by_direction(self, dx: int, dy: int):
        """Move player by direction (for arrow key controls)"""
        if not self.local_player:
            return
            
        # Calculate movement distance (tile size)
        move_distance = 32  # pixels per move
        
        # Calculate new position
        new_x = self.local_player.x + (dx * move_distance)
        new_y = self.local_player.y + (dy * move_distance)
        
        # Determine movement type (can add shift detection for running later)
        keys = pygame.key.get_pressed()
        movement_type = "run" if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else "walk"
        
        # Process the movement
        self._process_movement(new_x, new_y, movement_type)
        
        print(f"🎮 Arrow key movement: direction=({dx},{dy}), new_pos=({new_x:.0f},{new_y:.0f}), type={movement_type}")
    
    def _process_movement(self, target_x: float, target_y: float, movement_type: str = "walk"):
        """Process movement to target position"""
        if not self.local_player:
            return
            
        # Calculate direction based on movement
        current_x = self.local_player.x
        current_y = self.local_player.y
        dx = target_x - current_x
        dy = target_y - current_y
        
        # Update local player position immediately for responsiveness
        self.local_player.x = target_x
        self.local_player.y = target_y
        
        # Update facing direction based on movement direction
        if abs(dx) > abs(dy):
            self.local_player.facing_direction = 2 if dx > 0 else 4  # Right or Left
        else:
            self.local_player.facing_direction = 3 if dy > 0 else 1  # Down or Up
        
        # Set movement state
        self.local_player.movement_state = movement_type
        
        # Send movement to server
        self._move_player_on_server(target_x, target_y, movement_type)
        
        # Update UI
        self.ui.add_chat_message(f"Moving to ({target_x:.0f}, {target_y:.0f}) [{movement_type}]")
    
    def _move_player_on_server(self, target_x, target_y, movement_type):
        """Send movement command to server"""
        try:
            if hasattr(self.game, 'auth_token') and self.game.auth_token:
                response = grpc_client.move_player(
                    self.game.auth_token, 
                    target_x, 
                    target_y, 
                    movement_type
                )
                if response.success:
                    self.ui.add_chat_message(f"🚀 Server: {response.message}")
                    # Auto-sync position after successful movement
                    self._sync_player_position_to_server()
                else:
                    self.ui.add_chat_message(f"❌ Move failed: {response.message}")
            else:
                self.ui.add_chat_message("❌ No authentication token for movement")
        except Exception as e:
            self.ui.add_chat_message(f"❌ Movement error: {str(e)}")
            print(f"Error moving player: {e}")

    def reset(self):
        """Reset game state when entering"""
        # Could reload from save or reset to initial state
        pass
    
    def _add_other_players(self, other_players):
        """Add other players as entities to the game world"""
        for player_info in other_players:
            if player_info.is_online and player_info.id != self.local_player.id:
                # Check if player already exists
                existing_entity = self.entity_manager.get_entity(f"player_{player_info.id}")
                
                if existing_entity:
                    # Update existing player
                    existing_entity.x = player_info.position_x
                    existing_entity.y = player_info.position_y
                    existing_entity.name = player_info.name
                    existing_entity.stats.level = player_info.level
                    existing_entity.stats.hp = player_info.current_hp
                    existing_entity.stats.max_hp = player_info.max_hp
                    existing_entity.facing_direction = player_info.facing_direction
                    existing_entity.movement_state = player_info.movement_state
                else:
                    # Create new remote player entity
                    remote_player = Entity(
                        entity_id=f"player_{player_info.id}",
                        entity_type=EntityType.PLAYER,
                        x=player_info.position_x,
                        y=player_info.position_y,
                        name=player_info.name
                    )
                    
                    # Set remote player visual properties
                    remote_player.color = (0, 100, 255)  # Blue for other players
                    remote_player.stats.level = player_info.level
                    remote_player.stats.hp = player_info.current_hp
                    remote_player.stats.max_hp = player_info.max_hp
                    remote_player.stats.mp = player_info.current_mp
                    remote_player.stats.max_mp = player_info.max_mp
                    remote_player.stats.attack = player_info.attack
                    remote_player.stats.defense = player_info.defense
                    remote_player.facing_direction = player_info.facing_direction
                    remote_player.movement_state = player_info.movement_state
                    
                    # Add to entity manager
                    self.entity_manager.add_entity(remote_player)
                    
                    self.ui.add_chat_message(f"👤 Player {player_info.name} (Level {player_info.level}) joined the world")
                    print(f"👤 Added remote player: {player_info.name} at ({player_info.position_x}, {player_info.position_y})")
    
    def _start_world_updates_stream(self):
        """Start receiving real-time world updates from server"""
        if not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
            
        try:
            # Start world updates in a separate thread
            threading.Thread(target=self._world_updates_worker, daemon=True).start()
            print("🌍 Started world updates stream")
        except Exception as e:
            print(f"❌ Failed to start world updates: {e}")
    
    def _world_updates_worker(self):
        """Worker thread for polling world updates"""
        import time
        
        try:
            print("🔄 Starting world updates polling...")
            
            while True:
                try:
                    # Poll for world state every 100ms (10 FPS)
                    world_state = grpc_client.get_world_state(self.game.auth_token)
                    
                    if world_state and world_state.players:
                        self._update_remote_players(world_state.players)
                    
                    # Wait 100ms before next poll
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Error polling world state: {e}")
                    time.sleep(1)  # Wait longer if there's an error
                    
        except Exception as e:
            print(f"❌ World updates polling error: {e}")
    
    def _update_remote_players(self, players):
        """Queue remote player updates for processing in main thread"""
        # Put the update in the queue to be processed by main thread
        self.world_updates_queue.put(('player_updates', players))
    
    def _process_world_updates_queue(self):
        """Process world updates from the queue in main thread"""
        try:
            while not self.world_updates_queue.empty():
                update_type, data = self.world_updates_queue.get_nowait()
                
                if update_type == 'player_updates':
                    self._apply_player_updates(data)
                    
        except queue.Empty:
            pass
    
    def _apply_player_updates(self, players):
        """Apply player updates in main thread"""
        if not self.local_player:
            return
            
        for player_info in players:
            if player_info.is_online and player_info.id != self.local_player.id:
                entity_id = f"player_{player_info.id}"
                existing_entity = self.entity_manager.get_entity(entity_id)
                
                if existing_entity:
                    # Update existing remote player
                    existing_entity.x = player_info.position_x
                    existing_entity.y = player_info.position_y
                    existing_entity.facing_direction = player_info.facing_direction
                    existing_entity.movement_state = player_info.movement_state
                    existing_entity.stats.hp = player_info.current_hp
                    existing_entity.stats.level = player_info.level
                    print(f"🔄 Updated remote player {player_info.name} position: ({player_info.position_x}, {player_info.position_y})")
                else:
                    # Create new remote player if not exists
                    self._add_other_players([player_info])
                    print(f"➕ Added new remote player {player_info.name}")
