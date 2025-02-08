import pygame
import pymunk
import pymunk.pygame_util
import sys
import math

pygame.init()

WIDTH, HEIGHT = 600, 800
BORDER_THICKNESS = 10
FPS = 60
WAITING, MOVING, STOPPED = 0, 1, 2
MAX_LEVEL = 10
COOLDOWN_TIME = 1

COLORS = {
    1: (144, 238, 144),  # 浅绿
    2: (152, 251, 152),  # 黄绿
    3: (173, 255, 47),  # 绿黄
    4: (255, 215, 0),  # 金黄
    5: (255, 165, 0),  # 橙色
    6: (255, 69, 0),  # 红橙
    7: (255, 0, 0),  # 红色
    8: (147, 112, 219),  # 紫罗兰
    9: (138, 43, 226),  # 蓝紫
    10: (148, 0, 211),  # 深紫
}


class Physics:
    def __init__(self):
        self.space = pymunk.Space()
        self.space.gravity = (0, 900)
        self.space.damping = 0.8
        self._create_borders()
        self.collision_handler = self.space.add_collision_handler(1, 1)
        self.merge_pairs = []

    def _create_borders(self):
        borders = [
            [(0, 0), (WIDTH, 0)],
            [(0, HEIGHT), (WIDTH, HEIGHT)],
            [(0, 0), (0, HEIGHT)],
            [(WIDTH, 0), (WIDTH, HEIGHT)],
        ]
        for points in borders:
            body = pymunk.Body(body_type=pymunk.Body.STATIC)
            shape = pymunk.Segment(body, points[0], points[1], BORDER_THICKNESS)
            shape.elasticity = 0.8
            shape.friction = 1.5
            self.space.add(body, shape)

    def add(self, body, shape):
        self.space.add(body, shape)

    def remove(self, body, shape):
        self.space.remove(body, shape)

    def step(self, dt):
        for body in self.space.bodies:
            if not math.isfinite(body.position.x) or not math.isfinite(body.position.y):
                self.space.remove(body, *body.shapes)
        self.space.step(dt)


class Watermelon:
    def __init__(self, pos, level, state=WAITING):
        self.level = min(level, MAX_LEVEL)
        self.radius = self._calculate_radius()
        self.state = state
        self.merged = False

        self._init_physics(pos)
        self._init_shape_properties()

    def _init_physics(self, pos):
        if self.state == WAITING:
            self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            self.body.position = pos
            self.shape = pymunk.Circle(self.body, self.radius)
        else:
            mass = 1
            moment = pymunk.moment_for_circle(mass, 0, self.radius)
            self.body = pymunk.Body(mass, moment)
            self.body.position = pos
            self.shape = pymunk.Circle(self.body, self.radius)

    def _init_shape_properties(self):
        self.shape.elasticity = 0.8
        self.shape.friction = 0.5
        self.shape.collision_type = 1
        self.shape.filter = pymunk.ShapeFilter(categories=0b1)
        self.body.user_data = self
        self.body.angular_velocity = 0

    def convert_to_dynamic(self):
        if self.state == WAITING:
            mass = 120
            moment = pymunk.moment_for_circle(mass, 0, self.radius)
            new_body = pymunk.Body(mass, moment)
            new_body.position = self.body.position
            new_body.user_data = self

            self.shape.body = new_body
            self.body = new_body
            self.state = MOVING

    def _calculate_radius(self):
        return 45 + (self.level - 1) * 8

    def update(self):
        if not math.isfinite(self.body.position.x) or not math.isfinite(
            self.body.position.y
        ):
            self.body.position = (WIDTH // 2, HEIGHT // 2)
        if self.state == WAITING:
            x = max(self.radius, min(self.body.position.x, WIDTH - self.radius))
            self.body.position = (x, 50)

    def draw(self, surface):
        color = COLORS.get(self.level, (200, 200, 200))
        pos = int(self.body.position.x), int(self.body.position.y)

        shadow_offset = 3
        pygame.draw.circle(
            surface,
            (0, 0, 0, 100),
            (pos[0] + shadow_offset, pos[1] + shadow_offset),
            self.radius,
        )

        pygame.draw.circle(surface, color, pos, self.radius)
        pygame.draw.circle(surface, (0, 100, 0), pos, self.radius, 2)

        font = pygame.font.Font(None, int(self.radius))
        text = font.render(str(self.level), True, (30, 30, 30))
        text_rect = text.get_rect(center=pos)
        surface.blit(text, text_rect)


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Synthesis Watermelon")
        self.clock = pygame.time.Clock()
        self.physics = Physics()
        self._init_collision_handler()

        self.watermelons = []
        self.waiting_wm = self._create_waiting_wm()
        self.score = 1
        self.game_over = False

        self.cooldown = 0.0
        self.can_spawn = True

    def _init_collision_handler(self):
        def collision_handler(arbiter, space, data):
            try:
                shape_a, shape_b = arbiter.shapes
                wm1 = shape_a.body.user_data
                wm2 = shape_b.body.user_data
                if (
                    wm1.level == wm2.level
                    and not wm1.merged
                    and not wm2.merged
                    and wm1.state != WAITING
                    and wm2.state != WAITING
                ):
                    wm1.merged = True
                    wm2.merged = True
                    self.physics.merge_pairs.append((wm1, wm2))
            except AttributeError:
                pass
            return True

        self.physics.collision_handler.begin = collision_handler

    def _create_waiting_wm(self):
        wm = Watermelon((WIDTH // 2, 50), 1, WAITING)
        self.watermelons.append(wm)
        return wm

    def _handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.game_over and event.key == pygame.K_r:
                    self.__init__()
                elif not self.game_over:
                    if event.key in [pygame.K_DOWN, pygame.K_SPACE]:
                        self._release_wm()
        keys = pygame.key.get_pressed()
        if not self.game_over and self.waiting_wm.state == WAITING:
            speed = 5
            if keys[pygame.K_LEFT]:
                self.waiting_wm.body.position -= (speed, 0)

            if keys[pygame.K_RIGHT]:
                self.waiting_wm.body.position += (speed, 0)

    def _release_wm(self):
        if not self.can_spawn or self.waiting_wm.state != WAITING:
            return

        collision = False
        for wm in self.watermelons:
            if wm is not self.waiting_wm and self._check_collision(wm, self.waiting_wm):
                collision = True
                break

        if collision:
            self.game_over = True
            return

        self.waiting_wm.convert_to_dynamic()
        self.physics.add(self.waiting_wm.body, self.waiting_wm.shape)

        self.can_spawn = False
        self.cooldown = COOLDOWN_TIME

    def _process_merges(self):
        for wm1, wm2 in self.physics.merge_pairs[:]:
            if wm1 in self.watermelons and wm2 in self.watermelons:
                new_pos = (
                    (wm1.body.position.x + wm2.body.position.x) / 2,
                    (wm1.body.position.y + wm2.body.position.y) / 2,
                )
                new_level = wm1.level + 1

                self.physics.remove(wm1.body, wm1.shape)
                self.physics.remove(wm2.body, wm2.shape)
                self.watermelons.remove(wm1)
                self.watermelons.remove(wm2)

                new_wm = Watermelon(new_pos, new_level, MOVING)
                self.physics.add(new_wm.body, new_wm.shape)
                self.watermelons.append(new_wm)
                self.score = max(self.score, new_level)

                self.physics.merge_pairs.remove((wm1, wm2))

    def _check_collision(self, wm1, wm2):
        distance = math.hypot(
            wm1.body.position.x - wm2.body.position.x,
            wm1.body.position.y - wm2.body.position.y,
        )
        return distance < (wm1.radius + wm2.radius) * 0.9

    def _update(self):
        if not self.can_spawn:
            self.cooldown -= 1 / FPS
            if self.cooldown <= 0:
                self.can_spawn = True
                new_wm = Watermelon((WIDTH // 2, 50), 1, WAITING)
                safe = True
                for wm in self.watermelons:
                    if self._check_collision(new_wm, wm):
                        safe = False
                        break
                if safe:
                    self.watermelons.append(new_wm)
                    self.waiting_wm = new_wm
                else:
                    self.game_over = True
        for wm in self.watermelons:
            wm.update()
        self._process_merges()

    def _draw(self):
        self.screen.fill((245, 245, 220))  # 米色背景

        # 绘制所有西瓜
        for wm in sorted(self.watermelons, key=lambda x: x.body.position.y):
            wm.draw(self.screen)

        # 绘制分数
        font = pygame.font.Font(None, 36)
        text = font.render(f"Score: {self.score}", True, (30, 30, 30))
        self.screen.blit(text, (10, 10))

        # 游戏结束提示
        if self.game_over:
            text = font.render("Game Over! Press R to restart", True, (255, 0, 0))
            rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.blit(text, rect)

        pygame.display.flip()

    def run(self):
        while True:
            self._handle_input()
            if not self.game_over:
                self._update()
                self.physics.step(1 / FPS)
            self._draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    game = Game()
    game.run()
