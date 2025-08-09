import pygame
import math
import time
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

class EntityType(Enum):
    PLAYER = "player"
    NPC = "npc"
    MONSTER = "monster"
    ITEM = "item"

class MovementState(Enum):
    IDLE = "idle"
    WALKING = "walking"
    RUNNING = "running"
    ATTACKING = "attacking"
    DEAD = "dead"

@dataclass
class Stats:
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    level: int
    experience: int
    attack: int
    defense: int
    speed: float

class Entity:
    def __init__(self, entity_id: str, entity_type: EntityType, x: float, y: float, name: str = ""):
        self.id = entity_id
        self.type = entity_type
        self.name = name
        
        # Position and movement
        self.x = x
        self.y = y
        self.target_x = x
        self.target_y = y
        self.movement_state = MovementState.IDLE
        self.facing_direction = 0  # 0=down, 1=left, 2=up, 3=right
        
        # Visual properties
        self.width = 24
        self.height = 24
        self.color = self._get_default_color()
        
        # Game stats
        self.stats = Stats(100, 100, 50, 50, 1, 0, 10, 5, 100.0)
        
        # Inventário do jogador (lista de strings)
        self.inventory = []

        # State
        self.last_update = time.time()
        self.is_selected = False
        self.in_combat = False

        # Network sync
        self.last_sync = time.time()
        self.needs_sync = False
    
    def _get_default_color(self):
        colors = {
            EntityType.PLAYER: (0, 120, 255),    # Blue
            EntityType.NPC: (0, 200, 0),         # Green
            EntityType.MONSTER: (200, 0, 0),     # Red
            EntityType.ITEM: (255, 255, 0)       # Yellow
        }
        return colors.get(self.type, (255, 255, 255))
    
    def update(self, dt: float, game_map):
        """Update entity state"""
        current_time = time.time()
        
        # Handle movement
        if self.movement_state in [MovementState.WALKING, MovementState.RUNNING]:
            self._update_movement(dt, game_map)
        
        # Check if sync is needed
        if current_time - self.last_sync > 0.1:  # Sync every 100ms
            self.needs_sync = True
            self.last_sync = current_time
        
        self.last_update = current_time
    
    def _update_movement(self, dt: float, game_map):
        """Update movement towards target"""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < 2:  # Close enough to target
            self.x = self.target_x
            self.y = self.target_y
            self.movement_state = MovementState.IDLE
            return
        
        # Calculate movement speed
        speed_multiplier = 2.0 if self.movement_state == MovementState.RUNNING else 1.0
        movement_speed = self.stats.speed * speed_multiplier * (dt / 1000.0)
        
        # Normalize direction and apply movement
        if distance > 0:
            move_x = (dx / distance) * movement_speed
            move_y = (dy / distance) * movement_speed
            
            # Check collision for next position
            next_x = self.x + move_x
            next_y = self.y + move_y
            
            if self._can_move_to(next_x, next_y, game_map):
                self.x = next_x
                self.y = next_y
                
                # Update facing direction
                if abs(dx) > abs(dy):
                    self.facing_direction = 3 if dx > 0 else 1  # Right or Left
                else:
                    self.facing_direction = 2 if dy < 0 else 0  # Up or Down
    
    def _can_move_to(self, x: float, y: float, game_map) -> bool:
        """Check if entity can move to the given position"""
        # Check bounds
        tile_size = game_map.tile_size
        entity_margin = 8  # Pixels from edge
        
        # Check all corners of the entity
        corners = [
            (x - entity_margin, y - entity_margin),
            (x + entity_margin, y - entity_margin),
            (x - entity_margin, y + entity_margin),
            (x + entity_margin, y + entity_margin)
        ]
        
        for corner_x, corner_y in corners:
            tile_x, tile_y = game_map.world_to_tile(corner_x, corner_y)
            if not game_map.is_walkable(tile_x, tile_y):
                return False
        
        return True
    
    def set_target(self, target_x: float, target_y: float):
        """Set movement target"""
        self.target_x = target_x
        self.target_y = target_y
        if self.target_x != self.x or self.target_y != self.y:
            self.movement_state = MovementState.WALKING
            self.needs_sync = True
    
    def attack(self, target_entity):
        """Attack another entity"""
        if self.in_combat:
            return False
        
        distance = math.sqrt((self.x - target_entity.x) ** 2 + (self.y - target_entity.y) ** 2)
        if distance <= 40:  # Attack range
            self.movement_state = MovementState.ATTACKING
            damage = max(1, self.stats.attack - target_entity.stats.defense)
            target_entity.take_damage(damage)
            self.needs_sync = True
            return True
        return False
    
    def take_damage(self, damage: int):
        """Take damage"""
        self.stats.hp = max(0, self.stats.hp - damage)
        if self.stats.hp == 0:
            self.movement_state = MovementState.DEAD
        self.needs_sync = True
    
    def heal(self, amount: int):
        """Heal the entity"""
        self.stats.hp = min(self.stats.max_hp, self.stats.hp + amount)
        self.needs_sync = True
    
    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float):
        """Draw the entity"""
        screen_x = self.x - camera_x - self.width // 2
        screen_y = self.y - camera_y - self.height // 2
        
        # Don't draw if off screen
        if (screen_x + self.width < 0 or screen_x > screen.get_width() or 
            screen_y + self.height < 0 or screen_y > screen.get_height()):
            return
        
        # Draw entity body
        rect = pygame.Rect(screen_x, screen_y, self.width, self.height)
        pygame.draw.rect(screen, self.color, rect)
        
        # Draw border
        border_color = (255, 255, 0) if self.is_selected else (0, 0, 0)
        pygame.draw.rect(screen, border_color, rect, 2)
        
        # Draw facing direction indicator
        center_x = screen_x + self.width // 2
        center_y = screen_y + self.height // 2
        
        # Direction offsets for facing direction (1=Up, 2=Right, 3=Down, 4=Left)
        direction_offsets = [
            (0, 0),   # Index 0 - unused/default
            (0, -8),  # Index 1 - Up
            (8, 0),   # Index 2 - Right  
            (0, 8),   # Index 3 - Down
            (-8, 0)   # Index 4 - Left
        ]
        
        # Ensure facing_direction is within valid range
        if self.facing_direction < 0 or self.facing_direction >= len(direction_offsets):
            self.facing_direction = 3  # Default to Down
        
        offset_x, offset_y = direction_offsets[self.facing_direction]
        end_x = center_x + offset_x
        end_y = center_y + offset_y
        
        pygame.draw.line(screen, (255, 255, 255), (center_x, center_y), (end_x, end_y), 2)
        
        # Draw name
        if self.name:
            font = pygame.font.Font(None, 16)
            name_surface = font.render(self.name, True, (255, 255, 255))
            name_x = screen_x + (self.width - name_surface.get_width()) // 2
            name_y = screen_y - 20
            screen.blit(name_surface, (name_x, name_y))
        
        # Draw HP bar
        if self.stats.hp < self.stats.max_hp:
            self._draw_health_bar(screen, screen_x, screen_y - 5)
    
    def _draw_health_bar(self, screen: pygame.Surface, x: float, y: float):
        """Draw health bar above entity"""
        bar_width = self.width
        bar_height = 4
        
        # Background
        bg_rect = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (100, 0, 0), bg_rect)
        
        # Health
        health_ratio = self.stats.hp / self.stats.max_hp
        health_width = int(bar_width * health_ratio)
        if health_width > 0:
            health_rect = pygame.Rect(x, y, health_width, bar_height)
            pygame.draw.rect(screen, (0, 200, 0), health_rect)
    
    def get_sync_data(self) -> Dict:
        """Get data for network synchronization"""
        return {
            "id": self.id,
            "type": self.type.value,
            "x": self.x,
            "y": self.y,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "movement_state": self.movement_state.value,
            "facing_direction": self.facing_direction,
            "hp": self.stats.hp,
            "max_hp": self.stats.max_hp,
            "level": self.stats.level,
            "name": self.name
        }
    
    def update_from_sync_data(self, data: Dict):
        """Update entity from network sync data"""
        self.x = data.get("x", self.x)
        self.y = data.get("y", self.y)
        self.target_x = data.get("target_x", self.target_x)
        self.target_y = data.get("target_y", self.target_y)
        self.movement_state = MovementState(data.get("movement_state", self.movement_state.value))
        self.facing_direction = data.get("facing_direction", self.facing_direction)
        self.stats.hp = data.get("hp", self.stats.hp)
        self.stats.max_hp = data.get("max_hp", self.stats.max_hp)
        self.stats.level = data.get("level", self.stats.level)
        self.name = data.get("name", self.name)

class EntityManager:
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.local_player_id: Optional[str] = None
    
    def add_entity(self, entity: Entity):
        """Add entity to manager"""
        self.entities[entity.id] = entity
    
    def remove_entity(self, entity_id: str):
        """Remove entity from manager"""
        if entity_id in self.entities:
            del self.entities[entity_id]
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        return self.entities.get(entity_id)
    
    def get_local_player(self) -> Optional[Entity]:
        """Get the local player entity"""
        if self.local_player_id:
            return self.entities.get(self.local_player_id)
        return None
    
    def update_all(self, dt: float, game_map):
        """Update all entities"""
        for entity in self.entities.values():
            entity.update(dt, game_map)
    
    def draw_all(self, screen: pygame.Surface, camera_x: float, camera_y: float):
        """Draw all entities"""
        # Sort by Y position for proper layering
        sorted_entities = sorted(self.entities.values(), key=lambda e: e.y)
        
        for entity in sorted_entities:
            entity.draw(screen, camera_x, camera_y)
    
    def get_entities_in_range(self, x: float, y: float, range_distance: float) -> List[Entity]:
        """Get entities within range of a position"""
        entities_in_range = []
        for entity in self.entities.values():
            distance = math.sqrt((entity.x - x) ** 2 + (entity.y - y) ** 2)
            if distance <= range_distance:
                entities_in_range.append(entity)
        return entities_in_range
    
    def get_sync_data(self) -> List[Dict]:
        """Get sync data for all entities that need syncing"""
        sync_data = []
        for entity in self.entities.values():
            if entity.needs_sync:
                sync_data.append(entity.get_sync_data())
                entity.needs_sync = False
        return sync_data
