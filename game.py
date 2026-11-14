from collections import deque
from pathlib import Path
import random

import pygame

WINDOW_SIZE = (1280, 720)
MAP_SCALE = 3
GRID_TILE_SIZE = 16
GRID_SAMPLE_STEP = 4
BACKGROUND_COLOR_TOLERANCE = 28
BLACK_SAMPLE_RATIO = 0.5
SPEED = 300
FRAME_SIZE = (96, 96)
FRAME_DURATION = 0.12
LOADING_SCREEN_DURATION_MS = 1500
HITBOX_HALF = (18, 12)
DIRECTIONS = ("down", "right", "up", "left")
ENTRANCE_FRACTION = (0.13, 0.65)
SNAKE_SPEED = 185
SNAKE_SIZE = (60, 60)
SNAKE_FRAME_DURATION = 0.1
LAUNCHPAD_AREA = (630, 347, 41, 36)
PORTAL_LANDING = (689, 135)
PORTAL_LAUNCH_ARRIVAL = (664, 216)
PORTAL_INTERACTION_DISTANCE = 32 * MAP_SCALE
MAX_HEALTH = 100
ATTACK_DAMAGE = 25
ATTACK_RANGE = 85
CONTACT_DAMAGE = 20
CONTACT_COOLDOWN = 0.8
SNAKE_RESPAWN_MS = 30_000
ORE_COUNT = 24
ORE_HITS = 5
MINING_RANGE = 85
MINING_FRAME_MS = 50
LAUNCHPAD_COST = 5
ORE_SIZE = (48, 48)
PORTAL_ORE_CLEARANCE_TILES = 5
NPC_SIZE = (64, 96)
NPC_COLLISION_DISTANCE = 58
SHOP_INTERACTION_DISTANCE = 144
ORE_IMAGE_FILES = (
    "stoneore.png",
    "Screenshot_2026-11-14_at_11.55.42_AM-removebg-preview.png",
    "Screenshot_2026-11-14_at_11.55.42_AM__2_-removebg-preview.png",
)


def get_background_color(cave_img: pygame.Surface) -> tuple[int, int, int]:
    return cave_img.get_at((0, 0))[:3]


def is_black_sample(color: pygame.Color, background: tuple[int, int, int]) -> bool:
    channel_differences = (
        abs(color.r - background[0]),
        abs(color.g - background[1]),
        abs(color.b - background[2]),
    )
    return sum(channel_differences) <= BACKGROUND_COLOR_TOLERANCE


def build_grid(cave_img: pygame.Surface) -> list[list[bool]]:
    bg = get_background_color(cave_img)
    grid = []

    for row_start in range(0, cave_img.get_height(), GRID_TILE_SIZE):
        row = []
        for col_start in range(0, cave_img.get_width(), GRID_TILE_SIZE):
            total = 0
            black = 0
            row_end = min(row_start + GRID_TILE_SIZE, cave_img.get_height())
            col_end = min(col_start + GRID_TILE_SIZE, cave_img.get_width())

            for y in range(row_start, row_end, GRID_SAMPLE_STEP):
                for x in range(col_start, col_end, GRID_SAMPLE_STEP):
                    total += 1
                    if is_black_sample(cave_img.get_at((x, y)), bg):
                        black += 1

            row.append(black / total >= BLACK_SAMPLE_RATIO)
        grid.append(row)

    return grid


def can_stand(pos: pygame.Vector2, grid: list[list[bool]], tile_sz: int) -> bool:
    w, h = HITBOX_HALF
    left = int((pos.x - w) // tile_sz)
    right = int((pos.x + w) // tile_sz)
    top = int((pos.y - h) // tile_sz)
    bottom = int((pos.y + h) // tile_sz)

    for r in range(top, bottom + 1):
        for c in range(left, right + 1):
            if r < 0 or c < 0 or r >= len(grid) or c >= len(grid[r]) or grid[r][c]:
                return False
    return True


def find_spawn(target: pygame.Vector2, grid: list[list[bool]], tile_sz: int) -> pygame.Vector2:
    start_c = int(target.x // tile_sz)
    start_r = int(target.y // tile_sz)
    start_c = max(0, min(start_c, len(grid[0]) - 1))
    start_r = max(0, min(start_r, len(grid) - 1))

    q = deque([(start_r, start_c)])
    seen = {(start_r, start_c)}

    while q:
        r, c = q.popleft()
        tile_center = pygame.Vector2((c + 0.5) * tile_sz, (r + 0.5) * tile_sz)
        if can_stand(tile_center, grid, tile_sz):
            return tile_center

        for nr, nc in ((r - 1, c), (r, c + 1), (r + 1, c), (r, c - 1)):
            n = (nr, nc)
            if 0 <= nr < len(grid) and 0 <= nc < len(grid[nr]) and n not in seen:
                seen.add(n)
                q.append(n)

    raise ValueError("No walkable spawn found on cave map.")


def load_sprites(dir_path: Path) -> dict[str, list[pygame.Surface]]:
    return {
        dir: [
            pygame.transform.scale(
                pygame.image.load(dir_path / "walk" / dir / f"{i}.png").convert_alpha(),
                FRAME_SIZE,
            )
            for i in range(1, 10)
        ]
        for dir in DIRECTIONS
    }


def load_ore_images(img_dir: Path) -> list[pygame.Surface]:
    return [
        pygame.transform.scale(
            pygame.image.load(img_dir / filename).convert_alpha(),
            ORE_SIZE,
        )
        for filename in ORE_IMAGE_FILES
    ]


def scatter_ores(
    grid,
    tile_size,
    player_pos,
    snake_pos,
    npc_pos,
    portal_pos,
    ore_images,
    excluded_area,
):
    candidates = []
    for row, tiles in enumerate(grid):
        for col, blocked in enumerate(tiles):
            if blocked:
                continue

            position = pygame.Vector2(
                (col + 0.5) * tile_size,
                (row + 0.5) * tile_size,
            )
            if not can_stand(position, grid, tile_size):
                continue
            if position.distance_to(player_pos) < 3 * tile_size:
                continue
            if position.distance_to(snake_pos) < 3 * tile_size:
                continue
            if position.distance_to(npc_pos) < 3 * tile_size:
                continue
            if position.distance_to(portal_pos) < PORTAL_ORE_CLEARANCE_TILES * tile_size:
                continue
            if excluded_area.collidepoint(position):
                continue
            candidates.append(position)

    random.shuffle(candidates)
    ores = []
    for position in candidates:
        if any(position.distance_to(other_pos) < 2 * tile_size for other_pos, _ in ores):
            continue
        ores.append((position, random.choice(ore_images)))
        if len(ores) == ORE_COUNT:
            break
    return ores


def cave_routes(grid, tile_size):
    routes = {}
    for row, tiles in enumerate(grid):
        for col, blocked in enumerate(tiles):
            if not blocked:
                center = pygame.Vector2((col + 0.5) * tile_size, (row + 0.5) * tile_size)
                if can_stand(center, grid, tile_size):
                    routes[col, row] = center

    neighbors = {}
    for col, row in routes:
        adjacent = ((col, row - 1), (col + 1, row), (col, row + 1), (col - 1, row))
        neighbors[col, row] = [tile for tile in adjacent if tile in routes]
    return routes, neighbors


def find_routes(start, neighbors):
    previous = {start: None}
    queue = deque([start])
    while queue:
        tile = queue.popleft()
        for next_tile in neighbors[tile]:
            if next_tile not in previous:
                previous[next_tile] = tile
                queue.append(next_tile)
    return previous


def find_shopkeeper_position(player_pos, grid, tile_size):
    centers, neighbors = cave_routes(grid, tile_size)
    start = int(player_pos.x // tile_size), int(player_pos.y // tile_size)
    reachable = find_routes(start, neighbors)
    far_corner = pygame.Vector2(
        (len(grid[0]) - 0.5) * tile_size,
        0.5 * tile_size,
    )
    distant_positions = [
        centers[tile]
        for tile in reachable
        if centers[tile].distance_to(player_pos) >= 5 * tile_size
    ]
    if not distant_positions:
        distant_positions = [centers[tile] for tile in reachable]
    return min(distant_positions, key=lambda pos: pos.distance_to(far_corner))


class Snake:
    def __init__(self, img_dir, player_pos, grid, tile_size):
        self.grid = grid
        self.tile_size = tile_size
        self.centers, self.neighbors = cave_routes(grid, tile_size)
        start = self.tile_at(player_pos)
        reachable = find_routes(start, self.neighbors)
        self.tile = next(
            (tile for tile in reachable if self.centers[tile].distance_to(player_pos) >= 7 * tile_size),
            next(reversed(reachable)),
        )
        self.pos = self.centers[self.tile].copy()
        self.next_tile = self.tile
        self.player_tile = None
        self.routes = {}
        self.facing = "down"
        self.anim_timer = 0
        self.idle = {}
        self.walk = {}

        folder = img_dir / "walk" / "snake"
        for direction in DIRECTIONS:
            sprite = pygame.image.load(folder / f"snake_{direction}.png").convert_alpha()
            self.idle[direction] = pygame.transform.scale(sprite, SNAKE_SIZE)
            strip = pygame.image.load(folder / f"snake_{direction}_movement.png").convert_alpha()
            with pygame.PixelArray(strip) as pixels:
                pixels.replace((255, 255, 255, 255), (0, 0, 0, 0))
                pixels.replace((76, 76, 76, 255), (34, 177, 76, 255))
                pixels.replace((36, 36, 36, 255), (237, 28, 36, 255))
            size = strip.get_height()
            self.walk[direction] = [
                pygame.transform.scale(strip.subsurface((x, 0, size, size)), SNAKE_SIZE)
                for x in range(0, strip.get_width(), size)
            ]

    def tile_at(self, pos):
        return int(pos.x // self.tile_size), int(pos.y // self.tile_size)

    def update(self, player_pos, dt):
        player_tile = self.tile_at(player_pos)
        if player_tile != self.player_tile:
            self.player_tile = player_tile
            self.routes = find_routes(player_tile, self.neighbors) if player_tile in self.neighbors else {}

        if self.pos == self.centers[self.next_tile]:
            self.tile = self.next_tile
            self.next_tile = self.routes.get(self.tile) or self.tile

        target = self.centers[self.next_tile]
        if self.tile == self.next_tile == player_tile:
            target = player_pos

        step = self.pos.move_towards(target, SNAKE_SPEED * dt)
        old_pos = self.pos.copy()
        if can_stand(pygame.Vector2(step.x, self.pos.y), self.grid, self.tile_size):
            self.pos.x = step.x
        if can_stand(pygame.Vector2(self.pos.x, step.y), self.grid, self.tile_size):
            self.pos.y = step.y

        move = self.pos - old_pos
        if not move.length_squared():
            self.anim_timer = 0
            return self.idle[self.facing]

        if abs(move.x) > abs(move.y):
            self.facing = "right" if move.x > 0 else "left"
        else:
            self.facing = "down" if move.y > 0 else "up"

        frames = self.walk[self.facing]
        frame = frames[int(self.anim_timer / SNAKE_FRAME_DURATION) % len(frames)]
        self.anim_timer += dt
        return frame


def show_main_menu(screen: pygame.Surface, clock, img_dir: Path) -> bool:
    background = pygame.image.load(img_dir / "mainmenubg.png").convert()
    background = pygame.transform.scale(background, screen.get_size())
    button_font = pygame.font.Font(None, 44)
    start_button = pygame.Rect(90, 490, 260, 64)
    quit_button = pygame.Rect(90, 570, 260, 64)

    while True:
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return True
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_button.collidepoint(event.pos):
                    return True
                if quit_button.collidepoint(event.pos):
                    return False

        screen.blit(background, (0, 0))
        for label, button in (
            ("Start Game", start_button),
            ("Quit", quit_button),
        ):
            hovered = button.collidepoint(mouse_pos)
            fill = (35, 44, 49, 220) if hovered else (12, 19, 24, 190)
            button_surface = pygame.Surface(button.size, pygame.SRCALPHA)
            button_surface.fill(fill)
            screen.blit(button_surface, button.topleft)
            pygame.draw.rect(screen, (213, 105, 117), button, 2, border_radius=8)

            text = button_font.render(label, True, (245, 230, 225))
            screen.blit(text, text.get_rect(center=button.center))

        pygame.display.flip()
        clock.tick(60)


def show_loading_screen(screen: pygame.Surface) -> int:
    screen.fill((0, 0, 0))
    loading_font = pygame.font.Font(None, 40)
    loading_text = loading_font.render("loading", True, (255, 255, 255))
    screen.blit(loading_text, loading_text.get_rect(center=screen.get_rect().center))
    pygame.display.flip()
    return pygame.time.get_ticks()


def keep_loading_screen_visible(clock, shown_at: int) -> bool:
    while pygame.time.get_ticks() - shown_at < LOADING_SCREEN_DURATION_MS:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
        clock.tick(60)
    return True


def show_intro_screen(screen: pygame.Surface, clock) -> bool:
    story_font = pygame.font.Font(None, 42)
    prompt_font = pygame.font.Font(None, 30)
    story_lines = (
        "The cave you were exploring has collapsed!",
        "You must mine some ores and buy a launch pad to",
        "BOUNCE BACK out of the cave.",
        "Also watch out for the snek."
    )

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_SPACE,
            ):
                return True

        screen.fill((0, 0, 0))
        for line_number, line in enumerate(story_lines):
            text = story_font.render(line, True, (255, 255, 255))
            screen.blit(
                text,
                text.get_rect(center=(screen.get_width() // 2, 260 + line_number * 56)),
            )

        prompt = prompt_font.render(
            "Use WASD to move. Press Enter or Space to begin.",
            True,
            (255, 255, 255),
        )
        screen.blit(
            prompt,
            prompt.get_rect(center=(screen.get_width() // 2, 500)),
        )
        pygame.display.flip()
        clock.tick(60)


def show_shop_menu(screen, clock, ore_count, owns_launchpad):
    title_font = pygame.font.Font(None, 56)
    item_font = pygame.font.Font(None, 38)
    prompt_font = pygame.font.Font(None, 28)
    center_x = screen.get_width() // 2
    buy_button = pygame.Rect(0, 0, 210, 48)
    buy_button.center = (center_x, 410)

    while True:
        can_buy = not owns_launchpad and ore_count >= LAUNCHPAD_COST
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, ore_count, owns_launchpad
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_ESCAPE):
                return True, ore_count, owns_launchpad
            if (
                can_buy and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1 and buy_button.collidepoint(event.pos)
            ):
                ore_count -= LAUNCHPAD_COST
                owns_launchpad = True
                can_buy = False

        screen.fill((18, 22, 27))
        title = title_font.render("Shop", True, (245, 230, 225))
        item = item_font.render(f"Launch Pad - {LAUNCHPAD_COST} ores", True, (235, 205, 145))
        balance = prompt_font.render(f"Ores: {ore_count}", True, (220, 220, 220))
        label = "Buy" if can_buy else "Purchased" if owns_launchpad else "Need more ores"
        button_text = prompt_font.render(label, True, (245, 230, 225))
        prompt = prompt_font.render("Press E or Esc to return", True, (220, 220, 220))
        screen.blit(title, title.get_rect(center=(center_x, 220)))
        screen.blit(balance, balance.get_rect(center=(center_x, 275)))
        screen.blit(item, item.get_rect(center=(center_x, 330)))
        pygame.draw.rect(screen, (128, 74, 44) if can_buy else (61, 63, 67), buy_button)
        screen.blit(button_text, button_text.get_rect(center=buy_button.center))
        screen.blit(prompt, prompt.get_rect(center=(center_x, 500)))
        pygame.display.flip()
        clock.tick(60)


def load_mining_frames(img_dir):
    strip = pygame.image.load(img_dir / "mining_animation.png").convert()
    size = strip.get_height()
    frames = []
    for x in range(0, strip.get_width(), size):
        frame = pygame.transform.scale(strip.subsurface((x, 0, size, size)), FRAME_SIZE)
        frame.set_colorkey((255, 255, 255))
        frames.append(frame)
    return frames


def draw_health_bar(screen, frame, position, health, color):
    x, y = position
    width, height = frame.get_size()
    fill = pygame.Rect(x + 5, y + 7, width - 11, height - 14)
    pygame.draw.rect(screen, (35, 22, 24), fill)
    fill.width = round(fill.width * health / MAX_HEALTH)
    pygame.draw.rect(screen, color, fill)
    screen.blit(frame, position)


def show_credits(screen, clock):
    credits_lines = (
        "Credits",
        "",
        "Jonathan Alsgaard - Game Idea, Programmer",
        "Essa Khan - Artist, Developer",
        "Declyn Edwards - Lead Artist",
        "Made for Hackclub 2026",
        "HAVEN DC BABY",
    )
    heading_font = pygame.font.Font(None, 56)
    credits_font = pygame.font.Font(None, 42)
    scroll_y = float(screen.get_height())
    line_spacing = 56

    while scroll_y + len(credits_lines) * line_spacing > 0:
        dt = clock.tick(60) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_ESCAPE,
            ):
                return

        screen.fill((0, 0, 0))
        for line_number, line in enumerate(credits_lines):
            if not line:
                continue
            font = heading_font if line_number == 0 else credits_font
            text = font.render(line, True, (255, 255, 255))
            line_rect = text.get_rect(
                center=(screen.get_width() // 2, round(scroll_y + line_number * line_spacing))
            )
            screen.blit(text, line_rect)
        pygame.display.flip()
        scroll_y -= 70 * dt


def run_game() -> None:
    screen = pygame.display.set_mode(WINDOW_SIZE)
    clock = pygame.time.Clock()
    img_dir = Path(__file__).resolve().parent / "images"

    if not show_main_menu(screen, clock, img_dir):
        return

    loading_started_at = show_loading_screen(screen)
    raw_map = pygame.image.load(img_dir / "cavemap.png").convert()
    world = pygame.transform.scale(raw_map, (raw_map.get_width() * MAP_SCALE, raw_map.get_height() * MAP_SCALE))
    grid = build_grid(raw_map)
    tile_size = GRID_TILE_SIZE * MAP_SCALE
    sprites = load_sprites(img_dir)
    ore_images = load_ore_images(img_dir)
    mining_frames = load_mining_frames(img_dir)
    mining_started = None
    mining_target = None
    ore_count = 0
    owns_launchpad = False
    health_bar = pygame.image.load(img_dir / "health_bar.png").convert_alpha()
    death_message = pygame.font.Font(None, 44).render(
        "You died. Press Enter to respawn.", True, (255, 255, 255)
    )

    launchpad_area = pygame.Rect(*(value * MAP_SCALE for value in LAUNCHPAD_AREA))
    ore_spawn_exclusion = launchpad_area.inflate(*ORE_SIZE)
    launchpad = pygame.image.load(img_dir / "pixil-frame-0(2).png").convert_alpha()
    launchpad = launchpad.subsurface(launchpad.get_bounding_rect())
    pad_width = launchpad_area.width
    pad_height = round(launchpad.get_height() * pad_width / launchpad.get_width())
    launchpad = pygame.transform.scale(launchpad, (pad_width, pad_height))
    launchpad_placed = False
    portal_pos = find_spawn(pygame.Vector2(PORTAL_LANDING) * MAP_SCALE, grid, tile_size)
    launch_arrival_pos = find_spawn(
        pygame.Vector2(PORTAL_LAUNCH_ARRIVAL) * MAP_SCALE, grid, tile_size
    )

    spawn_x, spawn_y = ENTRANCE_FRACTION
    spawn_target = pygame.Vector2(raw_map.get_width() * spawn_x, raw_map.get_height() * spawn_y) * MAP_SCALE
    entrance_pos = find_spawn(spawn_target, grid, tile_size)
    pos = entrance_pos.copy()
    player_health = MAX_HEALTH
    snake_health = MAX_HEALTH
    contact_cooldown = 0.0

    shopkeeper = pygame.image.load(img_dir / "pixilart-drawing.png").convert_alpha()
    shopkeeper = pygame.transform.scale(shopkeeper, NPC_SIZE)
    shopkeeper_pos = find_shopkeeper_position(pos, grid, tile_size)
    snake = Snake(img_dir, pos, grid, tile_size)
    snake_spawn_tile = snake.tile
    snake_respawn_at = None
    ores = scatter_ores(
        grid,
        tile_size,
        pos,
        snake.pos,
        shopkeeper_pos,
        portal_pos,
        ore_images,
        ore_spawn_exclusion,
    )
    ores = [(position, sprite, ORE_HITS) for position, sprite in ores]

    if not keep_loading_screen_visible(clock, loading_started_at):
        return

    if not show_intro_screen(screen, clock):
        return

    center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
    facing = "down"
    anim_timer = 0.0
    prompt_font = pygame.font.Font(None, 28)
    running = True

    while running:
        dt = min(clock.tick(60) / 1000, 0.05)
        near_shopkeeper = pos.distance_to(shopkeeper_pos) <= SHOP_INTERACTION_DISTANCE

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif player_health == 0:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    player_health = MAX_HEALTH
                    pos = entrance_pos.copy()
                    contact_cooldown = CONTACT_COOLDOWN
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if snake_health > 0 and pos.distance_to(snake.pos) <= ATTACK_RANGE:
                    snake_health = max(0, snake_health - ATTACK_DAMAGE)
                    if snake_health == 0:
                        snake_respawn_at = pygame.time.get_ticks() + SNAKE_RESPAWN_MS
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mining_started = None
                mining_target = None
                if ores:
                    index = min(range(len(ores)), key=lambda i: pos.distance_squared_to(ores[i][0]))
                    ore_pos, ore_image, hits_left = ores[index]
                    if pos.distance_to(ore_pos) <= MINING_RANGE:
                        mining_started = pygame.time.get_ticks()
                        mining_target = ore_pos.copy()
                        if hits_left == 1:
                            ores.pop(index)
                            ore_count += 1
                        else:
                            ores[index] = (ore_pos, ore_image, hits_left - 1)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_z:
                if owns_launchpad and launchpad_area.collidepoint(pos.x, pos.y):
                    if launchpad_placed:
                        pos = launch_arrival_pos.copy()
                    else:
                        launchpad_placed = True
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_e
                and near_shopkeeper
            ):
                running, ore_count, owns_launchpad = show_shop_menu(
                    screen, clock, ore_count, owns_launchpad
                )
                break

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(int(keys[pygame.K_d]) - int(keys[pygame.K_a]), int(keys[pygame.K_s]) - int(keys[pygame.K_w]))
        has_input = player_health > 0 and move.length_squared() > 0

        if has_input:
            move = move.normalize()
            if abs(move.x) > abs(move.y):
                facing = "right" if move.x > 0 else "left"
            else:
                facing = "down" if move.y > 0 else "up"

        prev_pos = pos.copy()
        if has_input:
            step_x = move.x * SPEED * dt
            cand = pygame.Vector2(pos.x + step_x, pos.y)
            if (
                can_stand(cand, grid, tile_size)
                and cand.distance_to(shopkeeper_pos) >= NPC_COLLISION_DISTANCE
            ):
                pos.x = cand.x

            step_y = move.y * SPEED * dt
            cand = pygame.Vector2(pos.x, pos.y + step_y)
            if (
                can_stand(cand, grid, tile_size)
                and cand.distance_to(shopkeeper_pos) >= NPC_COLLISION_DISTANCE
            ):
                pos.y = cand.y

        if (
            player_health > 0
            and pos.distance_to(portal_pos) <= PORTAL_INTERACTION_DISTANCE
        ):
            show_credits(screen, clock)
            return

        is_moving = pos != prev_pos
        if is_moving:
            anim_timer += dt
        else:
            anim_timer = 0.0

        frames = sprites[facing]
        frame_idx = int(anim_timer / FRAME_DURATION) % len(frames)
        current_frame = frames[frame_idx if is_moving else 0]
        mining_frame = None
        if mining_started is not None:
            mining_frame = (pygame.time.get_ticks() - mining_started) // MINING_FRAME_MS
            if player_health == 0 or mining_frame >= len(mining_frames):
                mining_started = None
                mining_target = None

        if snake_respawn_at is not None and pygame.time.get_ticks() >= snake_respawn_at:
            snake.tile = snake.next_tile = snake_spawn_tile
            snake.pos = snake.centers[snake_spawn_tile].copy()
            snake.facing = "down"
            snake.anim_timer = 0.0
            snake_health = MAX_HEALTH
            snake_respawn_at = None

        if snake_health > 0:
            snake_frame = snake.update(pos, dt if player_health > 0 else 0)
            contact_cooldown = max(0, contact_cooldown - dt)
            dx, dy = snake.pos - pos
            if contact_cooldown == 0 and abs(dx) < 2 * HITBOX_HALF[0] and abs(dy) < 2 * HITBOX_HALF[1]:
                player_health = max(0, player_health - CONTACT_DAMAGE)
                contact_cooldown = CONTACT_COOLDOWN

        cam_x = max(0, min(pos.x - center.x, world.get_width() - screen.get_width()))
        cam_y = max(0, min(pos.y - center.y, world.get_height() - screen.get_height()))

        screen.fill((0, 0, 0))
        screen.blit(world, (-round(cam_x), -round(cam_y)))
        for ore_pos, ore_image, _ in ores:
            ore_rect = ore_image.get_rect(
                center=(round(ore_pos.x - cam_x), round(ore_pos.y - cam_y))
            )
            screen.blit(ore_image, ore_rect)
        if launchpad_placed:
            pad_rect = launchpad.get_rect(center=launchpad_area.center)
            screen.blit(launchpad, pad_rect.move(-round(cam_x), -round(cam_y)))
        shopkeeper_rect = shopkeeper.get_rect(
            center=(round(shopkeeper_pos.x - cam_x), round(shopkeeper_pos.y - cam_y))
        )
        screen.blit(shopkeeper, shopkeeper_rect)
        if snake_health > 0:
            snake_rect = snake_frame.get_rect(center=(round(snake.pos.x - cam_x), round(snake.pos.y - cam_y)))
            screen.blit(snake_frame, snake_rect)
        player_rect = current_frame.get_rect(center=(round(pos.x - cam_x), round(pos.y - cam_y)))
        screen.blit(current_frame, player_rect)
        if mining_target is not None and mining_frame is not None:
            mining_effect = mining_frames[mining_frame]
            mining_rect = mining_effect.get_rect(
                center=(
                    round(mining_target.x - cam_x),
                    round(mining_target.y - cam_y),
                )
            )
            screen.blit(mining_effect, mining_rect)
        if near_shopkeeper:
            prompt = prompt_font.render(
                "Press E to enter shop menu", True, (255, 255, 255)
            )
            prompt_rect = prompt.get_rect(
                center=(screen.get_width() // 2, screen.get_height() - 48)
            )
            pygame.draw.rect(screen, (20, 24, 28), prompt_rect.inflate(24, 14))
            screen.blit(prompt, prompt_rect)
        if snake_health > 0:
            bar_pos = (snake_rect.centerx - health_bar.get_width() // 2, snake_rect.top - health_bar.get_height())
            draw_health_bar(screen, health_bar, bar_pos, snake_health, (216, 107, 48))
        draw_health_bar(screen, health_bar, (16, 16), player_health, (208, 55, 68))
        ore_text = prompt_font.render(f"Ores: {ore_count}", True, (255, 255, 255))
        ore_rect = ore_text.get_rect(topleft=(20, 56))
        pygame.draw.rect(screen, (20, 24, 28), ore_rect.inflate(8, 6))
        screen.blit(ore_text, ore_rect)
        if player_health == 0:
            message_rect = death_message.get_rect(center=screen.get_rect().center)
            pygame.draw.rect(screen, (26, 17, 20), message_rect.inflate(32, 20))
            screen.blit(death_message, message_rect)
        pygame.display.flip()


def main() -> None:
    pygame.init()
    try:
        run_game()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()