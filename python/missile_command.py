"""
Missile Command — Python Recreation
Original by Joe Lowe (early 1990s), x86 Assembly / DOS / VGA
Recreated in Python with Pygame

This is a faithful recreation of the original assembly game.
The original ran in VGA 640x480 16-color mode with a cooperative
task scheduler, mouse input, and PC speaker sound.
"""

import pygame
import math
import random
import sys

# ---------------------------------------------------------------------------
# Constants (from original ASM data segment)
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 640, 480
FPS = 60

# Colors — original used VGA 16-color palette indices, mapped to RGB here.
# The original palette was loaded via preppallette/setpallette per wave.
# We use a representative default palette.
COLORS = {
    "back":       (0, 0, 0),
    "cloud":      (255, 0, 0),       # color 4 — explosion clouds
    "mcolor1":    (0, 255, 255),     # color 3 — missile head
    "mcolor2":    (0, 0, 170),       # color 1 — missile trail
    "ground":     (128, 96, 0),      # color 6
    "city":       (192, 192, 192),   # color 7
    "warhead1":   (0, 255, 255),     # color 3
    "warhead2":   (0, 170, 0),       # color 2
    "warcloud":   (170, 170, 0),     # color 5
    "crosshair":  (255, 255, 255),   # color 8 / xor
    "score":      (255, 255, 255),
}

# Layout positions (from original data)
XLAUNCH1 = 205
XLAUNCH2 = 434
YLAUNCH = 429
CITY_DECK = 462
SPLIT_DECK = 160
CLOUD_DECK = 429
CITY_X = [12, 106, 241, 335, 470, 564]
TARGET_X = [44, 138, 205, 273, 367, 434, 502, 596]

CLOUD_RAD = 45
CLOUD_SPEED = 80
MISS_SPEED = 2
WARHEAD_TRACE_SPEED = 3
MAX_MISSILES = 15

BONUS_GAP = 250
POINTS_WARHEAD_CLOUD = 2
POINTS_WARCLOUD = 4
POINTS_MISSILE_LEFT = 1
POINTS_CITY_LEFT = 10

# Wave definitions: (warhead_speed, [(delay_ms, count), ...])
# Translated from the original wave0–wave19 data
WAVES = [
    (5,  [(2000,4),(10000,4),(10000,4)]),
    (5,  [(2000,4),(10000,5),(10000,6)]),
    (5,  [(2000,5),(10000,6),(10000,2),(19000,2),(9000,8)]),
    (2,  [(2000,6),(10000,3),(10000,1),(1500,1),(1500,1),(1500,1),(1500,8)]),
    (2,  [(2000,3),(10000,3),(10000,3),(10000,3),(10000,5),(10000,5)]),
    (2,  [(2000,4),(10000,4),(10000,8),(10000,2),(10000,2),(10000,5)]),
    (3,  [(2000,3),(10000,3),(10000,3),(10000,3),(10000,5),(10000,5)]),
    (3,  [(2000,4),(10000,4),(10000,8),(10000,2),(10000,2),(10000,5)]),
    (3,  [(2000,4),(5000,4),(5000,4),(5000,4),(5000,4),(5000,4)]),
    (7,  [(4000,5),(4000,5),(4000,5),(3000,3),(3000,3),(3000,3),(5000,5)]),
    (7,  [(3000,4),(4000,4),(3500,4),(3000,4),(2500,4),(2000,4),(1500,4)]),
    (7,  [(3000,6),(6000,6),(6000,6),(6000,6),(10000,4),(7000,4)]),
    (1,  [(7000,2),(5000,2),(5000,2),(5000,2),(5000,2)]),
    (1,  [(7000,2),(8000,2),(8000,3),(5000,3),(5000,2),(8000,6)]),
    (1,  [(2000,6),(7000,6),(7000,6),(7000,3),(4000,3),(4000,7),(4000,2)]),
    (2,  [(2000,4),(5000,4),(5000,4),(5000,4),(5000,4),(5000,4),(5000,4)]),
    (3,  [(2000,3),(5000,3),(5000,3),(5000,3),(5000,3),(5000,3),(5000,3)]),
    (4,  [(2000,8),(8000,8),(8000,8),(8000,1),(5000,1),(5000,6)]),
    (5,  [(2000,5),(3000,5),(3000,5),(3000,5),(3000,5),(3000,5)]),
    (7,  [(2000,4),(10000,4),(10000,8),(10000,2),(10000,2),(10000,5)]),
]

# Timing: original timer ticks → we convert to milliseconds
# The original timer ran at ~18.2 Hz (55ms/tick) but was accelerated.
# We scale wave delays: original values / ~18 to get rough ms at 60fps
TICK_SCALE = 1.0 / 18.0  # convert original tick units to seconds


# ---------------------------------------------------------------------------
# City shape data — simplified from the original 8x8 bitmap shapes
# We draw stylized city silhouettes instead of exact pixel bitmaps
# ---------------------------------------------------------------------------
def draw_city_silhouette(surface, x, y, color):
    """Draw a simplified city at (x, y) base position."""
    buildings = [
        pygame.Rect(x, y - 22, 8, 22),
        pygame.Rect(x + 8, y - 22, 8, 22),
        pygame.Rect(x + 16, y - 27, 8, 27),
        pygame.Rect(x + 24, y - 32, 8, 32),
        pygame.Rect(x + 32, y - 32, 8, 32),
        pygame.Rect(x + 40, y - 23, 8, 23),
        pygame.Rect(x + 48, y - 23, 8, 23),
        pygame.Rect(x + 56, y - 18, 8, 18),
    ]
    for b in buildings:
        pygame.draw.rect(surface, color, b)


# ---------------------------------------------------------------------------
# Game Objects
# ---------------------------------------------------------------------------
class Missile:
    """Player missile — travels from launch base to target using Bresenham."""

    def __init__(self, start_x, start_y, target_x, target_y):
        self.x = float(start_x)
        self.y = float(start_y)
        self.target_x = target_x
        self.target_y = target_y
        self.trail = [(int(self.x), int(self.y))]
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)
        speed = 6.0
        if dist > 0:
            self.vx = dx / dist * speed
            self.vy = dy / dist * speed
        else:
            self.vx, self.vy = 0, -speed
        self.alive = True
        self.reached = False

    def update(self):
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        self.trail.append((int(self.x), int(self.y)))
        # Check if we've reached or passed the target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if (self.vy < 0 and self.y <= self.target_y) or \
           (self.vy >= 0 and self.y >= self.target_y):
            self.alive = False
            self.reached = True

    def draw(self, surface):
        if len(self.trail) > 1:
            pygame.draw.lines(surface, COLORS["mcolor1"], False, self.trail, 1)
        if self.alive:
            pygame.draw.circle(surface, COLORS["mcolor2"],
                               (int(self.x), int(self.y)), 2)


class Warhead:
    """Enemy warhead — descends from top toward a target city."""

    def __init__(self, start_x, start_y, target_idx, speed):
        self.x = float(start_x)
        self.y = float(start_y)
        tx = TARGET_X[target_idx]
        ty = CITY_DECK
        dx = tx - start_x
        dy = ty - start_y
        dist = math.hypot(dx, dy)
        self.speed = max(0.5, speed * 0.3)
        if dist > 0:
            self.vx = dx / dist * self.speed
            self.vy = dy / dist * self.speed
        else:
            self.vx, self.vy = 0, self.speed
        self.target_idx = target_idx
        self.trail = [(int(self.x), int(self.y))]
        self.alive = True
        self.split = False

    def update(self):
        if not self.alive:
            return
        self.x += self.vx
        self.y += self.vy
        self.trail.append((int(self.x), int(self.y)))
        if self.y >= CITY_DECK:
            self.alive = False
        if not self.split and int(self.y) >= SPLIT_DECK:
            if random.randint(0, 3) == 0:
                self.split = True

    def draw(self, surface):
        if len(self.trail) > 1:
            pygame.draw.lines(surface, COLORS["warhead1"], False, self.trail, 1)
        if self.alive:
            pygame.draw.circle(surface, COLORS["warhead2"],
                               (int(self.x), int(self.y)), 2)


class Cloud:
    """Explosion cloud — expands then contracts."""

    def __init__(self, x, y, color, max_radius=None):
        self.x = x
        self.y = y
        self.color = color
        self.radius = 0
        self.max_radius = max_radius or CLOUD_RAD
        # Limit max radius if near ground
        ground_dist = CLOUD_DECK - y
        if ground_dist < self.max_radius:
            self.max_radius = max(3, ground_dist)
        self.expanding = True
        self.alive = True
        self.speed = 0.8

    def update(self):
        if not self.alive:
            return
        if self.expanding:
            self.radius += self.speed
            if self.radius >= self.max_radius:
                self.expanding = False
        else:
            self.radius -= self.speed
            if self.radius <= 0:
                self.alive = False

    def draw(self, surface):
        if self.alive and self.radius > 0:
            pygame.draw.circle(surface, self.color,
                               (int(self.x), int(self.y)), int(self.radius), 1)
            # Fill for better visibility
            pygame.draw.circle(surface, self.color,
                               (int(self.x), int(self.y)), max(1, int(self.radius)))

    def contains(self, x, y):
        """Check if point is inside the cloud."""
        if not self.alive or self.radius <= 0:
            return False
        return math.hypot(x - self.x, y - self.y) <= self.radius


# ---------------------------------------------------------------------------
# Main Game
# ---------------------------------------------------------------------------
class MissileCommand:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Missile Command — Joe Lowe (1990s) — Python Recreation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 16)
        self.small_font = pygame.font.SysFont("monospace", 12)

        # Generate simple sound effects
        self.snd_launch = self._make_sound(440, 80)
        self.snd_explode = self._make_sound(120, 200)
        self.snd_click = self._make_sound(800, 30)

        self.reset_game()

    def _make_sound(self, freq, duration_ms):
        """Generate a simple tone as a pygame Sound object."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration_ms / 1000)
        buf = bytearray(n_samples * 2)
        for i in range(n_samples):
            t = i / sample_rate
            # Decay envelope
            env = max(0, 1.0 - t / (duration_ms / 1000))
            val = int(env * 16000 * math.sin(2 * math.pi * freq * t))
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        sound = pygame.mixer.Sound(buffer=bytes(buf))
        sound.set_volume(0.3)
        return sound

    def reset_game(self):
        self.score = 0
        self.city_alive = [True] * 6
        self.wave_num = 0
        self.next_bonus = BONUS_GAP
        self.bonus_cities = 0
        self.game_over = False
        self.start_wave()

    def start_wave(self):
        self.missiles = []
        self.warheads = []
        self.clouds = []
        self.miss_left = MAX_MISSILES
        self.miss_right = MAX_MISSILES
        self.wave_spawns = []
        self.wave_timer = 0

        wave_idx = self.wave_num % len(WAVES)
        speed, spawns = WAVES[wave_idx]
        self.warhead_speed = speed

        # Build spawn schedule: (time_ms, count)
        t = 0
        for delay, count in spawns:
            t += delay * TICK_SCALE * 1000 / FPS  # convert to frame-relative time
            self.wave_spawns.append((t, count))

        self.spawn_idx = 0
        self.wave_active = True
        self.wave_complete = False
        self.end_wave_timer = 0

    def alive_cities(self):
        return sum(self.city_alive)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if self.game_over and event.key == pygame.K_RETURN:
                        self.reset_game()
                elif event.type == pygame.MOUSEBUTTONDOWN and not self.game_over:
                    mx, my = event.pos
                    if event.button == 1:  # left click → left base
                        if self.miss_left > 0:
                            self.miss_left -= 1
                            self.missiles.append(Missile(XLAUNCH1, YLAUNCH, mx, my))
                            self.snd_launch.play()
                    elif event.button == 3:  # right click → right base
                        if self.miss_right > 0:
                            self.miss_right -= 1
                            self.missiles.append(Missile(XLAUNCH2, YLAUNCH, mx, my))
                            self.snd_launch.play()

            if not self.game_over:
                self.update()
            self.draw()
            pygame.display.flip()

        pygame.quit()

    def update(self):
        self.wave_timer += 1

        # Spawn warheads according to wave schedule
        while self.spawn_idx < len(self.wave_spawns):
            t, count = self.wave_spawns[self.spawn_idx]
            if self.wave_timer >= t:
                for _ in range(count):
                    sx = random.randint(0, SCREEN_W)
                    ti = random.randint(0, 7)
                    self.warheads.append(Warhead(sx, 0, ti, self.warhead_speed))
                self.spawn_idx += 1
            else:
                break

        # Update missiles
        for m in self.missiles:
            m.update()
            if not m.alive and m.reached:
                self.clouds.append(Cloud(int(m.x), int(m.y), COLORS["cloud"]))
                m.reached = False

        # Update warheads
        new_warheads = []
        for w in self.warheads:
            old_split = w.split
            w.update()

            # Check if warhead hit by any cloud
            if w.alive:
                for c in self.clouds:
                    if c.contains(w.x, w.y):
                        w.alive = False
                        self.clouds.append(Cloud(int(w.x), int(w.y),
                                                 COLORS["warcloud"], max_radius=25))
                        self.score += POINTS_WARHEAD_CLOUD
                        self.snd_explode.play()
                        break

            # Warhead splitting
            if w.alive and w.split and not old_split:
                for _ in range(2):
                    ti = (w.target_idx + random.choice([-1, 1])) % 8
                    new_warheads.append(Warhead(w.x, w.y, ti, self.warhead_speed))

            # Warhead reached ground — check city hits
            if not w.alive and w.y >= CITY_DECK - 5:
                hit_city = -1
                for i, cx in enumerate(CITY_X):
                    if self.city_alive[i] and abs(w.x - (cx + 32)) < 40:
                        hit_city = i
                        break
                if hit_city >= 0:
                    self.city_alive[hit_city] = False
                    # Nuke explosion on city
                    cx = CITY_X[hit_city] + 32
                    self.clouds.append(Cloud(cx, CITY_DECK - 15,
                                             COLORS["warcloud"], max_radius=23))
                    self.snd_explode.play()
                else:
                    self.clouds.append(Cloud(int(w.x), CITY_DECK,
                                             COLORS["warcloud"], max_radius=15))

        self.warheads.extend(new_warheads)

        # Update clouds
        for c in self.clouds:
            c.update()

        # Clean up dead objects
        self.missiles = [m for m in self.missiles if m.alive or len(m.trail) > 1]
        self.missiles = [m for m in self.missiles
                         if m.alive or any(c.alive for c in self.clouds)]
        self.warheads = [w for w in self.warheads if w.alive]
        self.clouds = [c for c in self.clouds if c.alive]

        # Check wave completion
        if (self.spawn_idx >= len(self.wave_spawns) and
                len(self.warheads) == 0 and len(self.clouds) == 0):
            if not self.wave_complete:
                self.wave_complete = True
                self.end_wave_timer = FPS * 2  # 2 second delay

        if self.wave_complete:
            self.end_wave_timer -= 1
            if self.end_wave_timer <= 0:
                self.finish_wave()

        # Check game over
        if self.alive_cities() == 0:
            self.game_over = True

    def finish_wave(self):
        """End-of-wave scoring — missiles and cities remaining."""
        # Score remaining missiles
        remaining = self.miss_left + self.miss_right
        self.score += remaining * POINTS_MISSILE_LEFT

        # Score remaining cities
        self.score += self.alive_cities() * POINTS_CITY_LEFT

        # Bonus city check
        if self.score >= self.next_bonus:
            self.bonus_cities += 1
            self.next_bonus += BONUS_GAP
            # Revive a dead city if possible
            for i in range(6):
                if not self.city_alive[i]:
                    self.city_alive[i] = True
                    break

        self.wave_num += 1
        self.start_wave()

    def draw(self):
        self.screen.fill(COLORS["back"])

        # Draw ground
        ground_color = COLORS["ground"]
        pygame.draw.rect(self.screen, ground_color,
                         (0, SCREEN_H - 20, SCREEN_W, 20))

        # Draw launch base mounds
        for lx in [XLAUNCH1, XLAUNCH2]:
            points = [(lx - 30, SCREEN_H - 20), (lx, SCREEN_H - 50),
                      (lx + 30, SCREEN_H - 20)]
            pygame.draw.polygon(self.screen, ground_color, points)

        # Draw cities
        for i, cx in enumerate(CITY_X):
            if self.city_alive[i]:
                draw_city_silhouette(self.screen, cx, CITY_DECK, COLORS["city"])

        # Draw missile counts on bases
        for base_idx, (lx, count) in enumerate(
                [(XLAUNCH1, self.miss_left), (XLAUNCH2, self.miss_right)]):
            for j in range(count):
                mx = lx - 14 + (j % 5) * 7
                my = SCREEN_H - 25 - (j // 5) * 8
                pygame.draw.line(self.screen, COLORS["cloud"],
                                 (mx, my), (mx, my - 5), 2)

        # Draw clouds
        for c in self.clouds:
            c.draw(self.screen)

        # Draw warheads
        for w in self.warheads:
            w.draw(self.screen)

        # Draw missiles
        for m in self.missiles:
            m.draw(self.screen)

        # Draw crosshair at mouse position
        mx, my = pygame.mouse.get_pos()
        ch_size = 6
        pygame.draw.line(self.screen, COLORS["crosshair"],
                         (mx - ch_size, my - ch_size), (mx + ch_size, my + ch_size), 1)
        pygame.draw.line(self.screen, COLORS["crosshair"],
                         (mx - ch_size, my + ch_size), (mx + ch_size, my - ch_size), 1)

        # HUD
        score_text = self.font.render(f"SCORE: {self.score}", True, COLORS["score"])
        self.screen.blit(score_text, (10, SCREEN_H - 18))

        wave_text = self.small_font.render(f"WAVE {self.wave_num + 1}", True, COLORS["score"])
        self.screen.blit(wave_text, (SCREEN_W // 2 - 30, 5))

        cities_text = self.small_font.render(
            f"CITIES: {self.alive_cities()}  LEFT: {self.miss_left}  RIGHT: {self.miss_right}",
            True, COLORS["score"])
        self.screen.blit(cities_text, (SCREEN_W - 350, 5))

        controls = self.small_font.render(
            "LEFT CLICK = Left Base | RIGHT CLICK = Right Base | ESC = Quit",
            True, (100, 100, 100))
        self.screen.blit(controls, (SCREEN_W // 2 - 220, SCREEN_H - 18))

        if self.game_over:
            go_text = self.font.render("GAME OVER", True, (255, 0, 0))
            restart_text = self.small_font.render("Press ENTER to restart",
                                                  True, (200, 200, 200))
            self.screen.blit(go_text,
                             (SCREEN_W // 2 - go_text.get_width() // 2, SCREEN_H // 2 - 20))
            self.screen.blit(restart_text,
                             (SCREEN_W // 2 - restart_text.get_width() // 2, SCREEN_H // 2 + 20))


if __name__ == "__main__":
    game = MissileCommand()
    game.run()
