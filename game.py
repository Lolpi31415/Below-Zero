from pathlib import Path
import pygame

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True


# get the folder with the animatoins and inmages
images_dir = Path(__file__).resolve().parent / "images"

map_surface = pygame.image.load(images_dir / "cavemap.png").convert()
zoom = 3
bg = pygame.transform.scale(
    map_surface,
    (map_surface.get_width() * zoom, map_surface.get_height() * zoom),
)

grid_cell_size = 16
world_cell_size = grid_cell_size * zoom
background_color = map_surface.get_at((0, 0))[:3]
wall_grid = []
for grid_y in range(0, map_surface.get_height(), grid_cell_size):
    row = []
    for grid_x in range(0, map_surface.get_width(), grid_cell_size):
        samples = 0
        wall_samples = 0
        for y in range(grid_y, min(grid_y + grid_cell_size, map_surface.get_height()), 4):
            for x in range(grid_x, min(grid_x + grid_cell_size, map_surface.get_width()), 4):
                color = map_surface.get_at((x, y))
                color_distance = sum(
                    abs(color[channel] - background_color[channel])
                    for channel in range(3)
                )
                samples += 1
                if color_distance > 28:
                    wall_samples += 1
        row.append(wall_samples / samples >= 0.25)
    wall_grid.append(row)

grid_height = len(wall_grid)
grid_width = len(wall_grid[0])
player_half_width = 18
player_half_height = 12


def can_move_to(position):
    left = int((position.x - player_half_width) // world_cell_size)
    right = int((position.x + player_half_width) // world_cell_size)
    top = int((position.y - player_half_height) // world_cell_size)
    bottom = int((position.y + player_half_height) // world_cell_size)

    for grid_y in range(top, bottom + 1):
        for grid_x in range(left, right + 1):
            if (
                grid_x < 0
                or grid_y < 0
                or grid_x >= grid_width
                or grid_y >= grid_height
                or wall_grid[grid_y][grid_x]
            ):
                return False
    return True


def nearest_walkable_position(target):
    candidates = []
    for grid_y, row in enumerate(wall_grid):
        for grid_x, is_wall in enumerate(row):
            if not is_wall:
                position = pygame.Vector2(
                    (grid_x + 0.5) * world_cell_size,
                    (grid_y + 0.5) * world_cell_size,
                )
                candidates.append(
                    ((position - target).length_squared(), position)
                )

    for _, position in sorted(candidates, key=lambda candidate: candidate[0]):
        if can_move_to(position):
            return position

    raise ValueError("The cave map has no walkable spawn position.")


walk_frames = {
    direction: [
        pygame.transform.scale(
          #get the right folder for animatoins
            pygame.image.load(
                images_dir / "walk" / direction / f"{frame}.png"
            ).convert_alpha(),
            (80, 80),
        )
        for frame in range(1, 10)
    ]
    for direction in ("down", "right", "up", "left")
}
facing = "down"
animation_time = 0.0
animation_speed = 0.12

# Spawn at the foot of the lit entrance stairs near the upper-right of the map.
entrance_spawn = pygame.Vector2(
    map_surface.get_width() * 0.87,
    map_surface.get_height() * 0.45,
) * zoom
player_world_pos = nearest_walkable_position(entrance_spawn)

# make  the players screen i sin the middle
screen_center = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)




while running:
  dt = clock.tick(60) / 1000

  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      running = False

  keys = pygame.key.get_pressed()
  movement = pygame.Vector2(0, 0)
  if keys[pygame.K_w]:
    movement.y -= 1
  if keys[pygame.K_s]:
    movement.y += 1
  if keys[pygame.K_a]:
    movement.x -= 1
  if keys[pygame.K_d]:
    movement.x += 1

  has_input = movement.length_squared() > 0
  if has_input:
    movement = movement.normalize()
    if abs(movement.x) > abs(movement.y):
      facing = "right" if movement.x > 0 else "left"
    else:
      facing = "down" if movement.y > 0 else "up"

  previous_pos = player_world_pos.copy()
  if has_input:
    next_pos = player_world_pos.copy()
    next_pos.x += movement.x * 300 * dt
    if can_move_to(next_pos):
      player_world_pos.x = next_pos.x

    next_pos = player_world_pos.copy()
    next_pos.y += movement.y * 300 * dt
    if can_move_to(next_pos):
      player_world_pos.y = next_pos.y

  moving = player_world_pos != previous_pos
  if moving:
    animation_time += dt
  else:
    animation_time = 0.0

  frame_index = int(animation_time / animation_speed) % len(walk_frames[facing])

  camera_x = max(
      0,
      min(
          player_world_pos.x - screen_center.x,
          bg.get_width() - screen.get_width(),
      ),
  )
  camera_y = max(
      0,
      min(
          player_world_pos.y - screen_center.y,
          bg.get_height() - screen.get_height(),
      ),
  )

  # have bg black in order to have the ouside of map look like the void
  screen.fill((0, 0, 0))

  screen.blit(bg, (-round(camera_x), -round(camera_y)))
# players pov
  current_frame = walk_frames[facing][frame_index if moving else 0]
  player_rect = current_frame.get_rect(
      center=(
          round(player_world_pos.x - camera_x),
          round(player_world_pos.y - camera_y),
      )
  )
  screen.blit(current_frame, player_rect)

  pygame.display.flip()

pygame.quit()
