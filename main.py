import os
import random
import sys
import pygame

from classes import BASE_DIR, asset_path, Player, Gun, Wave, Explosion

pygame.init()
pygame.font.init()

TITLE = "Glaxy Strike"
FPS = 60


def safe_load_image(path, alpha=True):
    image = pygame.image.load(path)
    return image.convert_alpha() if alpha else image.convert()


def load_font(path, size):
    try:
        return pygame.font.Font(path, size)
    except (pygame.error, OSError):
        return pygame.font.Font(None, size)


def load_highest_level():
    path = asset_path("highestLevel.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
        value = text.split("=", 1)[-1].strip()
        return max(0, int(value))
    except (OSError, ValueError):
        return 0


def save_highest_level(value):
    try:
        with open(asset_path("highestLevel.txt"), "w", encoding="utf-8") as f:
            f.write(f"highestLevel = {int(value)}")
    except OSError:
        pass


class Game:
    def __init__(self):
        self.fullscreen = True
        self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(True)
        self.icon = safe_load_image(asset_path("Images", "icon.png"))
        pygame.display.set_icon(self.icon)

        self.font = load_font(asset_path("Fonts", "Minecraft.ttf"), 48)
        self.small_font = pygame.font.Font(None, 24)
        self.medium_font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 72)
        self.screen_w, self.screen_h = self.window.get_size()

        self.menu_frames = [
            safe_load_image(asset_path("Images", "Menu", "Background", f"{i}.bmp"), False)
            for i in range(6)
        ]
        self.menu_frame = 0
        self.menu_timer = 0.0
        self.name_img = safe_load_image(asset_path("Images", "Menu", "GameName.png"))
        self.name_img = pygame.transform.smoothscale(self.name_img, (self.name_img.get_width() * 2, self.name_img.get_height() * 2))
        self.play_btn = safe_load_image(asset_path("Images", "Menu", "PlayBTN.png"))
        self.play_btn_hover = safe_load_image(asset_path("Images", "Menu", "PlayBTN_HL.png"))
        self.settings_title = safe_load_image(asset_path("Images", "Settings", "Settings.png"))
        self.quit_img = safe_load_image(asset_path("Images", "Settings", "Quit.png"))
        self.quit_hover = safe_load_image(asset_path("Images", "Settings", "Quit_HL.png"))
        self.menu_img = safe_load_image(asset_path("Images", "Settings", "MainMenu.png"))
        self.menu_img_hover = safe_load_image(asset_path("Images", "Settings", "MainMenu_HL.png"))
        self.background = safe_load_image(asset_path("Images", "Playing", "0.jpg"), False)

        self.explosion_frames = []
        for i in range(12):
            self.explosion_frames.append(safe_load_image(asset_path("Images", "Explosion", f"{i}.png")))

        self.stars = []
        self.rebuild_stars()
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.highest_level = load_highest_level()
        self.level = 1
        self.score = 0
        self.combo = 0
        self.combo_timer = 0.0
        self.wave_banner = 0.0
        self.wave_banner_level = 1
        self.shake = 0.0
        self.flash = 0.0
        self.explosions = []

        self.player = None
        self.gun = None
        self.wave = None
        self.reset_game()

    def rebuild_stars(self):
        self.stars = [
            [random.randrange(max(1, self.screen_w)), random.randrange(max(1, self.screen_h)), random.choice((1, 1, 1, 2)), random.uniform(25, 100)]
            for _ in range(120)
        ]

    def resize_layout(self):
        self.screen_w, self.screen_h = self.window.get_size()
        if self.player:
            self.player.resetPosition()
        self.rebuild_stars()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.resize_layout()

    def reset_game(self):
        self.level = 1
        self.score = 0
        self.combo = 0
        self.combo_timer = 0
        self.wave_banner = 1.8
        self.wave_banner_level = 1
        self.shake = 0
        self.flash = 0
        self.explosions.clear()
        self.player = Player(self.window, asset_path("Images", "Player"), 100, 360, 10)
        self.player.scale(2)
        self.gun = Gun(self.window, asset_path("Images", "Guns"), self.player, 10, 50, 2.0, 900)
        self.gun.scale(0.5)
        self.wave = Wave(self.window, self.level)
        self.state = "menu"

    def start_game(self):
        self.reset_game()
        self.state = "play"

    def button_rects(self):
        play_rect = self.play_btn.get_rect(center=(self.screen_w // 2, self.screen_h // 2))
        quit_rect = self.quit_img.get_rect(bottomright=(self.screen_w - 20, self.screen_h - 20))
        menu_rect = self.menu_img.get_rect(bottomleft=(20, self.screen_h - 20))
        return play_rect, quit_rect, menu_rect

    def draw_text(self, text, pos, size=28, color=(235, 245, 255), center=False):
        font = self.small_font if size <= 24 else self.medium_font if size <= 40 else self.big_font
        img = font.render(str(text), True, color)
        rect = img.get_rect()
        rect.center = pos if center else rect.center
        if not center:
            rect.topleft = pos
        self.window.blit(img, rect)

    def draw_panel(self, rect, alpha=150):
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (5, 12, 25, alpha), panel.get_rect(), border_radius=16)
        pygame.draw.rect(panel, (100, 180, 230, 80), panel.get_rect(), 1, border_radius=16)
        self.window.blit(panel, rect.topleft)

    def draw_stars(self, dt, speed=1.0):
        for star in self.stars:
            star[1] += star[3] * dt * speed
            if star[1] >= self.screen_h:
                star[0] = random.randrange(max(1, self.screen_w))
                star[1] = -5
            c = int(max(80, min(220, 80 + star[3])))
            pygame.draw.circle(self.window, (c, c, min(255, c + 30)), (int(star[0]), int(star[1])), star[2])

    def draw_menu(self, dt):
        self.menu_timer += dt
        if self.menu_timer >= 0.10:
            self.menu_timer = 0
            self.menu_frame = (self.menu_frame + 1) % len(self.menu_frames)
        frame = pygame.transform.smoothscale(self.menu_frames[self.menu_frame], (self.screen_w, self.screen_h))
        self.window.blit(frame, (0, 0))
        self.draw_stars(dt, 0.2)
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((0, 5, 15, 70))
        self.window.blit(overlay, (0, 0))

        title_rect = self.name_img.get_rect(center=(self.screen_w // 2, 120))
        self.window.blit(self.name_img, title_rect)
        self.draw_text("DEEP SPACE // SURVIVAL PROTOCOL", (self.screen_w // 2, 190), 22, (120, 190, 230), True)

        play_rect, _, _ = self.button_rects()
        hover = play_rect.collidepoint(pygame.mouse.get_pos())
        if hover:
            glow = pygame.Surface((play_rect.width + 36, play_rect.height + 36), pygame.SRCALPHA)
            pygame.draw.rect(glow, (70, 180, 255, 45), glow.get_rect(), border_radius=18)
            self.window.blit(glow, (play_rect.x - 18, play_rect.y - 18))
        self.window.blit(self.play_btn_hover if hover else self.play_btn, play_rect)

        panel = pygame.Rect(self.screen_w // 2 - 300, self.screen_h - 120, 600, 70)
        self.draw_panel(panel, 150)
        self.draw_text(f"BEST WAVE  {self.highest_level:02d}", (self.screen_w // 2 - 140, self.screen_h - 85), 22, (220, 235, 245), True)
        self.draw_text("WASD / ARROWS  MOVE", (self.screen_w // 2 + 120, self.screen_h - 85), 18, (140, 170, 195), True)
        self.draw_text("SPACE / LMB  FIRE     ESC  QUIT", (24, self.screen_h - 30), 18, (130, 155, 180))

    def draw_health(self):
        x, y = 25, 25
        self.draw_text("HULL", (x, y), 20, (155, 180, 210))
        rect = pygame.Rect(x, y + 27, 260, 16)
        pygame.draw.rect(self.window, (25, 30, 45), rect, border_radius=6)
        ratio = max(0, min(1, self.player.health / self.player.maxHealth))
        fill = rect.copy()
        fill.width = int(rect.width * ratio)
        if fill.width:
            color = (70, 220, 145) if ratio > 0.35 else (255, 90, 90)
            pygame.draw.rect(self.window, color, fill, border_radius=6)
        self.draw_text(f"{max(0, int(self.player.health))} / {self.player.maxHealth}", (x + 130, y + 62), 18, (220, 235, 245), True)

    def draw_hud(self):
        self.draw_panel(pygame.Rect(15, 15, 310, 90), 145)
        self.draw_panel(pygame.Rect(self.screen_w - 330, 15, 315, 90), 145)
        self.draw_health()
        self.draw_text("SCORE", (self.screen_w - 310, 28), 18, (155, 180, 210))
        self.draw_text(f"{self.score:,}", (self.screen_w - 310, 48), 32, (240, 248, 255))
        self.draw_text(f"WAVE {self.level:02d}", (self.screen_w - 310, 80), 20, (110, 205, 255))
        self.draw_text("AMMO", (self.screen_w - 70, 28), 18, (155, 180, 210), True)
        ammo_text = "RELOAD" if self.gun.reloading else f"{self.gun.ammo:02d}"
        self.draw_text(ammo_text, (self.screen_w - 70, 55), 26, (240, 248, 255), True)
        self.draw_text("R  RELOAD", (self.screen_w - 70, 88), 16, (130, 155, 180), True)
        if self.combo > 1 and self.combo_timer > 0:
            self.draw_text(f"COMBO x{self.combo}", (self.screen_w // 2, 35), 30, (255, 210, 100), True)

        if self.wave_banner > 0:
            alpha = min(180, int(self.wave_banner * 100))
            panel = pygame.Surface((460, 80), pygame.SRCALPHA)
            pygame.draw.rect(panel, (8, 14, 28, alpha), panel.get_rect(), border_radius=18)
            self.window.blit(panel, (self.screen_w // 2 - 230, self.screen_h // 2 - 110))
            self.draw_text(f"WAVE {self.wave_banner_level}", (self.screen_w // 2, self.screen_h // 2 - 70), 42, (235, 248, 255), True)

    def draw_settings(self):
        self.window.fill((2, 5, 12))
        self.draw_stars(1 / FPS, 0.15)
        title = self.settings_title.get_rect(center=(self.screen_w // 2, 130))
        self.window.blit(self.settings_title, title)
        self.draw_text("GAME PAUSED", (self.screen_w // 2, 215), 32, (120, 255, 160), True)
        _, quit_rect, menu_rect = self.button_rects()
        mouse = pygame.mouse.get_pos()
        self.window.blit(self.quit_hover if quit_rect.collidepoint(mouse) else self.quit_img, quit_rect)
        self.window.blit(self.menu_img_hover if menu_rect.collidepoint(mouse) else self.menu_img, menu_rect)
        self.draw_text("ESC  RESUME", (self.screen_w // 2, self.screen_h - 35), 18, (150, 170, 190), True)

    def draw_game_over(self):
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((3, 5, 12, 220))
        self.window.blit(overlay, (0, 0))
        self.draw_text("MISSION FAILED", (self.screen_w // 2, self.screen_h // 2 - 80), 70, (255, 90, 110), True)
        self.draw_text(f"SCORE  {self.score:,}", (self.screen_w // 2, self.screen_h // 2 + 10), 40, (235, 245, 255), True)
        self.draw_text(f"BEST WAVE  {self.highest_level}", (self.screen_w // 2, self.screen_h // 2 + 55), 26, (150, 180, 210), True)
        self.draw_text("ENTER  RETRY     ESC  MENU", (self.screen_w // 2, self.screen_h - 65), 22, (180, 200, 225), True)

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            w = max(800, event.w)
            h = max(500, event.h)
            self.window = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            self.resize_layout()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                self.toggle_fullscreen()
                return
            if event.key == pygame.K_ESCAPE:
                if self.state == "menu":
                    self.running = False
                elif self.state == "play":
                    self.state = "settings"
                elif self.state == "settings":
                    self.state = "play"
                elif self.state == "game_over":
                    self.state = "menu"
                return
            if self.state == "play" and event.key == pygame.K_r:
                self.gun.request_reload(pygame.time.get_ticks() / 1000.0)
            if self.state == "game_over" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "menu":
                play_rect, _, _ = self.button_rects()
                if play_rect.collidepoint(event.pos):
                    self.start_game()
            elif self.state == "settings":
                _, quit_rect, menu_rect = self.button_rects()
                if quit_rect.collidepoint(event.pos):
                    self.running = False
                elif menu_rect.collidepoint(event.pos):
                    self.state = "menu"
            elif self.state == "game_over":
                self.start_game()

    def update(self, dt):
        now = pygame.time.get_ticks() / 1000.0
        if self.state == "play":
            keys = pygame.key.get_pressed()
            self.player.xChange = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
            self.player.yChange = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
            # Normalize diagonal movement.
            if self.player.xChange and self.player.yChange:
                self.player.xChange *= 0.7071
                self.player.yChange *= 0.7071

            self.player.update(dt)
            if keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]:
                self.gun.fire(now)
            self.gun.update(dt, now)
            self.wave.update(dt, self.player)

            # Player bullets versus enemies.
            for bullet in self.gun.bullets:
                if not bullet.active:
                    continue
                for enemy in self.wave.enemies:
                    if enemy.isDead() or enemy.position[1] < 0:
                        continue
                    if enemy.CB.isCollide(bullet.collisionBox):
                        bullet.active = False
                        died = enemy.take_damage(bullet.damage)
                        self.shake = min(12, self.shake + (5 if died else 1))
                        self.flash = max(self.flash, 0.03)
                        if died:
                            self.combo += 1
                            self.combo_timer = 2.0
                            base = 2500 if enemy.type == "boss" else 750 if enemy.type == "structure" else 100
                            self.score += base * max(1, self.combo)
                            x, y = enemy.position
                            self.explosions.append(Explosion(self.window, (x - 50, y - 50), self.explosion_frames, 0.5))
                        break

            # Enemy bullets versus player.
            for enemy in self.wave.enemies:
                if enemy.bullet_active and enemy.bullet and enemy.bullet.collisionBox.isCollide(self.player.CB):
                    enemy.bullet_active = False
                    enemy.bullet = None
                    self.player.health -= enemy.damage
                    self.shake = min(18, self.shake + 9)
                    self.flash = max(self.flash, 0.12)
                    self.combo = 0
                    break

            if self.combo_timer > 0:
                self.combo_timer -= dt
                if self.combo_timer <= 0:
                    self.combo = 0

            if self.wave_banner > 0:
                self.wave_banner -= dt
            if self.flash > 0:
                self.flash -= dt
            if self.shake > 0:
                self.shake = max(0, self.shake - dt * 18)

            alive_wave = self.wave.isDead()
            if alive_wave:
                self.level += 1
                self.wave = Wave(self.window, self.level)
                self.wave_banner = 1.5
                self.wave_banner_level = self.level
                if self.level > self.highest_level:
                    self.highest_level = self.level
                    save_highest_level(self.highest_level)

            if self.player.health <= 0:
                self.player.health = 0
                if self.level > self.highest_level:
                    self.highest_level = self.level
                    save_highest_level(self.highest_level)
                self.state = "game_over"

        # Keep effects alive in every state.
        alive = []
        for effect in self.explosions:
            effect.update(dt)
            if not effect.done:
                alive.append(effect)
        self.explosions = alive

    def draw(self, dt):
        if self.state == "menu":
            self.draw_menu(dt)
        elif self.state == "play":
            # Tiled scrolling background.
            y = int((pygame.time.get_ticks() * 0.08) % self.background.get_height()) - self.background.get_height()
            while y < self.screen_h:
                self.window.blit(self.background, (0, y))
                y += self.background.get_height()
            self.draw_stars(dt, 0.35)
            self.wave.draw()
            self.gun.draw()
            self.player.draw()
            self.draw_hud()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "game_over":
            self.draw_game_over()

        if self.flash > 0:
            flash = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
            flash.fill((255, 70, 90, min(80, int(self.flash * 500))))
            self.window.blit(flash, (0, 0))

        if self.shake > 0:
            # Apply shake to a copy without corrupting logical positions.
            frame = self.window.copy()
            self.window.fill((0, 0, 0))
            offset = int(self.shake)
            self.window.blit(frame, (random.randint(-offset, offset), random.randint(-offset, offset)))

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.draw(dt)
        save_highest_level(self.highest_level)
        pygame.quit()


def main():
    try:
        Game().run()
    except Exception:
        pygame.quit()
        raise


if __name__ == "__main__":
    main()
