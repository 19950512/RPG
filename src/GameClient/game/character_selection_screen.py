import pygame
from ..auth.ui_components import Button
from ..grpc_client import grpc_client

class CharacterSelectionScreen:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 48)
        self.char_font = pygame.font.Font(None, 36)
        self.characters = []
        self.error_message = ""
        self.selected_character_index = None

        self.create_button = Button(550, 500, 200, 50, 'Create New')
        self.play_button = Button(300, 500, 200, 50, 'Play')
        self.logout_button = Button(50, 500, 200, 50, 'Logout')

    def fetch_characters(self):
        self.error_message = ""
        self.characters = []
        try:
            response = grpc_client.get_players(self.game.auth_token)
            if response.players:
                self.characters = list(response.players)
                print(f"Loaded {len(self.characters)} characters")
            else:
                self.error_message = "No characters found. Create one!"
                print("No characters found for this account")
        except Exception as e:
            print(f"Error fetching characters: {e}")
            self.error_message = "Failed to fetch characters."
            # Potentially handle token expiration by switching to login
            # self.game.switch_state("login")

    def handle_events(self, event):
        if self.create_button.is_clicked(event):
            print("Switching to create character screen...")
            self.game.switch_state("create_char")

        if self.logout_button.is_clicked(event):
            self.game.auth_token = None
            self.game.switch_state("login")

        if self.play_button.is_clicked(event) and self.selected_character_index is not None:
            selected_char = self.characters[self.selected_character_index]
            print(f"Entering game with {selected_char.name}...")
            print(f"🔍 DEBUG: Auth token in char_select: {self.game.auth_token}")
            self.game.selected_character = {
                'name': selected_char.name,
                'level': selected_char.level,
                'vocation': selected_char.vocation
            }
            # Maintain the auth token when switching to game
            self.game.switch_state("in_game", token=self.game.auth_token)

        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, char in enumerate(self.characters):
                char_rect = pygame.Rect(100, 150 + i * 60, 600, 50)
                if char_rect.collidepoint(event.pos):
                    self.selected_character_index = i

    def update(self):
        pass # Nothing to update continuously for now

    def draw(self, screen):
        title_surf = self.font.render("Select Your Character", True, (255, 255, 255))
        screen.blit(title_surf, (self.game.screen_width // 2 - title_surf.get_width() // 2, 50))

        for i, char in enumerate(self.characters):
            color = (200, 200, 200)
            if i == self.selected_character_index:
                color = (255, 255, 100) # Highlight selected
            
            char_text = f"{char.name} - Level {char.level} {char.vocation}"
            char_surf = self.char_font.render(char_text, True, color)
            char_rect = pygame.Rect(100, 150 + i * 60, 600, 50)
            pygame.draw.rect(screen, (40, 40, 60), char_rect)
            if i == self.selected_character_index:
                pygame.draw.rect(screen, (255, 255, 100), char_rect, 2)

            screen.blit(char_surf, (char_rect.x + 15, char_rect.y + 10))

        if self.error_message:
            error_surf = self.char_font.render(self.error_message, True, (255, 80, 80))
            screen.blit(error_surf, (self.game.screen_width // 2 - error_surf.get_width() // 2, 450))

        self.create_button.draw(screen)
        self.play_button.draw(screen)
        self.logout_button.draw(screen)

    def reset(self):
        self.selected_character_index = None
        self.fetch_characters()
