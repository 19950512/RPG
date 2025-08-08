import pygame
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from GameClient.auth.login_screen import LoginScreen
from GameClient.auth.create_account_screen import CreateAccountScreen
from GameClient.game.character_selection_screen import CharacterSelectionScreen
from GameClient.game.create_character_screen import CreateCharacterScreen
from GameClient.game.game_screen import GameScreen

class Game:
    def __init__(self):
        pygame.init()
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("RPG Game")
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_state = "login"  # Possible states: login, create_account, char_select, in_game
        self.auth_token = None

        self.states = {
            "login": LoginScreen(self),
            "create_account": CreateAccountScreen(self),
            "char_select": CharacterSelectionScreen(self),
            "create_char": CreateCharacterScreen(self),
            "in_game": GameScreen(self)
        }

    def run(self):
        while self.running:
            dt = self.clock.tick(60)  # Get delta time in milliseconds
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Call leave_world before quitting if player is in game
                if self.current_state == "in_game" and hasattr(self, 'auth_token') and self.auth_token:
                    try:
                        from GameClient.grpc_client import grpc_client
                        response = grpc_client.leave_world(self.auth_token)
                        if response.success:
                            print(f"🚪 Successfully left world: {response.message}")
                        else:
                            print(f"⚠️ Failed to leave world: {response.message}")
                    except Exception as e:
                        print(f"❌ Error leaving world: {e}")
                
                self.running = False
            self.states[self.current_state].handle_events(event)

    def update(self, dt):
        if hasattr(self.states[self.current_state], 'update'):
            # Check if update method accepts dt parameter
            import inspect
            sig = inspect.signature(self.states[self.current_state].update)
            if len(sig.parameters) > 0:
                self.states[self.current_state].update(dt)
            else:
                self.states[self.current_state].update()

    def draw(self):
        self.screen.fill((20, 20, 40))  # Dark blue background
        self.states[self.current_state].draw(self.screen)
        pygame.display.flip()

    def switch_state(self, new_state, token=None):
        self.current_state = new_state
        if token:
            self.auth_token = token
        # Reset state if needed
        if hasattr(self.states[self.current_state], 'reset'):
            self.states[self.current_state].reset()


if __name__ == "__main__":
    game = Game()
    game.run()
