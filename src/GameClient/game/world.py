import pygame
import json
import math
from enum import Enum
from typing import Dict, List, Tuple, Optional

class TileType(Enum):
    GRASS = 0
    STONE = 1
    WATER = 2
    TREE = 3
    WALL = 4
    DOOR = 5

class Tile:
    def __init__(self, tile_type: TileType, walkable: bool = True):
        self.type = tile_type
        self.walkable = walkable
        self.color = self._get_color()
    
    def _get_color(self):
        colors = {
            TileType.GRASS: (34, 139, 34),   # Forest Green
            TileType.STONE: (128, 128, 128), # Gray
            TileType.WATER: (0, 100, 200),   # Blue
            TileType.TREE: (0, 100, 0),      # Dark Green
            TileType.WALL: (101, 67, 33),    # Brown
            TileType.DOOR: (139, 69, 19)     # Saddle Brown
        }
        return colors.get(self.type, (255, 255, 255))

class GameMap:
    def __init__(self, width: int, height: int, tile_size: int = 32):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tiles = []
        self.spawn_points = []
        self.npc_positions = []
        self.monster_spawns = []
        
        self._generate_basic_map()
    
    def _generate_basic_map(self):
        """Generate a basic town map with surrounding wilderness"""
        self.tiles = []
        
        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Create a town in the center
                if 20 <= x <= 40 and 15 <= y <= 35:
                    # Town area - stone paths
                    if (x % 3 == 0 or y % 3 == 0):
                        row.append(Tile(TileType.STONE, True))
                    else:
                        row.append(Tile(TileType.GRASS, True))
                    
                    # Add some buildings (walls)
                    if (25 <= x <= 30 and y == 20) or (25 <= x <= 30 and y == 25):
                        row[-1] = Tile(TileType.WALL, False)
                    elif x == 25 and 20 <= y <= 25:
                        row[-1] = Tile(TileType.WALL, False)
                    elif x == 30 and 20 <= y <= 25:
                        row[-1] = Tile(TileType.WALL, False)
                    
                    # Add door
                    if x == 27 and y == 20:
                        row[-1] = Tile(TileType.DOOR, True)
                
                # Water areas
                elif 5 <= x <= 15 and 40 <= y <= 50:
                    row.append(Tile(TileType.WATER, False))
                
                # Forest areas
                elif (x < 10 or x > 50 or y < 10 or y > 45) and (x + y) % 4 == 0:
                    row.append(Tile(TileType.TREE, False))
                
                # Default grass
                else:
                    row.append(Tile(TileType.GRASS, True))
            
            self.tiles.append(row)
        
        # Set spawn points
        self.spawn_points = [
            (30, 22),  # Town center
            (15, 15),  # Forest edge
            (45, 30)   # Plains
        ]
        
        # NPC positions
        self.npc_positions = [
            (28, 22, "Merchant"),
            (32, 28, "Guard"),
            (18, 18, "Villager")
        ]
        
        # Monster spawn areas
        self.monster_spawns = [
            (8, 8, "Wolf"),
            (52, 10, "Orc"),
            (10, 45, "Skeleton")
        ]
    
    def is_walkable(self, x: int, y: int) -> bool:
        """Check if a position is walkable"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x].walkable
        return False
    
    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """Get tile at position"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None
    
    def world_to_tile(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """Convert world coordinates to tile coordinates"""
        return int(world_x // self.tile_size), int(world_y // self.tile_size)
    
    def tile_to_world(self, tile_x: int, tile_y: int) -> Tuple[float, float]:
        """Convert tile coordinates to world coordinates"""
        return tile_x * self.tile_size, tile_y * self.tile_size
    
    def draw(self, screen: pygame.Surface, camera_x: float, camera_y: float, screen_width: int, screen_height: int):
        """Draw the visible portion of the map"""
        # Calculate visible tile range
        start_x = max(0, int(camera_x // self.tile_size))
        start_y = max(0, int(camera_y // self.tile_size))
        end_x = min(self.width, int((camera_x + screen_width) // self.tile_size) + 1)
        end_y = min(self.height, int((camera_y + screen_height) // self.tile_size) + 1)
        
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.tiles[y][x]
                screen_x = x * self.tile_size - camera_x
                screen_y = y * self.tile_size - camera_y
                
                rect = pygame.Rect(screen_x, screen_y, self.tile_size, self.tile_size)
                pygame.draw.rect(screen, tile.color, rect)
                
                # Draw tile border for clarity
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
    
    def save_to_file(self, filename: str):
        """Save map to JSON file"""
        map_data = {
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "tiles": [[tile.type.value for tile in row] for row in self.tiles],
            "spawn_points": self.spawn_points,
            "npc_positions": self.npc_positions,
            "monster_spawns": self.monster_spawns
        }
        
        with open(filename, 'w') as f:
            json.dump(map_data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str):
        """Load map from JSON file"""
        with open(filename, 'r') as f:
            map_data = json.load(f)
        
        game_map = cls(map_data["width"], map_data["height"], map_data["tile_size"])
        
        # Recreate tiles
        game_map.tiles = []
        for y, row in enumerate(map_data["tiles"]):
            tile_row = []
            for x, tile_type_value in enumerate(row):
                tile_type = TileType(tile_type_value)
                walkable = tile_type not in [TileType.WATER, TileType.TREE, TileType.WALL]
                tile_row.append(Tile(tile_type, walkable))
            game_map.tiles.append(tile_row)
        
        game_map.spawn_points = map_data["spawn_points"]
        game_map.npc_positions = map_data["npc_positions"]
        game_map.monster_spawns = map_data["monster_spawns"]
        
        return game_map
