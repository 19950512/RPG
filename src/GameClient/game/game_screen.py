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
from ..world_client import world_client

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
        
        # Thread control for world updates
        self.world_updates_running = False
        self.world_entity_updates_running = False
        
        # Thread-safe queue for world updates
        self.world_updates_queue = queue.Queue()
        self.world_entity_updates_queue = queue.Queue()
        
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
        
        # NPCs and monsters will be loaded from server
        # (Removed local creation - all entities now come from server)
        
        # Add welcome message
        self.ui.add_chat_message("Welcome to the RPG world!")
        self.ui.add_chat_message("Use ARROW KEYS or WASD to move")
        self.ui.add_chat_message("Hold SHIFT + arrows to run")
        self.ui.add_chat_message("Press F1 to attack, ' for stats, F11 for fullscreen")
        self.ui.add_chat_message("Press I for inventory, C for character")
        
        # JoinWorld will be called after the game state is properly initialized
        self._join_world_on_server()
        
        # Load world entities from server
        self._load_world_entities()

    def _load_world_entities(self):
        """Load NPCs, monsters, and items from server"""
        try:
            print("🌍 Loading world entities from server...")
            
            response = world_client.get_world_entities()
            
            # Clear existing NPCs and monsters (keep only players)
            self._cleanup_world_entities()
            
            # Add NPCs from server
            for npc_data in response.npcs:
                npc = self._create_entity_from_server_data(npc_data)
                self.entity_manager.add_entity(npc)
                print(f"🟢 Added NPC: {npc.name} at ({npc.x:.0f}, {npc.y:.0f})")
            
            # Add monsters from response  
            for monster_data in response.monsters:
                monster = self._create_entity_from_server_data(monster_data)
                self.entity_manager.add_entity(monster)
                print(f"🔴 Added Monster: {monster.name} at ({monster.x:.0f}, {monster.y:.0f}) HP: {monster.stats.hp}/{monster.stats.max_hp}")
            
            # Add items from server
            for item_data in response.items:
                item = self._create_entity_from_server_data(item_data)
                self.entity_manager.add_entity(item)
                print(f"🟡 Added Item: {item.name} at ({item.x:.0f}, {item.y:.0f})")
                
            print(f"✅ Loaded {len(response.npcs)} NPCs, {len(response.monsters)} monsters, {len(response.items)} items")
            self.ui.add_chat_message(f"🌍 Loaded {len(response.npcs)} NPCs, {len(response.monsters)} monsters, {len(response.items)} items from server!")
                
        except Exception as e:
            print(f"❌ Error loading world entities: {e}")
            self.ui.add_chat_message("⚠️ Failed to load world entities from server")
    
    def _create_entity_from_server_data(self, entity_data):
        """Create a local Entity object from server WorldEntity data"""
        # Determine entity type
        if entity_data.entity_type == "npc":
            entity_type = EntityType.NPC
            color = (0, 200, 0)  # Green
        elif entity_data.entity_type == "monster":
            entity_type = EntityType.MONSTER  
            color = (200, 0, 0)  # Red
        elif entity_data.entity_type == "item":
            entity_type = EntityType.ITEM
            color = (255, 255, 0)  # Yellow
        else:
            entity_type = EntityType.NPC  # Default
            color = (128, 128, 128)  # Gray
        
        # Create entity
        entity = Entity(
            entity_id=entity_data.id,
            entity_type=entity_type,
            x=entity_data.position_x,
            y=entity_data.position_y,
            name=entity_data.name
        )
        
        # Set color
        entity.color = color
        
        # Set stats for monsters
        if entity_type == EntityType.MONSTER:
            entity.stats.hp = entity_data.current_hp
            entity.stats.max_hp = entity_data.max_hp
            entity.stats.mp = entity_data.current_mp
            entity.stats.max_mp = entity_data.max_mp
            entity.stats.attack = entity_data.attack
            entity.stats.defense = entity_data.defense
            entity.facing_direction = entity_data.facing_direction
            entity.movement_state = MovementState(entity_data.movement_state) if entity_data.movement_state else MovementState.IDLE
        
        return entity
    
    def _cleanup_world_entities(self):
        """Remove all NPCs, monsters, and items from entity manager"""
        entity_ids_to_remove = []
        
        for entity_id, entity in self.entity_manager.entities.items():
            if entity.type in [EntityType.NPC, EntityType.MONSTER, EntityType.ITEM]:
                entity_ids_to_remove.append(entity_id)
        
        for entity_id in entity_ids_to_remove:
            self.entity_manager.remove_entity(entity_id)
            
        print(f"🧹 Cleaned up {len(entity_ids_to_remove)} world entities")
    
    def reset(self):
        """Called when switching to this state"""
        print("🔍 DEBUG: GameScreen reset() called")
        
        # Reset world state
        self.world_joined = False
        self._stop_all_updates()
        
        # Clear any existing remote players (keep local player and NPCs/monsters)
        self._cleanup_remote_players()
        
        # Reset local player to selected character data
        self._reset_local_player()
        
        # Join world when entering the game state
        self._join_world_on_server()
    
    def _cleanup_world_state(self):
        """Clean up world state when leaving"""
        print("🧹 Cleaning up world state...")
        
        # Reset flags
        self.world_joined = False
        self._stop_all_updates()
        
        # Clear world updates queues
        while not self.world_updates_queue.empty():
            try:
                self.world_updates_queue.get_nowait()
            except:
                break
                
        while not self.world_entity_updates_queue.empty():
            try:
                self.world_entity_updates_queue.get_nowait()
            except:
                break
        
        # Remove all remote players (keep local player, NPCs, monsters)
        self._cleanup_remote_players()
        
        print("✅ World state cleaned up")
    
    def _cleanup_remote_players(self):
        """Remove all remote players from entity manager"""
        remote_player_ids = []
        
        for entity_id, entity in self.entity_manager.entities.items():
            # Remove entities that are remote players (other players, not local)
            if (entity.type == EntityType.PLAYER and 
                entity_id != self.local_player.id and 
                entity_id.startswith("player_")):
                remote_player_ids.append(entity_id)
        
        for entity_id in remote_player_ids:
            self.entity_manager.remove_entity(entity_id)
            print(f"🗑️ Removed remote player: {entity_id}")
    
    def _reset_local_player(self):
        """Reset local player to initial state based on selected character"""
        if not self.local_player:
            return
            
        # Reset to spawn point
        spawn_x, spawn_y = self.game_map.spawn_points[0]
        world_x, world_y = self.game_map.tile_to_world(spawn_x, spawn_y)
        
        self.local_player.x = world_x
        self.local_player.y = world_y
        self.local_player.target_x = world_x
        self.local_player.target_y = world_y
        self.local_player.movement_state = MovementState.IDLE
        self.local_player.facing_direction = 0
        
        # Update name if character is selected
        if hasattr(self.game, 'selected_character') and self.game.selected_character:
            self.local_player.name = self.game.selected_character.get('name', 'Player')
        
        print(f"🔄 Reset local player: {self.local_player.name} at ({world_x}, {world_y})")
    
    def handle_events(self, event):
        """Handle game events"""
        # Let UI handle events first
        action = self.ui.handle_event(event, self.camera)
        
        if action:
            self._process_action(action)
        
        # Handle game-specific events
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # Coletar item mais próximo
                if self.local_player:
                    nearest_item = None
                    nearest_distance = float('inf')
                    for entity in self.entity_manager.entities.values():
                        if entity.type == EntityType.ITEM:
                            distance = ((entity.x - self.local_player.x) ** 2 + (entity.y - self.local_player.y) ** 2) ** 0.5
                            if distance < 32 and distance < nearest_distance:
                                nearest_distance = distance
                                nearest_item = entity
                    if nearest_item:
                        self._pickup_item(nearest_item)
                    else:
                        self.ui.add_chat_message("Nenhum item próximo para coletar.")
                return
            if event.key == pygame.K_ESCAPE:
                # Stop world updates polling
                self.world_updates_running = False
                print("🛑 Stopping world updates...")
                
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
                
                # Clear world state before leaving
                self._cleanup_world_state()
                
                # Clear selected character state to prevent wrong character selection
                if hasattr(self.game, 'selected_character'):
                    self.game.selected_character = None
                    print("🧹 Cleared selected character state")
                
                self.game.switch_state("char_select")
            elif event.key == pygame.K_F1:
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
            elif event.key == pygame.K_QUOTE:  # ' key
                # Debug: Display player stats
                if self.local_player:
                    stats = self.local_player.stats
                    self.ui.add_chat_message("=== DEBUG STATS ===")
                    self.ui.add_chat_message(f"Level: {stats.level} | XP: {stats.experience}")
                    self.ui.add_chat_message(f"HP: {stats.hp}/{stats.max_hp} | MP: {stats.mp}/{stats.max_mp}")
                    self.ui.add_chat_message(f"Attack: {stats.attack} | Defense: {stats.defense}")
                    self.ui.add_chat_message(f"Position: ({self.local_player.x:.0f}, {self.local_player.y:.0f})")
                    self.ui.add_chat_message(f"Facing: {self.local_player.facing_direction} | State: {self.local_player.movement_state}")
            elif event.key == pygame.K_F11:
                # Toggle fullscreen
                self._toggle_fullscreen()
            
            # Note: Arrow key movement is now handled in _handle_continuous_movement()
            # which is called from update() method for smooth continuous movement
    
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
            # Handle entity selection ou coleta de item
            coords = action[6:].split(',')
            if len(coords) == 2:
                try:
                    click_x = float(coords[0])
                    click_y = float(coords[1])
                    selected_entity = self._get_entity_at_position(click_x, click_y)
                    self.ui.set_selected_entity(selected_entity)
                    if selected_entity:
                        if selected_entity.type == EntityType.ITEM:
                            self._pickup_item(selected_entity)
                        else:
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

    def _pickup_item(self, item_entity):
        """Solicita ao servidor a coleta do item e atualiza o inventário local"""
        try:
            if hasattr(self.game, 'auth_token') and self.game.auth_token:
                response = world_client.interact_with_entity(
                    entity_id=item_entity.id,
                    interaction_type="pickup"
                )
                if response.success:
                    self.ui.add_chat_message(f"👜 {response.message}")
                    # Remove item localmente
                    self.entity_manager.remove_entity(item_entity.id)
                else:
                    self.ui.add_chat_message(f"❌ {response.message}")
        except Exception as e:
            self.ui.add_chat_message(f"⚠️ Erro ao coletar item: {e}")
    
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
        
        # Check distance
        distance = ((self.local_player.x - target.x) ** 2 + (self.local_player.y - target.y) ** 2) ** 0.5
        if distance > 64:  # Attack range
            self.ui.add_chat_message("Target is too far away!")
            return
        
        # If attacking a monster or NPC, use server interaction
        if target.type in [EntityType.MONSTER, EntityType.NPC]:
            self._attack_world_entity(target)
        else:
            # For players, use existing system (though this could also be server-side)
            if self.local_player.attack(target):
                self.ui.add_chat_message(f"Attacking {target.name}!")
    
    def _attack_world_entity(self, target: Entity):
        """Attack a world entity (monster/NPC) via server"""
        try:
            if hasattr(self.game, 'auth_token') and self.game.auth_token:
                print(f"🗡️ Attacking {target.name} (ID: {target.id}) via server...")
                
                # Send attack request to server
                response = world_client.interact_with_entity(
                    entity_id=target.id,
                    interaction_type="attack",
                    parameters={
                        "player_attack": str(self.local_player.stats.attack),
                        "player_level": str(self.local_player.stats.level)
                    }
                )
                
                if response.success:
                    self.ui.add_chat_message(f"⚔️ {response.message}")
                    
                    # Update affected entities
                    for entity_data in response.affected_entities:
                        self._update_entity_from_server_data(entity_data)
                    
                    # Process rewards (XP, items, etc.)
                    if response.rewards:
                        for reward_type, reward_value in response.rewards.items():
                            if reward_type == "experience":
                                exp_gained = int(reward_value)
                                self.local_player.stats.experience += exp_gained
                                self.ui.add_chat_message(f"✨ Gained {exp_gained} experience!")
                                self._check_level_up()
                                self._sync_player_stats_to_server()
                            elif reward_type == "gold":
                                gold_gained = int(reward_value)
                                self.ui.add_chat_message(f"💰 Gained {gold_gained} gold!")
                else:
                    self.ui.add_chat_message(f"❌ {response.message}")
                    
        except Exception as e:
            print(f"❌ Error attacking entity: {e}")
            self.ui.add_chat_message("⚠️ Attack failed - server error")
    
    def _update_entity_from_server_data(self, entity_data):
        """Update a local entity with data from server"""
        entity = self.entity_manager.get_entity(entity_data.id)
        if entity:
            # Update position
            entity.x = entity_data.position_x
            entity.y = entity_data.position_y
            
            # Update stats for monsters
            if entity.type == EntityType.MONSTER:
                entity.stats.hp = entity_data.current_hp
                entity.stats.max_hp = entity_data.max_hp
                entity.stats.mp = entity_data.current_mp
                entity.stats.max_mp = entity_data.max_mp
                entity.facing_direction = entity_data.facing_direction
                entity.movement_state = MovementState(entity_data.movement_state) if entity_data.movement_state else MovementState.IDLE
                
                # If entity died, show death message and remove it
                if not entity_data.is_alive and entity.stats.hp <= 0:
                    self.ui.add_chat_message(f"💀 {entity.name} has been defeated!")
                    # Entity will be removed in next world update
            
            print(f"🔄 Updated {entity.name}: HP {entity.stats.hp}/{entity.stats.max_hp}")
        else:
            print(f"⚠️ Entity {entity_data.id} not found locally")
    
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
            return False
        
        try:
            response = grpc_client.update_player_stats(
                self.game.auth_token,
                level=self.local_player.stats.level,
                experience=self.local_player.stats.experience,
                hp=self.local_player.stats.hp,
                mp=self.local_player.stats.mp
            )
            
            if response and response.success:
                print(f"📊 Stats synced to server: Level {self.local_player.stats.level}, EXP {self.local_player.stats.experience}, HP {self.local_player.stats.hp}/{self.local_player.stats.max_hp}")
                return True
            else:
                error_msg = response.message if response else "No response from server"
                print(f"❌ Stats update failed: {error_msg}")
                self.ui.add_chat_message(f"⚠️ Stats sync failed: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing stats to server: {e}")
            self.ui.add_chat_message(f"⚠️ Stats sync error: {str(e)}")
            return False
    
    def _sync_player_position_to_server(self):
        """Sync current player position and state to server"""
        if not self.local_player or not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return False
        
        try:
            # Send position and all relevant state info
            response = grpc_client.update_player_position(
                self.game.auth_token,
                position_x=self.local_player.x,
                position_y=self.local_player.y,
                facing_direction=self.local_player.facing_direction,
                movement_state=self.local_player.movement_state
            )
            
            if response and response.success:
                print(f"📍 Position synced to server: ({self.local_player.x:.0f}, {self.local_player.y:.0f}), facing={self.local_player.facing_direction}, state={self.local_player.movement_state}")
                return True
            else:
                error_msg = response.message if response else "No response from server"
                print(f"❌ Position update failed: {error_msg}")
                self.ui.add_chat_message(f"⚠️ Position sync failed: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing position to server: {e}")
            self.ui.add_chat_message(f"⚠️ Position sync error: {str(e)}")
            return False
    
    def _sync_all_player_data_to_server(self):
        """Sync all player data to server (comprehensive sync)"""
        if not self.local_player or not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return False
        
        try:
            # Sync stats and position separately and check results
            stats_success = self._sync_player_stats_to_server()
            position_success = self._sync_player_position_to_server()
            
            if stats_success and position_success:
                print(f"🔄 Complete player data synced to server successfully")
                return True
            else:
                failed_items = []
                if not stats_success:
                    failed_items.append("stats")
                if not position_success:
                    failed_items.append("position")
                
                print(f"⚠️ Partial sync failure: {', '.join(failed_items)} failed")
                self.ui.add_chat_message(f"⚠️ Sync incomplete: {', '.join(failed_items)} failed")
                return False
                
        except Exception as e:
            print(f"❌ Error syncing all player data to server: {e}")
            self.ui.add_chat_message(f"⚠️ Complete sync error: {str(e)}")
            return False
    
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
    
    def _toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        try:
            # Get current display info
            current_flags = pygame.display.get_surface().get_flags()
            
            if current_flags & pygame.FULLSCREEN:
                # Currently fullscreen, switch to windowed
                pygame.display.set_mode((self.game.screen_width, self.game.screen_height))
                self.ui.add_chat_message("🖼️ Switched to windowed mode")
                print("🖼️ Switched to windowed mode")
            else:
                # Currently windowed, switch to fullscreen
                # Get the native screen resolution
                info = pygame.display.Info()
                pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
                self.ui.add_chat_message("🖥️ Switched to fullscreen mode")
                print(f"🖥️ Switched to fullscreen mode ({info.current_w}x{info.current_h})")
                
        except Exception as e:
            self.ui.add_chat_message(f"❌ Failed to toggle fullscreen: {str(e)}")
            print(f"❌ Error toggling fullscreen: {e}")
    
    def update(self, dt: float = 0):
        """Update game state"""
        # Join world once when auth token is available
        if not self.world_joined and hasattr(self.game, 'auth_token') and self.game.auth_token:
            self._join_world_on_server()
            self.world_joined = True

        # Process world updates from streaming thread
        self._process_world_updates_queue()
        
        # Process world entity updates from streaming thread
        self._process_world_entity_updates()
        
        # Handle continuous movement (check pressed keys)
        self._handle_continuous_movement()
        
        # Update camera
        self.camera.update(dt)
        
        # Update all entities
        self.entity_manager.update_all(dt, self.game_map)
        
        # Auto-sync player data to server periodically
        current_time = time.time()
        if current_time - self.last_auto_sync > self.auto_sync_interval:
            if self.local_player and hasattr(self.game, 'auth_token') and self.game.auth_token:
                sync_success = self._sync_all_player_data_to_server()
                if sync_success:
                    self.ui.add_chat_message("🔄 Auto-sync: Player data saved to server")
                else:
                    self.ui.add_chat_message("⚠️ Auto-sync: Some data failed to save")
                print(f"🕐 Auto-sync triggered: {current_time:.1f} - Success: {sync_success}")
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
    
    def _handle_continuous_movement(self):
        """Handle continuous movement while keys are held down"""
        if not self.local_player:
            return
            
        # Get currently pressed keys
        keys = pygame.key.get_pressed()
        
        # Check for movement keys
        dx, dy = 0, 0
        
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -1
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = 1
            
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -1
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 1
        
        # Only move if a direction key is pressed
        if dx != 0 or dy != 0:
            # Calculate movement distance
            move_distance = 32  # pixels per move
            
            # Calculate new position
            new_x = self.local_player.x + (dx * move_distance)
            new_y = self.local_player.y + (dy * move_distance)
            
            # Determine movement type (check for shift for running)
            movement_type = "run" if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else "walk"
            
            # Add a small delay between movements to make it controllable
            current_time = time.time()
            if not hasattr(self, 'last_continuous_move') or current_time - self.last_continuous_move > 0.15:
                self.last_continuous_move = current_time
                self._process_movement(new_x, new_y, movement_type)
    
    def draw(self, screen: pygame.Surface):
        """Draw the game world"""
        # Get the current screen size
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        
        # If in fullscreen mode with different resolution than base
        if screen_width != self.game.screen_width or screen_height != self.game.screen_height:
            # Calculate integer scaling factors for crisp pixel art
            scale_x = screen_width // self.game.screen_width
            scale_y = screen_height // self.game.screen_height
            scale = max(1, min(scale_x, scale_y))  # Use integer scaling, minimum 1
            
            # If no good integer scale, fall back to smooth scaling
            if scale == 1 and (screen_width > self.game.screen_width or screen_height > self.game.screen_height):
                scale_x = screen_width / self.game.screen_width
                scale_y = screen_height / self.game.screen_height
                scale = min(scale_x, scale_y)
                use_smooth_scaling = True
            else:
                use_smooth_scaling = False
            
            # Calculate centered position for scaled content
            scaled_width = int(self.game.screen_width * scale)
            scaled_height = int(self.game.screen_height * scale)
            offset_x = (screen_width - scaled_width) // 2
            offset_y = (screen_height - scaled_height) // 2
            
            # Clear screen with black background
            screen.fill((0, 0, 0))
            
            # Create a temporary surface with our base resolution
            temp_surface = pygame.Surface((self.game.screen_width, self.game.screen_height))
            
            # Draw everything on the temporary surface
            temp_surface.fill((20, 20, 40))
            
            # Draw map
            self.game_map.draw(temp_surface, self.camera.x, self.camera.y, 
                              self.game.screen_width, self.game.screen_height)
            
            # Draw entities
            self.entity_manager.draw_all(temp_surface, self.camera.x, self.camera.y)
            
            # Draw UI
            self.ui.draw(temp_surface, self.local_player, 16)
            
            # Scale with appropriate method
            if use_smooth_scaling:
                # Use smoothscale for non-integer scaling
                scaled_surface = pygame.transform.smoothscale(temp_surface, (scaled_width, scaled_height))
            else:
                # Use regular scale for integer scaling (crisp pixels)
                scaled_surface = pygame.transform.scale(temp_surface, (scaled_width, scaled_height))
            
            screen.blit(scaled_surface, (offset_x, offset_y))
        else:
            # Normal windowed mode, draw directly
            screen.fill((20, 20, 40))
            
            # Draw map
            self.game_map.draw(screen, self.camera.x, self.camera.y, 
                              self.game.screen_width, self.game.screen_height)
            
            # Draw entities
            self.entity_manager.draw_all(screen, self.camera.x, self.camera.y)
            
            # Draw UI
            self.ui.draw(screen, self.local_player, 16)
    
    def _join_world_on_server(self):
        """Join the world on the server"""
        print("🔍 DEBUG: _join_world_on_server called")
        try:
            if hasattr(self.game, 'auth_token') and self.game.auth_token:
                print(f"🔍 DEBUG: Auth token exists, calling join_world...")
                
                # Get the player ID from selected character
                player_id = None
                if hasattr(self.game, 'selected_character') and self.game.selected_character:
                    player_id = self.game.selected_character.get('id')
                    print(f"🔍 DEBUG: Using player_id: {player_id}")
                else:
                    print("🔍 DEBUG: No selected character found, using default")
                
                response = grpc_client.join_world(self.game.auth_token, player_id=player_id)
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

                        # Sincronizar inventário
                        if hasattr(response.player, 'inventory'):
                            self.local_player.inventory = list(response.player.inventory)
                        else:
                            self.local_player.inventory = []

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
                    
                    # Start world entity updates stream for real-time world state
                    self._start_world_entity_updates_stream()
                    
                    # Load world entities after successfully joining world
                    self._load_world_entities()
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
                if response and response.success:
                    self.ui.add_chat_message(f"🚀 Server: {response.message}")
                    # Only sync position after successful movement
                    self._sync_player_position_to_server()
                else:
                    error_msg = response.message if response else "Unknown error"
                    self.ui.add_chat_message(f"❌ Move failed: {error_msg}")
                    print(f"❌ Movement failed: {error_msg}")
            else:
                self.ui.add_chat_message("❌ No authentication token for movement")
                print("❌ No auth token available for movement")
        except Exception as e:
            self.ui.add_chat_message(f"❌ Movement error: {str(e)}")
            print(f"❌ Error moving player: {e}")

    def reset(self):
        """Reset game state when entering"""
        # Could reload from save or reset to initial state
        pass
    
    def _add_other_players(self, other_players):
        """Add other players as entities to the game world"""
        if not self.local_player:
            return
            
        for player_info in other_players:
            # Skip if this is the local player (compare by name since IDs are different)
            if (player_info.is_online and 
                player_info.name != self.local_player.name):
                
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
                    print(f"🔄 Updated remote player: {player_info.name}")
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
            else:
                print(f"🚫 Skipping local player: {player_info.name} (local: {self.local_player.name})")
    
    def _start_world_updates_stream(self):
        """Start receiving real-time world updates from server"""
        if not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
            
        try:
            # Set flag to start thread
            self.world_updates_running = True
            
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
            
            while self.world_updates_running:
                try:
                    # Check if we should still be running
                    if not self.world_updates_running:
                        break
                    
                    # Poll for world state every 100ms (10 FPS)
                    world_state = grpc_client.get_world_state(self.game.auth_token)
                    
                    if world_state and world_state.players:
                        print(f"🌍 Received world state with {len(world_state.players)} players")
                        self._update_remote_players(world_state.players)
                    else:
                        print(f"🌍 Received empty world state")
                        # Clear all remote players if no players in world state
                        self._clear_all_remote_players()
                    
                    # Wait 100ms before next poll
                    time.sleep(0.1)
                    
                except Exception as e:
                    if self.world_updates_running:  # Only log if we're supposed to be running
                        print(f"❌ Error polling world state: {e}")
                    time.sleep(1)  # Wait longer if there's an error
                    
            print("🔄 World updates polling stopped")
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
        
        # Get current remote player entities for cleanup
        current_remote_players = set()
        for entity_id in list(self.entity_manager.entities.keys()):
            if entity_id.startswith("player_") and entity_id != self.local_player.id:
                current_remote_players.add(entity_id)
        
        # Track which players are still online
        still_online = set()
            
        for player_info in players:
            entity_id = f"player_{player_info.id}"
            
            # Skip if this is the local player (compare by name since IDs are different)
            if player_info.name == self.local_player.name:
                continue
            
            if player_info.is_online:
                # Player is online - add to still_online set
                still_online.add(entity_id)
                
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
            else:
                # Player is offline - should be removed
                if entity_id in current_remote_players:
                    self.entity_manager.remove_entity(entity_id)
                    print(f"🚪 Removed offline player {player_info.name}")
        
        # Remove any players that are no longer in the server's player list
        for entity_id in current_remote_players:
            if entity_id not in still_online:
                entity = self.entity_manager.get_entity(entity_id)
                if entity:
                    self.entity_manager.remove_entity(entity_id)
                    print(f"🗑️ Removed disconnected player {entity.name} ({entity_id})")
    
    def _clear_all_remote_players(self):
        """Clear all remote players from the world"""
        remote_player_ids = []
        
        for entity_id, entity in self.entity_manager.entities.items():
            # Remove entities that are remote players (other players, not local)
            if (entity.type == EntityType.PLAYER and 
                entity_id != self.local_player.id and 
                entity_id.startswith("player_")):
                remote_player_ids.append(entity_id)
        
        for entity_id in remote_player_ids:
            entity = self.entity_manager.get_entity(entity_id)
            if entity:
                self.entity_manager.remove_entity(entity_id)
                print(f"🧹 Cleared remote player: {entity.name}")
    
    def _start_world_entity_updates_stream(self):
        """Start receiving real-time world entity updates from server"""
        if not hasattr(self.game, 'auth_token') or not self.game.auth_token:
            return
            
        try:
            # Set flag to start thread
            self.world_entity_updates_running = True
            
            # Start world entity updates in a separate thread
            threading.Thread(target=self._world_entity_updates_worker, daemon=True).start()
            print("🌍 Started world entity updates stream")
        except Exception as e:
            print(f"❌ Failed to start world entity updates: {e}")
    
    def _world_entity_updates_worker(self):
        """Worker thread for world entity updates streaming"""
        try:
            print("🌍 Starting world entity updates stream...")
            
            # Get the stream from server
            stream = world_client.get_world_updates_stream()
            
            for update in stream:
                # Check if we should still be running
                if not self.world_entity_updates_running:
                    break
                
                # Put update in queue for main thread processing
                self.world_entity_updates_queue.put(update)
                
        except Exception as e:
            print(f"❌ World entity updates stream error: {e}")
        finally:
            print("🌍 World entity updates stream ended")
    
    def _process_world_entity_updates(self):
        """Process world entity updates from the queue (called from main thread)"""
        try:
            while not self.world_entity_updates_queue.empty():
                update = self.world_entity_updates_queue.get_nowait()
                
                # Process updated entities
                for entity_data in update.updated_entities:
                    existing_entity = self.entity_manager.get_entity(entity_data.id)
                    
                    if existing_entity:
                        # Update existing entity
                        self._update_entity_from_server_data(entity_data)
                    else:
                        # Add new entity
                        new_entity = self._create_entity_from_server_data(entity_data)
                        self.entity_manager.add_entity(new_entity)
                        print(f"➕ Added new entity: {new_entity.name}")
                
                # Process removed entities
                for removed_id in update.removed_entity_ids:
                    entity = self.entity_manager.get_entity(removed_id)
                    if entity:
                        self.entity_manager.remove_entity(removed_id)
                        print(f"➖ Removed entity: {entity.name}")
                
        except queue.Empty:
            pass
        except Exception as e:
            print(f"❌ Error processing world entity updates: {e}")
    
    def _stop_all_updates(self):
        """Stop all update streams"""
        self.world_updates_running = False
        self.world_entity_updates_running = False
        print("🛑 All update streams stopped")
