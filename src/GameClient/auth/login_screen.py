import pygame
from .ui_components import InputBox, Button
from ..grpc_client import grpc_client

class LoginScreen:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 28)
        self.error_message = ""
        self.error_time = 0

        center_x = self.game.screen_width // 2
        self.email_box = InputBox(center_x - 150, 200, 300, 40, 'Email')
        self.password_box = InputBox(center_x - 150, 260, 300, 40, 'Password', is_password=True)
        self.login_button = Button(center_x - 150, 320, 140, 50, 'Login')
        self.create_account_button = Button(center_x + 10, 320, 140, 50, 'Create Account')
        self.input_boxes = [self.email_box, self.password_box]

    def handle_events(self, event):
        for box in self.input_boxes:
            box.handle_event(event)

        if self.login_button.is_clicked(event):
            self.attempt_login()

        if self.create_account_button.is_clicked(event):
            self.game.switch_state("create_account")

    def attempt_login(self):
        email = self.email_box.text
        password = self.password_box.text
        try:
            response = grpc_client.login(email, password)
            if response.success:
                print(f"Login successful! Token: {response.jwt_token}")
                self.game.switch_state("char_select", token=response.jwt_token)
            else:
                self.show_error(response.message)
        except Exception as e:
            self.show_error("Failed to connect to server.")
            print(f"Error during login: {e}")

    def show_error(self, message):
        self.error_message = message
        self.error_time = pygame.time.get_ticks()

    def update(self, dt=0):
        for box in self.input_boxes:
            box.update(dt)
        if self.error_message and pygame.time.get_ticks() - self.error_time > 5000: # 5 seconds
            self.error_message = ""

    def draw(self, screen):
        title_surf = self.font.render("Game Title", True, (255, 255, 255))
        screen.blit(title_surf, (self.game.screen_width // 2 - title_surf.get_width() // 2, 100))

        for box in self.input_boxes:
            box.draw(screen)
        self.login_button.draw(screen)
        self.create_account_button.draw(screen)

        if self.error_message:
            error_surf = self.small_font.render(self.error_message, True, (255, 80, 80))
            screen.blit(error_surf, (self.game.screen_width // 2 - error_surf.get_width() // 2, 400))

    def reset(self):
        self.email_box.text = ''
        self.password_box.text = ''
        self.error_message = ''
