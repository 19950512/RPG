import pygame
from .ui_components import InputBox, Button
from ..grpc_client import grpc_client

class CreateAccountScreen:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 28)
        self.message = ""
        self.message_color = (255, 255, 255)
        self.message_time = 0

        center_x = self.game.screen_width // 2
        self.email_box = InputBox(center_x - 150, 200, 300, 40, 'Email')
        self.password_box = InputBox(center_x - 150, 260, 300, 40, 'Password', is_password=True)
        self.confirm_password_box = InputBox(center_x - 150, 320, 300, 40, 'Confirm Password', is_password=True)
        self.create_button = Button(center_x - 150, 380, 300, 50, 'Create Account')
        self.back_button = Button(center_x - 150, 440, 300, 50, 'Back to Login')
        self.input_boxes = [self.email_box, self.password_box, self.confirm_password_box]

    def handle_events(self, event):
        for box in self.input_boxes:
            box.handle_event(event)

        if self.create_button.is_clicked(event):
            self.attempt_create_account()

        if self.back_button.is_clicked(event):
            self.game.switch_state("login")

    def attempt_create_account(self):
        email = self.email_box.text
        password = self.password_box.text
        confirm_password = self.confirm_password_box.text

        if password != confirm_password:
            self.show_message("Passwords do not match!", "error")
            return

        try:
            response = grpc_client.create_account(email, password)
            if response.success:
                self.show_message("Account created! Please login.", "success")
            else:
                self.show_message(response.message, "error")
        except Exception as e:
            self.show_message("Failed to connect to server.", "error")
            print(f"Error creating account: {e}")

    def show_message(self, text, msg_type="info"):
        self.message = text
        self.message_time = pygame.time.get_ticks()
        if msg_type == "error":
            self.message_color = (255, 80, 80)
        else:
            self.message_color = (80, 255, 80)

    def update(self, dt=0):
        for box in self.input_boxes:
            box.update(dt)
        if self.message and pygame.time.get_ticks() - self.message_time > 5000: # 5 seconds
            self.message = ""

    def draw(self, screen):
        title_surf = self.font.render("Create Account", True, (255, 255, 255))
        screen.blit(title_surf, (self.game.screen_width // 2 - title_surf.get_width() // 2, 100))

        for box in self.input_boxes:
            box.draw(screen)
        self.create_button.draw(screen)
        self.back_button.draw(screen)

        if self.message:
            msg_surf = self.small_font.render(self.message, True, self.message_color)
            screen.blit(msg_surf, (self.game.screen_width // 2 - msg_surf.get_width() // 2, 500))

    def reset(self):
        for box in self.input_boxes:
            box.text = ''
        self.message = ''
