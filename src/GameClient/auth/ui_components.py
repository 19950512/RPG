import pygame

class Button:
    def __init__(self, x, y, width, height, text, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, font_size)
        self.color = (70, 70, 100)
        self.hover_color = (90, 90, 120)
        self.text_color = (255, 255, 255)
        self.is_hovered = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        
    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                return self.rect.collidepoint(event.pos)
        return False

    def draw(self, screen):
        color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2)
        
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

class InputField:
    def __init__(self, x, y, width, height, placeholder="", font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.placeholder = placeholder
        self.text = ""
        self.font = pygame.font.Font(None, font_size)
        self.active = False
        self.cursor_pos = 0
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif event.key == pygame.K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
            elif event.key == pygame.K_RIGHT:
                if self.cursor_pos < len(self.text):
                    self.cursor_pos += 1
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.unicode.isprintable():
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1

    def update(self, dt):
        if self.active:
            self.cursor_timer += dt
            if self.cursor_timer >= 500:  # Blink every 500ms
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0

    def draw(self, screen):
        # Background
        color = (60, 60, 80) if self.active else (40, 40, 60)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255) if self.active else (150, 150, 150), self.rect, 2)
        
        # Text
        display_text = self.text if self.text else self.placeholder
        text_color = (255, 255, 255) if self.text else (150, 150, 150)
        
        text_surface = self.font.render(display_text, True, text_color)
        text_x = self.rect.x + 5
        text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        screen.blit(text_surface, (text_x, text_y))
        
        # Cursor
        if self.active and self.cursor_visible and self.text:
            cursor_x = text_x + self.font.size(self.text[:self.cursor_pos])[0]
            cursor_y = text_y
            cursor_height = text_surface.get_height()
            pygame.draw.line(screen, (255, 255, 255), 
                           (cursor_x, cursor_y), 
                           (cursor_x, cursor_y + cursor_height), 2)

    def get_text(self):
        return self.text
        
    def set_text(self, text):
        self.text = text
        self.cursor_pos = len(text)
        
    def clear(self):
        self.text = ""
        self.cursor_pos = 0

# Alias para compatibilidade
class InputBox(InputField):
    def __init__(self, x, y, width, height, placeholder="", is_password=False, font_size=24):
        super().__init__(x, y, width, height, placeholder, font_size)
        self.is_password = is_password
        
    def draw(self, screen):
        # Background
        color = (60, 60, 80) if self.active else (40, 40, 60)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (255, 255, 255) if self.active else (150, 150, 150), self.rect, 2)
        
        # Text (masked if password)
        if self.text:
            display_text = "*" * len(self.text) if self.is_password else self.text
            text_color = (255, 255, 255)
        else:
            display_text = self.placeholder
            text_color = (150, 150, 150)
        
        text_surface = self.font.render(display_text, True, text_color)
        text_x = self.rect.x + 5
        text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
        screen.blit(text_surface, (text_x, text_y))
        
        # Cursor
        if self.active and self.cursor_visible and self.text:
            if self.is_password:
                cursor_x = text_x + self.font.size("*" * self.cursor_pos)[0]
            else:
                cursor_x = text_x + self.font.size(self.text[:self.cursor_pos])[0]
            cursor_y = text_y
            cursor_height = text_surface.get_height()
            pygame.draw.line(screen, (255, 255, 255), 
                           (cursor_x, cursor_y), 
                           (cursor_x, cursor_y + cursor_height), 2)
