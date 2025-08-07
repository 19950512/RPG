import pygame
from GameClient.auth.ui_components import Button
from GameClient.grpc_client import grpc_client

class CreateCharacterScreen:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 48)
        self.label_font = pygame.font.Font(None, 32)
        self.input_font = pygame.font.Font(None, 28)
        
        # Form fields
        self.character_name = ""
        self.selected_vocation = "Knight"
        self.vocations = ["Knight", "Mage", "Paladin", "Assassin"]
        self.vocation_index = 0
        
        # UI state
        self.name_input_active = False
        self.error_message = ""
        self.success_message = ""
        
        # Buttons
        self.create_button = Button(300, 450, 200, 50, 'Create Character')
        self.back_button = Button(50, 500, 150, 50, 'Back')
        self.prev_vocation_button = Button(250, 300, 50, 40, '<')
        self.next_vocation_button = Button(500, 300, 50, 40, '>')
        
        # Input field rect
        self.name_input_rect = pygame.Rect(300, 200, 200, 40)

    def handle_events(self, event):
        # Handle name input
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.name_input_rect.collidepoint(event.pos):
                self.name_input_active = True
            else:
                self.name_input_active = False
                
        if event.type == pygame.KEYDOWN and self.name_input_active:
            if event.key == pygame.K_BACKSPACE:
                self.character_name = self.character_name[:-1]
            elif len(self.character_name) < 20:  # Limit name length
                self.character_name += event.unicode
                
        # Handle button clicks
        if self.back_button.is_clicked(event):
            self.game.switch_state("char_select")
            
        if self.prev_vocation_button.is_clicked(event):
            self.vocation_index = (self.vocation_index - 1) % len(self.vocations)
            self.selected_vocation = self.vocations[self.vocation_index]
            
        if self.next_vocation_button.is_clicked(event):
            self.vocation_index = (self.vocation_index + 1) % len(self.vocations)
            self.selected_vocation = self.vocations[self.vocation_index]
            
        if self.create_button.is_clicked(event):
            self.create_character()

    def create_character(self):
        if not self.character_name.strip():
            self.error_message = "Character name cannot be empty!"
            return
            
        if len(self.character_name.strip()) < 3:
            self.error_message = "Character name must be at least 3 characters!"
            return
            
        try:
            self.error_message = ""
            self.success_message = ""
            
            response = grpc_client.create_character(
                self.game.auth_token, 
                self.character_name.strip(), 
                self.selected_vocation
            )
            
            if response.success:
                self.success_message = f"Character '{self.character_name}' created successfully!"
                # Clear form
                self.character_name = ""
                self.vocation_index = 0
                self.selected_vocation = self.vocations[0]
                # Switch back to character selection after a brief delay
                pygame.time.set_timer(pygame.USEREVENT + 1, 2000)  # 2 seconds
            else:
                self.error_message = response.message or "Failed to create character"
                
        except Exception as e:
            print(f"Error creating character: {e}")
            self.error_message = "Failed to create character. Please try again."

    def update(self):
        # Handle delayed switch back to character selection
        for event in pygame.event.get([pygame.USEREVENT + 1]):
            if event.type == pygame.USEREVENT + 1:
                pygame.time.set_timer(pygame.USEREVENT + 1, 0)  # Stop the timer
                self.game.switch_state("char_select")

    def draw(self, screen):
        # Title
        title_text = self.font.render("Create Character", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(screen.get_width() // 2, 80))
        screen.blit(title_text, title_rect)
        
        # Character name label
        name_label = self.label_font.render("Character Name:", True, (255, 255, 255))
        screen.blit(name_label, (300, 170))
        
        # Character name input field
        color = (100, 100, 100) if self.name_input_active else (60, 60, 60)
        pygame.draw.rect(screen, color, self.name_input_rect)
        pygame.draw.rect(screen, (255, 255, 255), self.name_input_rect, 2)
        
        # Character name text
        name_text = self.input_font.render(self.character_name, True, (255, 255, 255))
        screen.blit(name_text, (self.name_input_rect.x + 5, self.name_input_rect.y + 8))
        
        # Vocation label
        vocation_label = self.label_font.render("Vocation:", True, (255, 255, 255))
        screen.blit(vocation_label, (300, 270))
        
        # Vocation selection
        vocation_text = self.label_font.render(self.selected_vocation, True, (255, 255, 0))
        vocation_rect = vocation_text.get_rect(center=(400, 320))
        screen.blit(vocation_text, vocation_rect)
        
        # Vocation description
        descriptions = {
            "Knight": "Strong melee fighter with high defense",
            "Mage": "Master of magic with powerful spells",
            "Paladin": "Ranged combatant with precision attacks",
            "Assassin": "Stealthy assassin with quick strikes"
        }
        
        desc_text = self.input_font.render(descriptions[self.selected_vocation], True, (200, 200, 200))
        desc_rect = desc_text.get_rect(center=(400, 350))
        screen.blit(desc_text, desc_rect)
        
        # Draw buttons
        self.create_button.draw(screen)
        self.back_button.draw(screen)
        self.prev_vocation_button.draw(screen)
        self.next_vocation_button.draw(screen)
        
        # Error message
        if self.error_message:
            error_text = self.input_font.render(self.error_message, True, (255, 100, 100))
            error_rect = error_text.get_rect(center=(screen.get_width() // 2, 400))
            screen.blit(error_text, error_rect)
            
        # Success message
        if self.success_message:
            success_text = self.input_font.render(self.success_message, True, (100, 255, 100))
            success_rect = success_text.get_rect(center=(screen.get_width() // 2, 400))
            screen.blit(success_text, success_rect)

    def reset(self):
        self.character_name = ""
        self.selected_vocation = "Knight"
        self.vocation_index = 0
        self.name_input_active = False
        self.error_message = ""
        self.success_message = ""
