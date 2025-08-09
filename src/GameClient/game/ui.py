import pygame
import math
from typing import Optional, Tuple
from .entities import Entity

class Camera:
    def __init__(self, screen_width: int, screen_height: int):
        self.x = 0.0
        self.y = 0.0
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.target_entity: Optional[Entity] = None
        
        # Camera smoothing
        self.smoothing = 0.1
        self.zoom = 1.0
        self.target_zoom = 1.0
        
        # Camera bounds
        self.min_x = 0
        self.min_y = 0
        self.max_x = 10000
        self.max_y = 10000
    
    def update(self, dt: float):
        """Update camera position"""
        if self.target_entity:
            # Calculate target camera position (center on entity)
            target_x = self.target_entity.x - self.screen_width // 2
            target_y = self.target_entity.y - self.screen_height // 2
            
            # Smooth camera movement
            self.x += (target_x - self.x) * self.smoothing
            self.y += (target_y - self.y) * self.smoothing
        
        # Apply camera bounds
        self.x = max(self.min_x, min(self.max_x - self.screen_width, self.x))
        self.y = max(self.min_y, min(self.max_y - self.screen_height, self.y))
        
        # Update zoom
        if abs(self.zoom - self.target_zoom) > 0.01:
            self.zoom += (self.target_zoom - self.zoom) * 0.1
    
    def set_target(self, entity: Entity):
        """Set camera target entity"""
        self.target_entity = entity
    
    def set_bounds(self, max_x: int, max_y: int):
        """Set camera bounds based on world size"""
        self.max_x = max_x
        self.max_y = max_y
    
    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates"""
        screen_x = (world_x - self.x) * self.zoom
        screen_y = (world_y - self.y) * self.zoom
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates"""
        world_x = (screen_x / self.zoom) + self.x
        world_y = (screen_y / self.zoom) + self.y
        return world_x, world_y

class UI:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # UI Elements
        self.show_debug = False
        self.show_minimap = True
        self.show_chat = True
        self.chat_messages = []
        self.chat_input = ""
        self.chat_input_active = False
        
        # UI Panels
        self.panels = {
            "inventory": False,
            "character": False,
            "quest": False,
            "settings": False
        }
        
        # Selected entity
        self.selected_entity: Optional[Entity] = None
        
        # Action buttons
        self.action_buttons = [
            {"rect": pygame.Rect(10, screen_height - 100, 80, 30), "text": "Attack", "action": "attack"},
            {"rect": pygame.Rect(100, screen_height - 100, 80, 30), "text": "Heal", "action": "heal"},
            {"rect": pygame.Rect(190, screen_height - 100, 80, 30), "text": "Run", "action": "run"},
        ]
    
    def handle_event(self, event, camera: Camera) -> Optional[str]:
        """Handle UI events, returns action if any"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.show_debug = not self.show_debug
            elif event.key == pygame.K_F2:
                self.show_minimap = not self.show_minimap
            elif event.key == pygame.K_F3:
                self.show_chat = not self.show_chat
            elif event.key == pygame.K_i:
                self.panels["inventory"] = not self.panels["inventory"]
            elif event.key == pygame.K_c:
                self.panels["character"] = not self.panels["character"]
            elif event.key == pygame.K_q:
                self.panels["quest"] = not self.panels["quest"]
            elif event.key == pygame.K_RETURN:
                if self.chat_input_active:
                    if self.chat_input.strip():
                        self.add_chat_message(f"You: {self.chat_input}")
                        action = self.chat_input
                        self.chat_input = ""
                        self.chat_input_active = False
                        return f"chat:{action}"
                else:
                    self.chat_input_active = True
            elif event.key == pygame.K_ESCAPE:
                self.chat_input_active = False
                self.chat_input = ""
                # Close all panels
                for panel in self.panels:
                    self.panels[panel] = False
            
            # Chat input
            if self.chat_input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.chat_input = self.chat_input[:-1]
                elif event.unicode.isprintable():
                    self.chat_input += event.unicode
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                # Check action buttons
                for button in self.action_buttons:
                    if button["rect"].collidepoint(event.pos):
                        return button["action"]
                
                # Check if clicking on world
                if not self._is_clicking_ui(event.pos):
                    world_x, world_y = camera.screen_to_world(event.pos[0], event.pos[1])
                    return f"click:{world_x},{world_y}"
            
            # Right click movement disabled
            # elif event.button == 3:  # Right click
            #     if not self._is_clicking_ui(event.pos):
            #         world_x, world_y = camera.screen_to_world(event.pos[0], event.pos[1])
            #         return f"move:{world_x},{world_y}"
        
        return None
    
    def _is_clicking_ui(self, pos: Tuple[int, int]) -> bool:
        """Check if click is on UI element"""
        x, y = pos
        
        # Check panels
        if self.panels["inventory"] and x > self.screen_width - 300:
            return True
        if self.panels["character"] and x < 250:
            return True
        if self.show_chat and y > self.screen_height - 150:
            return True
        
        # Check action buttons
        for button in self.action_buttons:
            if button["rect"].collidepoint(pos):
                return True
        
        return False
    
    def add_chat_message(self, message: str):
        """Add message to chat"""
        self.chat_messages.append(message)
        if len(self.chat_messages) > 10:
            self.chat_messages.pop(0)
    
    def set_selected_entity(self, entity: Optional[Entity]):
        """Set selected entity"""
        if self.selected_entity:
            self.selected_entity.is_selected = False
        
        self.selected_entity = entity
        if entity:
            entity.is_selected = True
    
    def draw(self, screen: pygame.Surface, player_entity: Optional[Entity], dt: float):
        """Draw UI elements"""
        # Draw player health bar
        if player_entity:
            self._draw_player_health(screen, player_entity)
        
        # Draw minimap
        if self.show_minimap:
            self._draw_minimap(screen)
        
        # Draw chat
        if self.show_chat:
            self._draw_chat(screen)
        
        # Draw panels
        if self.panels["inventory"]:
            self._draw_inventory_panel(screen, player_entity)
        if self.panels["character"]:
            self._draw_character_panel(screen, player_entity)
        if self.panels["quest"]:
            self._draw_quest_panel(screen)
        
        # Draw action buttons
        self._draw_action_buttons(screen)
        
        # Draw selected entity info
        if self.selected_entity:
            self._draw_entity_info(screen, self.selected_entity)
        
        # Draw debug info
        if self.show_debug:
            self._draw_debug_info(screen, player_entity, dt)
    
    def _draw_player_health(self, screen: pygame.Surface, player: Entity):
        """Draw player health and mana bars"""
        bar_width = 200
        bar_height = 20
        x = 10
        y = 10
        
        # Health bar background
        health_bg = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (100, 0, 0), health_bg)
        
        # Health bar
        health_ratio = player.stats.hp / player.stats.max_hp
        health_width = int(bar_width * health_ratio)
        health_rect = pygame.Rect(x, y, health_width, bar_height)
        pygame.draw.rect(screen, (200, 0, 0), health_rect)
        
        # Health text
        health_text = f"HP: {player.stats.hp}/{player.stats.max_hp}"
        text_surface = self.small_font.render(health_text, True, (255, 255, 255))
        screen.blit(text_surface, (x + 5, y + 2))
        
        # Mana bar
        y += 25
        mana_bg = pygame.Rect(x, y, bar_width, bar_height)
        pygame.draw.rect(screen, (0, 0, 100), mana_bg)
        
        mana_ratio = player.stats.mp / player.stats.max_mp
        mana_width = int(bar_width * mana_ratio)
        mana_rect = pygame.Rect(x, y, mana_width, bar_height)
        pygame.draw.rect(screen, (0, 0, 200), mana_rect)
        
        # Mana text
        mana_text = f"MP: {player.stats.mp}/{player.stats.max_mp}"
        text_surface = self.small_font.render(mana_text, True, (255, 255, 255))
        screen.blit(text_surface, (x + 5, y + 2))
        
        # Level and XP
        y += 25
        level_text = f"Level {player.stats.level} - XP: {player.stats.experience}"
        text_surface = self.small_font.render(level_text, True, (255, 255, 255))
        screen.blit(text_surface, (x, y))
    
    def _draw_minimap(self, screen: pygame.Surface):
        """Draw minimap"""
        map_size = 150
        x = self.screen_width - map_size - 10
        y = 10
        
        # Background
        bg_rect = pygame.Rect(x, y, map_size, map_size)
        pygame.draw.rect(screen, (0, 0, 0, 128), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)
        
        # Title
        title = self.small_font.render("Minimap", True, (255, 255, 255))
        screen.blit(title, (x + 5, y + 5))
    
    def _draw_chat(self, screen: pygame.Surface):
        """Draw chat window"""
        chat_height = 150
        chat_width = 400
        x = 10
        y = self.screen_height - chat_height - 10
        
        # Background
        bg_rect = pygame.Rect(x, y, chat_width, chat_height)
        pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)
        
        # Draw messages
        message_y = y + 5
        for message in self.chat_messages[-6:]:  # Show last 6 messages
            text_surface = self.small_font.render(message, True, (255, 255, 255))
            screen.blit(text_surface, (x + 5, message_y))
            message_y += 20
        
        # Input box
        input_y = y + chat_height - 25
        input_rect = pygame.Rect(x + 5, input_y, chat_width - 10, 20)
        color = (100, 100, 100) if self.chat_input_active else (50, 50, 50)
        pygame.draw.rect(screen, color, input_rect)
        pygame.draw.rect(screen, (255, 255, 255), input_rect, 1)
        
        # Input text
        input_text = f"> {self.chat_input}"
        if self.chat_input_active:
            input_text += "_"
        text_surface = self.small_font.render(input_text, True, (255, 255, 255))
        screen.blit(text_surface, (x + 8, input_y + 2))
    
    def _draw_action_buttons(self, screen: pygame.Surface):
        """Draw action buttons"""
        for button in self.action_buttons:
            # Button background
            pygame.draw.rect(screen, (60, 60, 80), button["rect"])
            pygame.draw.rect(screen, (255, 255, 255), button["rect"], 2)
            
            # Button text
            text_surface = self.small_font.render(button["text"], True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=button["rect"].center)
            screen.blit(text_surface, text_rect)
    
    def _draw_inventory_panel(self, screen: pygame.Surface, player: 'Entity' = None):
        """Draw inventory panel"""
        panel_width = 300
        panel_height = 400
        x = self.screen_width - panel_width - 10
        y = self.screen_height // 2 - panel_height // 2

        # Background
        bg_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(screen, (40, 40, 60), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)

        # Title
        title = self.font.render("Inventory", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))

        # Close button
        close_text = self.small_font.render("X", True, (255, 255, 255))
        screen.blit(close_text, (x + panel_width - 20, y + 5))

        # Exibir itens do inventário
        if player and hasattr(player, 'inventory'):
            inv_y = y + 50
            if not player.inventory:
                empty_text = self.small_font.render("(Inventário vazio)", True, (200, 200, 200))
                screen.blit(empty_text, (x + 20, inv_y))
            else:
                for idx, item in enumerate(player.inventory):
                    item_text = self.small_font.render(f"{idx+1}. {item}", True, (255, 255, 0))
                    screen.blit(item_text, (x + 20, inv_y))
                    inv_y += 28
    
    def _draw_character_panel(self, screen: pygame.Surface, player: Optional[Entity]):
        """Draw character panel"""
        panel_width = 250
        panel_height = 400
        x = 10
        y = self.screen_height // 2 - panel_height // 2
        
        # Background
        bg_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(screen, (40, 40, 60), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)
        
        # Title
        title = self.font.render("Character", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))
        
        if player:
            stats_y = y + 50
            stats = [
                f"Name: {player.name}",
                f"Level: {player.stats.level}",
                f"HP: {player.stats.hp}/{player.stats.max_hp}",
                f"MP: {player.stats.mp}/{player.stats.max_mp}",
                f"Attack: {player.stats.attack}",
                f"Defense: {player.stats.defense}",
                f"Speed: {player.stats.speed}",
                f"Experience: {player.stats.experience}"
            ]
            
            for stat in stats:
                text_surface = self.small_font.render(stat, True, (255, 255, 255))
                screen.blit(text_surface, (x + 10, stats_y))
                stats_y += 25
    
    def _draw_quest_panel(self, screen: pygame.Surface):
        """Draw quest panel"""
        panel_width = 350
        panel_height = 300
        x = self.screen_width // 2 - panel_width // 2
        y = 50
        
        # Background
        bg_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(screen, (40, 40, 60), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 2)
        
        # Title
        title = self.font.render("Quests", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))
        
        # Sample quest
        quest_text = self.small_font.render("• Kill 5 wolves in the forest", True, (255, 255, 255))
        screen.blit(quest_text, (x + 10, y + 50))
    
    def _draw_entity_info(self, screen: pygame.Surface, entity: Entity):
        """Draw selected entity information"""
        info_width = 200
        info_height = 100
        x = self.screen_width // 2 - info_width // 2
        y = 10
        
        # Background
        bg_rect = pygame.Rect(x, y, info_width, info_height)
        pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
        pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)
        
        # Entity info
        info_y = y + 10
        info_lines = [
            f"Name: {entity.name}",
            f"Type: {entity.type.value.title()}",
            f"Level: {entity.stats.level}",
            f"HP: {entity.stats.hp}/{entity.stats.max_hp}"
        ]
        
        for line in info_lines:
            text_surface = self.small_font.render(line, True, (255, 255, 255))
            screen.blit(text_surface, (x + 5, info_y))
            info_y += 18
    
    def _draw_debug_info(self, screen: pygame.Surface, player: Optional[Entity], dt: float):
        """Draw debug information"""
        if not player:
            return
        
        debug_lines = [
            f"FPS: {1000 / max(dt, 1):.1f}",
            f"Player Pos: ({player.x:.1f}, {player.y:.1f})",
            f"Target: ({player.target_x:.1f}, {player.target_y:.1f})",
            f"State: {player.movement_state}",
            f"Direction: {player.facing_direction}"
        ]
        
        y = 100
        for line in debug_lines:
            text_surface = self.small_font.render(line, True, (255, 255, 0))
            screen.blit(text_surface, (10, y))
            y += 20
