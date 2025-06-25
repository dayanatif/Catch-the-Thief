import pygame
import asyncio
import platform
import heapq
from collections import deque
import random
import math
import numpy as np

WIDTH, HEIGHT = 600, 600
GRID_SIZE = 20
CELL_SIZE = WIDTH // GRID_SIZE
FPS = 60
LEVEL_TIME_LIMIT = 60

# Colors
NEON_PINK = (255, 0, 127)
NEON_BLUE = (0, 209, 255)
NEON_RED = (255, 0, 0)
DEEP_PURPLE = (42, 0, 79)
WHITE = (255, 255, 255)
GRAY = (80, 80, 80)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
POWER_UP_COLOR = (200, 0, 200)
PATH_COLOR = (30, 30, 30)

highscore = 0
particles = []
screen_shake = 0

def generate_valid_grid():
    for _ in range(10):
        grid = [[0 if random.random() > 0.3 else 1 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        grid[0][0] = 0
        grid[GRID_SIZE-1][GRID_SIZE-1] = 0
        path = bfs_path((0, 0), (GRID_SIZE-1, GRID_SIZE-1), grid)
        if path:
            return grid, True
    grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    grid[0][0] = 0
    grid[GRID_SIZE-1][GRID_SIZE-1] = 0
    return grid, False

def bfs_path(start, target, grid):
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == target:
            return path + [(x, y)]
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            new_x, new_y = x + dx, y + dy
            if 0 <= new_x < GRID_SIZE and 0 <= new_y < GRID_SIZE and grid[new_x][new_y] != 1 and (new_x, new_y) not in visited:
                visited.add((new_x, new_y))
                queue.append(((new_x, new_y), path + [(x, y)]))
    return []

city_grid, valid_grid = generate_valid_grid()
power_ups = []
road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
for _ in range(3):
    if road_cells:
        x, y = random.choice(road_cells)
        city_grid[x][y] = 2
        power_ups.append((x, y))
        road_cells.remove((x, y))

police_pos = [0, 0]
thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
caught = False
game_state = "welcome"
difficulty = "Medium"
difficulty_probs = {
    "Easy": {"random": 0.7, "avoid": 0.2, "stay": 0.1},
    "Medium": {"random": 0.4, "avoid": 0.5, "stay": 0.1},
    "Hard": {"random": 0.1, "avoid": 0.8, "stay": 0.1}
}
start_time = 0
score = 0
police_auto = True
paused = False
pause_start_time = 0
total_pause_time = 0
power_up_active = False
power_up_timer = 0
move_interval = 0.5
invalid_move_timer = 0
grid_warning = False
thief_stuck_counter = 0
police_stuck_counter = 0
last_thief_pos = thief_pos.copy()
last_police_pos = police_pos.copy()

resume_button_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 20, 240, 60)
mainmenu_button_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 100, 240, 60)
try_again_button_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 20, 240, 60)
quit_button_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT // 2 + 180, 240, 60)

def create_sprite(color, glow_color, size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(surface, glow_color, (0, 0, size, size), 2)
    pygame.draw.rect(surface, color, (2, 2, size-4, size-4))
    return surface

def add_particles(x, y, color, count=10):
    global particles
    for _ in range(count):
        angle = random.random() * 2 * math.pi
        speed = random.uniform(1, 3)
        particles.append({
            "pos": [x, y],
            "vel": [math.cos(angle) * speed, math.sin(angle) * speed],
            "color": color,
            "life": random.uniform(0.5, 1.5)
        })

def update_particles(dt):
    global particles
    new_particles = []
    for p in particles:
        p["pos"][0] += p["vel"][0] * dt * 60
        p["pos"][1] += p["vel"][1] * dt * 60
        p["life"] -= dt
        if p["life"] > 0:
            new_particles.append(p)
    particles = new_particles

def setup():
    global screen, clock, font, title_font, button_rect, difficulty_rects, click_sound, catch_sound, bg_music
    global police_sprite, thief_sprite, rain_particles
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Catch the Thief")
    clock = pygame.time.Clock()
    try:
        font = pygame.font.Font(pygame.font.match_font("neuropol", "arial"), 28)
        title_font = pygame.font.Font(pygame.font.match_font("neuropol", "arial"), 72)
    except:
        font = pygame.font.SysFont("arial", 28)
        title_font = pygame.font.SysFont("arial", 72)
    
    button_rect = pygame.Rect(WIDTH // 2 - 120, HEIGHT - 160, 240, 60)
    difficulty_rects = {
        "Easy": pygame.Rect(WIDTH // 2 - 180, HEIGHT - 260, 120, 50),
        "Medium": pygame.Rect(WIDTH // 2 - 60, HEIGHT - 260, 120, 50),
        "Hard": pygame.Rect(WIDTH // 2 + 60, HEIGHT - 260, 120, 50)
    }
    
    police_sprite = create_sprite(NEON_BLUE, WHITE, CELL_SIZE)
    thief_sprite = create_sprite(NEON_RED, WHITE, CELL_SIZE)
    
    rain_particles = [{"pos": [random.randint(0, WIDTH), random.randint(0, HEIGHT // 2)], "vel": [0, random.uniform(5, 10)]} for _ in range(100)]
    
    if platform.system() != "Emscripten":
        try:
            pygame.mixer.init()
            sample_rate = 44100
            duration = 0.1
            t = np.linspace(0, duration, int(sample_rate * duration))
            click_wave = np.sin(2 * np.pi * 1000 * t)
            click_array = (click_wave * 32767).astype(np.int16)
            click_sound = pygame.mixer.Sound(click_array.tobytes())
            duration = 0.2
            t = np.linspace(0, duration, int(sample_rate * duration))
            catch_wave = np.sin(2 * np.pi * 800 * t) + np.sin(2 * np.pi * 1000 * t)
            catch_array = (catch_wave * 32767 / 2).astype(np.int16)
            catch_sound = pygame.mixer.Sound(catch_array.tobytes())
            duration = 2.0
            t = np.linspace(0, duration, int(sample_rate * duration))
            freqs = [220, 247, 262, 294]
            wave = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
            music_array = (wave * 16383).astype(np.int16)
            bg_music = pygame.mixer.Sound(music_array.tobytes())
            bg_music.set_volume(0.3)
            bg_music.play(-1)
        except Exception as e:
            print(f"Sound initialization failed: {e}")
            click_sound = None
            catch_sound = None
            bg_music = None
    else:
        click_sound = None
        catch_sound = None
        bg_music = None
    
    if platform.system() != "Emscripten":
        print("Initial Grid:")
        for row in city_grid:
            print(row)
        print(f"Valid grid: {valid_grid}")

def manhattan_distance(pos1, pos2):
    return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

def is_valid_move(x, y):
    return 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE and city_grid[x][y] != 1

def get_neighbors(pos):
    x, y = pos
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    neighbors = []
    for dx, dy in directions:
        new_x, new_y = x + dx, y + dy
        if is_valid_move(new_x, new_y):
            neighbors.append((new_x, new_y))
    return neighbors

def a_star(start, goal):
    if not is_valid_move(goal[0], goal[1]):
        return []
    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: manhattan_distance(start, goal)}
    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            return path[::-1]
        for neighbor in get_neighbors(current):
            tentative_g_score = g_score[current] + 1
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = tentative_g_score + manhattan_distance(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return []

def bfs_police_path(start, target):
    if not is_valid_move(target[0], target[1]):
        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if is_valid_move(x, y)]
        if not road_cells:
            if platform.system() != "Emscripten":
                print("No valid road cells found!")
            return []
        target = min(road_cells, key=lambda p: manhattan_distance(p, target))
    
    queue = deque([(start, [])])
    visited = {start}
    while queue:
        (x, y), path = queue.popleft()
        if (x, y) == target:
            return path + [(x, y)]
        for neighbor in get_neighbors((x, y)):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [(x, y)]))
    
    path = a_star(start, target)
    if path:
        return path
    
    neighbors = get_neighbors(start)
    if neighbors:
        return [min(neighbors, key=lambda p: manhattan_distance(p, target))]
    
    if platform.system() != "Emscripten":
        print(f"No path found from {start} to {target}!")
        for row in city_grid:
            print(row)
    return []

def decide_thief_move():
    global thief_pos, thief_stuck_counter
    distance = manhattan_distance(thief_pos, police_pos)
    probs = difficulty_probs[difficulty]
    neighbors = get_neighbors(tuple(thief_pos))
    
    if neighbors:
        choice = random.random()
        cumulative = 0
        for action, prob in [("random", probs["random"]), ("avoid", probs["avoid"]), ("stay", probs["stay"])]:
            cumulative += prob
            if choice <= cumulative:
                if action == "random":
                    return random.choice(neighbors)
                elif action == "avoid":
                    best_move = max(neighbors, key=lambda p: manhattan_distance(p, tuple(police_pos)), default=thief_pos)
                    return best_move
                return thief_pos
    return thief_pos

def draw_city_background():
    for y in range(HEIGHT):
        b = 79 - (y * (79 - 0) // HEIGHT)
        pygame.draw.line(screen, (42, 0, b), (0, y), (WIDTH, y))
    
    for _ in range(20):
        x = random.randint(0, WIDTH - 40)
        w = random.randint(30, 60)
        h = random.randint(100, 200)
        pygame.draw.rect(screen, GRAY, (x, HEIGHT - h, w, h))
        for _ in range(random.randint(3, 8)):
            wx = random.randint(x + 5, x + w - 15)
            wy = random.randint(HEIGHT - h + 10, HEIGHT - 10)
            color = random.choice([NEON_PINK, NEON_BLUE])
            pygame.draw.rect(screen, color, (wx, wy, 10, 10))
    
    for p in rain_particles:
        p["pos"][1] += p["vel"][1] * (1 / FPS)
        if p["pos"][1] > HEIGHT:
            p["pos"] = [random.randint(0, WIDTH), 0]
            p["vel"][1] = random.uniform(5, 10)
        pygame.draw.line(screen, (100, 150, 255), p["pos"], (p["pos"][0], p["pos"][1] + 5))

def draw_button(rect, text, color, hover):
    scale = 1.2 if hover else 1.0
    scaled_rect = rect.inflate(rect.width * (scale - 1), rect.height * (scale - 1))
    glow_surface = pygame.Surface((scaled_rect.width + 10, scaled_rect.height + 10), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*color, 50), (5, 5, scaled_rect.width, scaled_rect.height), border_radius=15)
    screen.blit(glow_surface, (scaled_rect.x - 5, scaled_rect.y - 5))
    pygame.draw.rect(screen, color, scaled_rect, border_radius=15)
    pygame.draw.rect(screen, WHITE if hover else BLACK, scaled_rect, 3, border_radius=15)
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=scaled_rect.center)
    screen.blit(text_surface, text_rect)

def draw_welcome():
    draw_city_background()
    title = title_font.render("Catch the Thief", True, NEON_PINK)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    glow_surface = pygame.Surface((title_rect.width + 20, title_rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*NEON_PINK, 100), (10, 10, title_rect.width, title_rect.height), border_radius=10)
    screen.blit(glow_surface, (title_rect.x - 10, title_rect.y - 10))
    screen.blit(title, title_rect)
    
    mouse_pos = pygame.mouse.get_pos()
    for diff, rect in difficulty_rects.items():
        draw_button(rect, diff, NEON_PINK if diff == difficulty else GRAY, rect.collidepoint(mouse_pos))
    draw_button(button_rect, "Play Now", NEON_BLUE, button_rect.collidepoint(mouse_pos))

def draw_grid():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            rect = pygame.Rect(y * CELL_SIZE, x * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if city_grid[x][y] == 1:
                pygame.draw.rect(screen, GRAY, rect)
                pygame.draw.rect(screen, NEON_BLUE, rect, 3)
            elif city_grid[x][y] == 2:
                pulse = 1.0 + 0.3 * math.sin(pygame.time.get_ticks() / 500.0)
                pygame.draw.circle(screen, POWER_UP_COLOR, (y * CELL_SIZE + CELL_SIZE // 2, x * CELL_SIZE + CELL_SIZE // 2), int(CELL_SIZE // 2 * pulse))
            else:
                pygame.draw.rect(screen, PATH_COLOR, rect)
                pygame.draw.rect(screen, WHITE, rect, 1)

def draw_entities(path=[]):
    global screen_shake
    offset_x = random.uniform(-screen_shake, screen_shake) if screen_shake > 0 else 0
    offset_y = random.uniform(-screen_shake, screen_shake) if screen_shake > 0 else 0
    screen_shake = max(0, screen_shake - 0.1)
    
    if invalid_move_timer > 0:
        add_particles(police_pos[1] * CELL_SIZE + CELL_SIZE // 2, police_pos[0] * CELL_SIZE + CELL_SIZE // 2, NEON_PINK, 5)
    
    screen.blit(police_sprite, (police_pos[1] * CELL_SIZE + offset_x, police_pos[0] * CELL_SIZE + offset_y))
    screen.blit(thief_sprite, (thief_pos[1] * CELL_SIZE + offset_x, thief_pos[0] * CELL_SIZE + offset_y))
    
    # Only draw path in auto mode
    if police_auto and path:
        for x, y in path:
            rect = pygame.Rect(y * CELL_SIZE + CELL_SIZE // 4 + offset_x, x * CELL_SIZE + CELL_SIZE // 4 + offset_y, CELL_SIZE // 2, CELL_SIZE // 2)
            pygame.draw.rect(screen, NEON_BLUE, rect)
    
    for p in particles:
        pygame.draw.circle(screen, p["color"], (int(p["pos"][0] + offset_x), int(p["pos"][1] + offset_y)), 2)
    
    # HUD
    hud_surface = pygame.Surface((WIDTH, 50), pygame.SRCALPHA)
    pygame.draw.rect(hud_surface, (0, 0, 0, 150), (0, 0, WIDTH, 50), border_radius=5)
    distance = manhattan_distance(police_pos, thief_pos)
    adjusted_time = pygame.time.get_ticks() - start_time - total_pause_time
    elapsed = adjusted_time // 1000
    time_left = max(0, LEVEL_TIME_LIMIT - elapsed)
    mode = "Auto" if police_auto else "Manual"
    power_up_text = f"Power-Up: {int(power_up_timer)}s" if power_up_active else ""
    warning_text = "Grid Reset!" if grid_warning else ""
    text = font.render(f"Diff: {difficulty} | Dist: {distance} | Time: {elapsed}s | Time Left: {time_left}s | Mode: {mode} | {power_up_text} | {warning_text}", True, WHITE)
    hud_surface.blit(text, (10, 10))
    screen.blit(hud_surface, (0, HEIGHT - 50))

    pulse = 1.0 + 0.2 * math.sin(pygame.time.get_ticks() / 1000.0)
    hs_text = font.render(f"Highscore: {highscore}", True, YELLOW)
    hs_rect = hs_text.get_rect(topleft=(10, 10))
    glow_surface = pygame.Surface((hs_rect.width + 10, hs_rect.height + 10), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*YELLOW, int(100 * pulse)), (5, 5, hs_rect.width, hs_rect.height))
    screen.blit(glow_surface, (hs_rect.x - 5, hs_rect.y - 5))
    screen.blit(hs_text, hs_rect)

    if paused:
        draw_pause_overlay()

def draw_pause_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))
    title_surface = title_font.render("Paused", True, NEON_PINK)
    title_rect = title_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
    glow_surface = pygame.Surface((title_rect.width + 20, title_rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*NEON_PINK, 100), (10, 10, title_rect.width, title_rect.height), border_radius=10)
    screen.blit(glow_surface, (title_rect.x - 10, title_rect.y - 10))
    screen.blit(title_surface, title_rect)
    
    mouse_pos = pygame.mouse.get_pos()
    draw_button(resume_button_rect, "Resume", NEON_BLUE, resume_button_rect.collidepoint(mouse_pos))
    draw_button(mainmenu_button_rect, "Main Menu", GRAY, mainmenu_button_rect.collidepoint(mouse_pos))
    draw_button(quit_button_rect, "Quit", GRAY, quit_button_rect.collidepoint(mouse_pos))

def draw_game_over():
    global highscore
    draw_city_background()
    
    title_surface = title_font.render("Game Over", True, NEON_PINK)
    title_rect = title_surface.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    glow_surface = pygame.Surface((title_rect.width + 20, title_rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*NEON_PINK, 100), (10, 10, title_rect.width, title_rect.height), border_radius=10)
    screen.blit(glow_surface, (title_rect.x - 10, title_rect.y - 10))
    screen.blit(title_surface, title_rect)
    
    text_surface = title_font.render("Thief Caught!", True, NEON_BLUE)
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    glow_surface = pygame.Surface((text_rect.width + 20, text_rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*NEON_BLUE, 100), (10, 10, text_rect.width, text_rect.height), border_radius=10)
    screen.blit(glow_surface, (text_rect.x - 10, text_rect.y - 10))
    screen.blit(text_surface, text_rect)
    
    adjusted_time = pygame.time.get_ticks() - start_time - total_pause_time
    elapsed = adjusted_time // 1000
    score_text = font.render(f"Score: {max(10000 - elapsed * 100, 0)} | Time: {elapsed}s", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3))
    pygame.draw.rect(screen, DEEP_PURPLE, score_rect.inflate(20, 20), border_radius=10)
    screen.blit(score_text, score_rect)
    
    score_final = max(10000 - elapsed * 100, 0)
    if score_final > highscore:
        highscore = score_final
    hs_text = font.render(f"Highscore: {highscore}", True, YELLOW)
    hs_rect = hs_text.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3 + 40))
    pygame.draw.rect(screen, DEEP_PURPLE, hs_rect.inflate(20, 20), border_radius=10)
    screen.blit(hs_text, hs_rect)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    pygame.display.flip()

def draw_game_failed():
    draw_grid()
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))
    text_surface = title_font.render("You Failed!", True, NEON_PINK)
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
    glow_surface = pygame.Surface((text_rect.width + 20, text_rect.height + 20), pygame.SRCALPHA)
    pygame.draw.rect(glow_surface, (*NEON_PINK, 100), (10, 10, text_rect.width, text_rect.height), border_radius=10)
    screen.blit(glow_surface, (text_rect.x - 10, text_rect.y - 10))
    screen.blit(text_surface, text_rect)
    
    mouse_pos = pygame.mouse.get_pos()
    draw_button(try_again_button_rect, "Try Again", NEON_BLUE, try_again_button_rect.collidepoint(mouse_pos))
    draw_button(mainmenu_button_rect, "Main Menu", GRAY, mainmenu_button_rect.collidepoint(mouse_pos))
    
    pygame.display.flip()

async def update_loop():
    global police_pos, thief_pos, caught, game_state, difficulty, start_time, score, police_auto, paused, pause_start_time, total_pause_time, power_ups, power_up_active, power_up_timer, move_interval, invalid_move_timer, city_grid, grid_warning, thief_stuck_counter, police_stuck_counter, last_thief_pos, last_police_pos, screen_shake
    global highscore
    move_timer = 0
    police_path = []
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if game_state == "welcome":
                    for diff, rect in difficulty_rects.items():
                        if rect.collidepoint(mouse_pos):
                            difficulty = diff
                            if click_sound:
                                click_sound.play()
                    if button_rect.collidepoint(mouse_pos):
                        game_state = "playing"
                        start_time = pygame.time.get_ticks()
                        total_pause_time = 0
                        if click_sound:
                            click_sound.play()
                elif game_state == "playing" and paused:
                    if resume_button_rect.collidepoint(mouse_pos):
                        paused = False
                        total_pause_time += pygame.time.get_ticks() - pause_start_time
                        if click_sound:
                            click_sound.play()
                    elif mainmenu_button_rect.collidepoint(mouse_pos) or quit_button_rect.collidepoint(mouse_pos):
                        game_state = "welcome"
                        police_pos = [0, 0]
                        thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
                        caught = False
                        police_auto = True
                        paused = False
                        power_up_active = False
                        move_interval = 0.5
                        total_pause_time = 0
                        city_grid, valid_grid = generate_valid_grid()
                        power_ups.clear()
                        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
                        for _ in range(3):
                            if road_cells:
                                x, y = random.choice(road_cells)
                                city_grid[x][y] = 2
                                power_ups.append((x, y))
                                road_cells.remove((x, y))
                        thief_stuck_counter = 0
                        police_stuck_counter = 0
                        if click_sound:
                            click_sound.play()
                elif game_state == "game_failed":
                    if try_again_button_rect.collidepoint(mouse_pos):
                        game_state = "playing"
                        police_pos = [0, 0]
                        thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
                        caught = False
                        police_auto = True
                        paused = False
                        power_up_active = False
                        move_interval = 0.5
                        total_pause_time = 0
                        city_grid, valid_grid = generate_valid_grid()
                        power_ups.clear()
                        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
                        for _ in range(3):
                            if road_cells:
                                x, y = random.choice(road_cells)
                                city_grid[x][y] = 2
                                power_ups.append((x, y))
                                road_cells.remove((x, y))
                        thief_stuck_counter = 0
                        police_stuck_counter = 0
                        start_time = pygame.time.get_ticks()
                        if click_sound:
                            click_sound.play()
                    elif mainmenu_button_rect.collidepoint(mouse_pos):
                        game_state = "welcome"
                        police_pos = [0, 0]
                        thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
                        caught = False
                        police_auto = True
                        paused = False
                        power_up_active = False
                        move_interval = 0.5
                        total_pause_time = 0
                        city_grid, valid_grid = generate_valid_grid()
                        power_ups.clear()
                        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
                        for _ in range(3):
                            if road_cells:
                                x, y = random.choice(road_cells)
                                city_grid[x][y] = 2
                                power_ups.append((x, y))
                                road_cells.remove((x, y))
                        thief_stuck_counter = 0
                        police_stuck_counter = 0
                        if click_sound:
                            click_sound.play()
            
            if event.type == pygame.KEYDOWN and game_state == "playing":
                if event.key == pygame.K_p:
                    paused = not paused
                    if paused:
                        pause_start_time = pygame.time.get_ticks()
                    else:
                        total_pause_time += pygame.time.get_ticks() - pause_start_time
                    if click_sound:
                        click_sound.play()
                if event.key == pygame.K_m:
                    police_auto = not police_auto
                    if platform.system() != "Emscripten":
                        print(f"Switched to {'Auto' if police_auto else 'Manual'} mode")
                    if click_sound:
                        click_sound.play()
                if event.key == pygame.K_q:
                    pygame.quit()
                    return
                if not paused and not police_auto:
                    new_pos = police_pos.copy()
                    if event.key in (pygame.K_UP, pygame.K_w):
                        new_pos[0] -= 1
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        new_pos[0] += 1
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        new_pos[1] -= 1
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        new_pos[1] += 1
                    if is_valid_move(new_pos[0], new_pos[1]):
                        police_pos = new_pos
                        police_stuck_counter = 0
                    else:
                        invalid_move_timer = 0.2
                        add_particles(police_pos[1] * CELL_SIZE + CELL_SIZE // 2, police_pos[0] * CELL_SIZE + CELL_SIZE // 2, NEON_PINK, 5)
        
        screen.fill(DEEP_PURPLE)
        
        if game_state == "welcome":
            draw_welcome()
        elif game_state == "playing":
            if not paused:
                update_particles(1 / FPS)
                adjusted_time = pygame.time.get_ticks() - start_time - total_pause_time
                elapsed = adjusted_time // 1000
                if elapsed >= LEVEL_TIME_LIMIT and not caught:
                    game_state = "game_failed"
                    if platform.system() != "Emscripten":
                        print("Time limit exceeded! Switching to game_failed state")
                    continue
                
                if invalid_move_timer > 0:
                    invalid_move_timer -= 1 / FPS
                if grid_warning:
                    grid_warning = False
                
                if power_up_active:
                    power_up_timer -= 1 / FPS
                    if power_up_timer <= 0:
                        power_up_active = False
                        move_interval = 0.5
                
                move_timer += 1 / FPS
                if move_timer >= move_interval:
                    new_pos = decide_thief_move()
                    if new_pos != tuple(thief_pos):
                        thief_pos = list(new_pos)
                        thief_stuck_counter = 0
                    else:
                        thief_stuck_counter += 1
                    
                    if thief_stuck_counter >= 10:
                        city_grid, valid_grid = generate_valid_grid()
                        power_ups.clear()
                        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
                        for _ in range(3):
                            if road_cells:
                                x, y = random.choice(road_cells)
                                city_grid[x][y] = 2
                                power_ups.append((x, y))
                                road_cells.remove((x, y))
                        grid_warning = True
                        thief_stuck_counter = 0
                        police_stuck_counter = 0
                        if platform.system() != "Emscripten":
                            print("Grid Regenerated due to thief stuck:")
                            for row in city_grid:
                                print(row)
                    
                    if police_auto:
                        police_path = bfs_police_path(tuple(police_pos), tuple(thief_pos))
                        if platform.system() != "Emscripten":
                            print(f"Auto mode: Police pos = {police_pos}, Thief pos = {thief_pos}, Path = {police_path}")
                        if len(police_path) > 1:
                            police_pos = list(police_path[1])
                            police_stuck_counter = 0
                            if platform.system() != "Emscripten":
                                print(f"Police moved to: {police_pos}")
                        elif len(police_path) == 1:
                            police_stuck_counter = 0
                        else:
                            police_stuck_counter += 1
                    
                    if police_stuck_counter >= 10:
                        city_grid, valid_grid = generate_valid_grid()
                        power_ups.clear()
                        road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
                        for _ in range(3):
                            if road_cells:
                                x, y = random.choice(road_cells)
                                city_grid[x][y] = 2
                                power_ups.append((x, y))
                                road_cells.remove((x, y))
                        grid_warning = True
                        thief_stuck_counter = 0
                        police_stuck_counter = 0
                        if platform.system() != "Emscripten":
                            print("Grid Regenerated due to police stuck:")
                            for row in city_grid:
                                print(row)
                    
                    if not police_auto:
                        police_path = bfs_police_path(tuple(police_pos), tuple(thief_pos))
                    
                    if tuple(police_pos) in power_ups:
                        power_ups.remove(tuple(police_pos))
                        city_grid[police_pos[0]][police_pos[1]] = 0
                        power_up_active = True
                        power_up_timer = 10
                        move_interval = 0.25
                        add_particles(police_pos[1] * CELL_SIZE + CELL_SIZE // 2, police_pos[0] * CELL_SIZE + CELL_SIZE // 2, NEON_BLUE, 20)
                        if click_sound:
                            click_sound.play()
                    
                    if police_pos == thief_pos:
                        caught = True
                        game_state = "game_over"
                        adjusted_time = pygame.time.get_ticks() - start_time - total_pause_time
                        elapsed = adjusted_time // 1000
                        score = max(10000 - elapsed * 100, 0)
                        if score > highscore:
                            highscore = score
                        screen_shake = 5.0
                        add_particles(police_pos[1] * CELL_SIZE + CELL_SIZE // 2, police_pos[0] * CELL_SIZE + CELL_SIZE // 2, NEON_PINK, 50)
                        if catch_sound:
                            catch_sound.play()
                        if platform.system() != "Emscripten":
                            print("Thief caught! Switching to game_over state")
                    
                    move_timer = 0
            
            draw_grid()
            draw_entities(police_path)
        elif game_state == "game_over":
            draw_game_over()
            await asyncio.sleep(3)
            game_state = "welcome"
            police_pos = [0, 0]
            thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
            caught = False
            police_auto = True
            paused = False
            power_up_active = False
            move_interval = 0.5
            total_pause_time = 0
            city_grid, valid_grid = generate_valid_grid()
            power_ups.clear()
            road_cells = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] == 0 and (x, y) not in [(0, 0), (GRID_SIZE-1, GRID_SIZE-1)]]
            for _ in range(3):
                if road_cells:
                    x, y = random.choice(road_cells)
                    city_grid[x][y] = 2
                    power_ups.append((x, y))
                    road_cells.remove((x, y))
            thief_stuck_counter = 0
            police_stuck_counter = 0
        elif game_state == "game_failed":
            draw_game_failed()
        
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(1.0 / FPS)

async def main():
    setup()
    await update_loop()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
