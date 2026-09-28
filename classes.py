import os
import random
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(*parts):
    return os.path.join(BASE_DIR, *parts)


class CollisionBox:
    """Reliable axis-aligned collision box centered at x/y."""
    def __init__(self, width, height, x=0, y=0):
        self.width = max(1, float(width))
        self.height = max(1, float(height))
        self.x = float(x)
        self.y = float(y)

    def update_coords(self, x, y):
        self.x = float(x)
        self.y = float(y)

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x - self.width / 2),
            round(self.y - self.height / 2),
            max(1, round(self.width)),
            max(1, round(self.height)),
        )

    def isCollide(self, other):
        if other is None:
            return False
        return self.rect.colliderect(other.rect)


class Bullet:
    def __init__(self, image, x=0, y=0, vx=0, vy=0, damage=1):
        self.image = image
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.damage = damage
        self.active = True
        self.collisionBox = CollisionBox(image.get_width(), image.get_height(), x, y)

    @property
    def rect(self):
        return self.image.get_rect(center=(round(self.x), round(self.y)))

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.collisionBox.update_coords(self.x, self.y)


class Explosion:
    def __init__(self, window, position, frames=None, scale=0.5):
        self.window = window
        self.x, self.y = position
        self.frames = frames or []
        self.frame = 0
        self.frame_time = 0.035
        self.timer = 0.0
        self.done = not self.frames
        if scale != 1 and self.frames:
            self.frames = [
                pygame.transform.smoothscale(
                    img,
                    (max(1, int(img.get_width() * scale)), max(1, int(img.get_height() * scale))),
                )
                for img in self.frames
            ]

    def update(self, dt):
        if self.done:
            return
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.frame += 1
            if self.frame >= len(self.frames):
                self.done = True
                return
        self.window.blit(self.frames[self.frame], (round(self.x), round(self.y)))


class Player:
    def __init__(self, window, sprite_folder, health=100, speed=360, fire_power=10):
        self.window = window
        self.sprite_folder = sprite_folder
        self.maxHealth = health
        self.health = float(health)
        self.speed = speed
        self.firePower = fire_power
        self.hit = False
        self.start = False
        self.xChange = 0
        self.yChange = 0

        self.sprite = self._load_sprite()
        self.dimension = self.sprite.get_size()
        self.position = [0.0, 0.0]
        self.CB = CollisionBox(*self.dimension)
        self.resetPosition()

    def _load_sprite(self):
        path = os.path.join(self.sprite_folder, "Player_0.png")
        return pygame.image.load(path).convert_alpha()

    def resetPosition(self):
        w, h = self.window.get_size()
        self.position[0] = (w - self.dimension[0]) / 2
        self.position[1] = h - self.dimension[1] - 45
        self.position[0] = max(0, self.position[0])
        self.position[1] = max(0, self.position[1])
        self.xChange = 0
        self.yChange = 0
        self.sync_collision()

    # Keep compatibility with the old project spelling.
    resetPostion = resetPosition

    def scale(self, multiplier):
        w = max(1, int(self.sprite.get_width() * multiplier))
        h = max(1, int(self.sprite.get_height() * multiplier))
        self.sprite = pygame.transform.smoothscale(self.sprite, (w, h))
        self.dimension = self.sprite.get_size()
        self.CB.width = w
        self.CB.height = h
        self.resetPosition()

    def sync_collision(self):
        self.CB.update_coords(
            self.position[0] + self.dimension[0] / 2,
            self.position[1] + self.dimension[1] / 2,
        )

    def update(self, dt):
        w, h = self.window.get_size()
        self.position[0] += self.xChange * self.speed * dt
        self.position[1] += self.yChange * self.speed * dt
        self.position[0] = max(0, min(self.position[0], w - self.dimension[0]))
        self.position[1] = max(0, min(self.position[1], h - self.dimension[1] - 18))
        self.sync_collision()

    def draw(self):
        self.window.blit(self.sprite, (round(self.position[0]), round(self.position[1])))


class Gun:
    def __init__(self, window, sprite_folder, player, damage=10, magazine_size=50, reload_time=2.0, bullet_speed=900):
        self.window = window
        self.player = player
        self.damage = damage
        self.maxBullets = magazine_size
        self.reloadTime = reload_time
        self.bulletSpeed = bullet_speed
        self.shotCooldown = 0.12
        self.lastShot = -999.0
        self.reload_started = 0.0
        self.reloading = False
        self.numBullets = 0
        self.bullets = []
        self.image = pygame.image.load(os.path.join(sprite_folder, "laser.png")).convert_alpha()
        self.dimension = self.image.get_size()

    @property
    def ammo(self):
        return self.maxBullets - self.numBullets

    def scale(self, multiplier):
        w = max(1, int(self.image.get_width() * multiplier))
        h = max(1, int(self.image.get_height() * multiplier))
        self.image = pygame.transform.smoothscale(self.image, (w, h))
        self.dimension = self.image.get_size()

    def can_fire(self, now):
        return (not self.reloading and self.numBullets < self.maxBullets and now - self.lastShot >= self.shotCooldown)

    def fire(self, now):
        if not self.can_fire(now):
            return False
        x = self.player.position[0] + self.player.dimension[0] / 2
        y = self.player.position[1] - self.dimension[1] / 2
        self.bullets.append(Bullet(self.image, x, y, 0, -self.bulletSpeed, self.damage))
        self.numBullets += 1
        self.lastShot = now
        if self.numBullets >= self.maxBullets:
            self.start_reload(now)
        return True

    def start_reload(self, now):
        if not self.reloading:
            self.reloading = True
            self.reload_started = now

    def request_reload(self, now):
        if self.numBullets > 0:
            self.start_reload(now)

    def update(self, dt, now):
        for b in self.bullets:
            if b.active:
                b.update(dt)
        self.bullets = [b for b in self.bullets if b.active and b.y > -b.image.get_height()]

        if self.reloading and now - self.reload_started >= self.reloadTime:
            self.numBullets = 0
            self.reloading = False

    def reset(self):
        self.bullets.clear()
        self.numBullets = 0
        self.reloading = False
        self.lastShot = -999.0

    def draw(self):
        for b in self.bullets:
            if b.active:
                self.window.blit(b.image, b.rect)


class Enemy:
    def __init__(self, window, enemy_type, sprite_number, difficulty):
        self.window = window
        self.type = enemy_type
        self.difficulty = difficulty
        self.health = (30 if enemy_type == "boss" else 8 if enemy_type == "structure" else 5) * difficulty
        self.max_health = self.health
        self.damage = min(40 if enemy_type == "boss" else 20, (1.0 if enemy_type == "boss" else 0.5) * difficulty)
        self.hit = False
        self.finished = False
        self.active = True
        self.attacking = False
        self.bullet_active = False
        self.position = [0.0, -200.0]
        self.velocity_y = 90 + min(120, difficulty * 3)
        self.fire_timer = random.uniform(0.7, 2.0)

        if enemy_type == "alien":
            self.sprite = pygame.image.load(asset_path("Images", "Enemy", "Aliens", f"Alien_{sprite_number}.png")).convert_alpha()
            self.bullet_image = pygame.image.load(asset_path("Images", "Enemy", "Bullets", "Laser.png")).convert_alpha()
        elif enemy_type == "boss":
            self.sprite = pygame.image.load(asset_path("Images", "Enemy", "Bosses", f"Boss_{sprite_number}.png")).convert_alpha()
            self.bullet_image = pygame.image.load(asset_path("Images", "Enemy", "Bullets", "Laser_beam.png")).convert_alpha()
        else:
            self.sprite = pygame.image.load(asset_path("Images", "Enemy", "Structures", f"Structure_{sprite_number}.png")).convert_alpha()
            self.bullet_image = pygame.image.load(asset_path("Images", "Enemy", "Bullets", "Laser.png")).convert_alpha()

        self.CB = CollisionBox(*self.sprite.get_size())
        self.bullet = None
        self._sync()

    @property
    def dmg(self):
        return self.damage

    @property
    def coordinates(self):
        return self.position

    def spawn_enemy(self, coordinates):
        self.position = [float(coordinates[0]), float(coordinates[1])]
        self.bullet = None
        self.bullet_active = False
        self._sync()

    def _sync(self):
        self.CB.update_coords(*self.position)
        if self.bullet is not None:
            self.bullet.collisionBox.update_coords(self.bullet.x, self.bullet.y)

    def move_down(self, dt):
        self.position[1] += self.velocity_y * dt
        self._sync()

    def update(self, dt, player, screen_size):
        if not self.active:
            return
        w, h = screen_size
        if self.position[1] < 80:
            self.move_down(dt)
            return

        self.fire_timer -= dt
        if self.fire_timer <= 0 and not self.bullet_active:
            self.fire_timer = random.uniform(0.8, 2.2) / min(2.5, 1 + self.difficulty * 0.05)
            bx = self.position[0]
            by = self.position[1] + self.sprite.get_height() / 2 + self.bullet_image.get_height() / 2
            speed = 330 + min(220, self.difficulty * 8)
            self.bullet = Bullet(self.bullet_image, bx, by, 0, speed, self.damage)
            self.bullet_active = True

        if self.bullet_active and self.bullet:
            self.bullet.update(dt)
            if self.bullet.y - self.bullet.image.get_height() / 2 > h:
                self.bullet_active = False
                self.bullet = None
        self._sync()

    def draw(self):
        if not self.active:
            return
        rect = self.sprite.get_rect(center=(round(self.position[0]), round(self.position[1])))
        self.window.blit(self.sprite, rect)
        if self.bullet_active and self.bullet:
            self.window.blit(self.bullet.image, self.bullet.rect)

        if self.health < self.max_health:
            bar_w = max(30, self.sprite.get_width())
            bar = pygame.Rect(round(self.position[0] - bar_w / 2), round(self.position[1] - self.sprite.get_height() / 2 - 10), bar_w, 5)
            pygame.draw.rect(self.window, (35, 35, 45), bar)
            fill = bar.copy()
            fill.width = max(0, int(bar.width * max(0, self.health) / self.max_health))
            pygame.draw.rect(self.window, (255, 90, 100), fill)

    def isDead(self):
        return self.health <= 0 or not self.active

    def take_damage(self, amount):
        if not self.active:
            return False
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.active = False
            self.bullet_active = False
            self.bullet = None
            return True
        return False


class Wave:
    def __init__(self, window, difficulty):
        self.window = window
        self.difficulty = max(1, difficulty)
        self.enemies = []
        self.ready = False
        self._spawned = False
        self.spawn_enemies()

    def spawn_enemies(self):
        self.enemies.clear()
        w, h = self.window.get_size()
        boss_wave = self.difficulty % 10 == 0
        count = 20 if boss_wave else 5 * (((self.difficulty - 1) % 9) + 1)

        if boss_wave:
            count = 20

        for i in range(count):
            enemy = Enemy(self.window, "alien", random.randint(0, 3), self.difficulty)
            col = i % 5
            row = i // 5
            x = w * (col + 1) / 6
            y = -100 - row * 120
            enemy.spawn_enemy((x, y))
            self.enemies.append(enemy)

        if boss_wave:
            boss = Enemy(self.window, "boss", 0, self.difficulty)
            boss.spawn_enemy((w / 2, -h * 0.45))
            self.enemies.append(boss)
            for x in (64, w - 64):
                structure = Enemy(self.window, "structure", 0, self.difficulty)
                structure.spawn_enemy((x, -h * 0.35))
                self.enemies.append(structure)

        self.ready = False
        self._spawned = True

    def update(self, dt, player):
        if not self.enemies:
            self.ready = True
            return
        for enemy in self.enemies:
            enemy.update(dt, player, self.window.get_size())
        self.ready = all(enemy.position[1] >= 80 or enemy.isDead() for enemy in self.enemies)

    def draw(self):
        for enemy in self.enemies:
            enemy.draw()

    def isDead(self):
        return not self.enemies or all(enemy.isDead() for enemy in self.enemies)
