"""
Light Cycles — Python Recreation
Original by Joe Lowe (early 1990s), x86 Assembly / DOS / VGA
Recreated in Python with Pygame

Two-player Tron-style light cycle game.
Player 1: A/D keys (or Z/X as in original)
Player 2: Left/Right arrow keys
"""

import pygame
import sys

SCREEN_W, SCREEN_H = 640, 480
FPS = 60

BACK_COLOR = (0, 0, 0)
BORDER_COLOR = (0, 0, 170)
P1_COLOR = (0, 255, 0)       # color 10
P1_TRAIL = (0, 100, 0)       # color 2
P2_COLOR = (255, 50, 50)     # color 12
P2_TRAIL = (150, 0, 0)       # color 4

# Directions: 0=up, 1=right, 2=down, 3=left
DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]


class Player:
    def __init__(self, x, y, direction, color, trail_color):
        self.x = x
        self.y = y
        self.direction = direction
        self.color = color
        self.trail_color = trail_color
        self.dead = False
        self.trail = [(x, y)]
        self.move_timer = 0
        self.speed = 9  # frames between moves (from original wait1/wait2 = 9)

    def turn_left(self):
        if not self.dead:
            self.direction = (self.direction - 1) % 4

    def turn_right(self):
        if not self.dead:
            self.direction = (self.direction + 1) % 4

    def update(self, grid):
        if self.dead:
            return
        self.move_timer += 1
        if self.move_timer < self.speed:
            return
        self.move_timer = 0

        # Leave trail at current position
        grid[self.y][self.x] = self.trail_color

        # Move
        self.x += DX[self.direction]
        self.y += DY[self.direction]

        # Check collision
        if (self.x <= 0 or self.x >= SCREEN_W - 1 or
                self.y <= 0 or self.y >= SCREEN_H - 1):
            self.dead = True
            return
        if grid[self.y][self.x] != BACK_COLOR:
            self.dead = True
            return

        grid[self.y][self.x] = self.color
        self.trail.append((self.x, self.y))


class LightCycles:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Light Cycles — Joe Lowe (1990s) — Python Recreation")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 20)
        self.small_font = pygame.font.SysFont("monospace", 14)
        self.surface = pygame.Surface((SCREEN_W, SCREEN_H))
        self.reset()

    def reset(self):
        # Grid stores color at each pixel
        self.grid = [[BACK_COLOR] * SCREEN_W for _ in range(SCREEN_H)]

        # Draw border into grid
        for x in range(SCREEN_W):
            self.grid[0][x] = BORDER_COLOR
            self.grid[SCREEN_H - 1][x] = BORDER_COLOR
        for y in range(SCREEN_H):
            self.grid[y][0] = BORDER_COLOR
            self.grid[y][SCREEN_W - 1] = BORDER_COLOR

        # Starting positions (from original)
        sx1 = SCREEN_W // 2 - SCREEN_W // 40
        sy = SCREEN_H - SCREEN_H // 10
        sx2 = SCREEN_W // 2 + SCREEN_W // 40

        self.p1 = Player(sx1, sy, 0, P1_COLOR, P1_TRAIL)
        self.p2 = Player(sx2, sy, 0, P2_COLOR, P2_TRAIL)

        self.grid[self.p1.y][self.p1.x] = P1_COLOR
        self.grid[self.p2.y][self.p2.x] = P2_COLOR

        self.state = "playing"
        self.explode_radius = 0
        self.explode_phase = 0
        self.max_rad = 20

        # Draw initial state to surface
        self.surface.fill(BACK_COLOR)
        pygame.draw.rect(self.surface, BORDER_COLOR, (0, 0, SCREEN_W, SCREEN_H), 1)

    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # Player 1: Z/X or A/D
                    if event.key in (pygame.K_z, pygame.K_a):
                        self.p1.turn_left()
                    if event.key in (pygame.K_x, pygame.K_d):
                        self.p1.turn_right()
                    # Player 2: arrow keys
                    if event.key == pygame.K_LEFT:
                        self.p2.turn_left()
                    if event.key == pygame.K_RIGHT:
                        self.p2.turn_right()
                    # Restart
                    if self.state == "prompt":
                        if event.key == pygame.K_y:
                            self.reset()
                        elif event.key == pygame.K_n:
                            running = False

            if self.state == "playing":
                self.update_playing()
            elif self.state == "exploding":
                self.update_exploding()

            self.draw()
            pygame.display.flip()

        pygame.quit()

    def update_playing(self):
        self.p1.update(self.grid)
        self.p2.update(self.grid)

        # Draw new trail pixels to surface
        if self.p1.trail:
            tx, ty = self.p1.trail[-1]
            self.surface.set_at((tx, ty), P1_COLOR if not self.p1.dead else P1_TRAIL)
        if self.p2.trail:
            tx, ty = self.p2.trail[-1]
            self.surface.set_at((tx, ty), P2_COLOR if not self.p2.dead else P2_TRAIL)

        if self.p1.dead or self.p2.dead:
            self.state = "exploding"
            self.explode_radius = 0
            self.explode_phase = 0

    def update_exploding(self):
        self.explode_radius += 1
        if self.explode_radius > self.max_rad:
            self.explode_phase += 1
            self.explode_radius = 0
        if self.explode_phase >= 3:
            self.state = "prompt"

    def draw(self):
        self.screen.blit(self.surface, (0, 0))

        if self.state in ("exploding", "prompt"):
            r = self.explode_radius
            if self.explode_phase == 0:
                color1, color2 = P1_COLOR, P2_COLOR
            elif self.explode_phase == 1:
                color1, color2 = P1_TRAIL, P2_TRAIL
            else:
                color1 = color2 = BACK_COLOR

            if r > 0 and self.state == "exploding":
                if self.p1.dead:
                    pygame.draw.circle(self.screen, color1,
                                       (self.p1.x, self.p1.y), r, 1)
                if self.p2.dead:
                    pygame.draw.circle(self.screen, color2,
                                       (self.p2.x, self.p2.y), r, 1)

        if self.state == "prompt":
            text = self.font.render("Play again? (Y or N)", True, (255, 255, 255))
            self.screen.blit(text, (SCREEN_W // 2 - text.get_width() // 2,
                                    SCREEN_H // 2 - 10))

        # Controls hint
        if self.state == "playing":
            hint = self.small_font.render(
                "P1: Z/X turn | P2: ←/→ turn | ESC: quit",
                True, (60, 60, 60))
            self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 5))


if __name__ == "__main__":
    game = LightCycles()
    game.run()
