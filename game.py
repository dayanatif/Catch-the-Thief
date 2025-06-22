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

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
DARK_GRAY = (50, 50, 50)
SKY_BLUE = (135, 206, 235)
PURPLE = (128, 0, 128)

# --- Highscore feature (Feature 1) ---
highscore = 0

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
    "Easy": {"random": 0.7, "astar": 0.2, "stay": 0.1, "close_astar": 0.2},
    "Medium": {"random": 0.4, "astar": 0.5, "stay": 0.1, "close_astar": 0.7},
    "Hard": {"random": 0.1, "astar": 0.8, "stay": 0.1, "close_astar": 0.9}
}
start_time = 0
score = 0
police_auto = True
paused = False
power_up_active = False
power_up_timer = 0
move_interval = 0.5
invalid_move_timer = 0
grid_warning = False
thief_stuck_counter = 0
police_stuck_counter = 0
last_thief_pos = thief_pos.copy()
last_police_pos = police_pos.copy()

# --- Pause overlay button area (Feature 6) ---
resume_button_rect = None
mainmenu_button_rect = None

def setup():
    global screen, clock, font, title_font, button_rect, difficulty_rects, click_sound, catch_sound
    global resume_button_rect, mainmenu_button_rect
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Catch the Thief")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)
    title_font = pygame.font.SysFont(None, 64)
    
    button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 150, 200, 50)
    difficulty_rects = {
        "Easy": pygame.Rect(WIDTH // 2 - 150, HEIGHT - 250, 100, 40),
        "Medium": pygame.Rect(WIDTH // 2 - 50, HEIGHT - 250, 100, 40),
        "Hard": pygame.Rect(WIDTH // 2 + 50, HEIGHT - 250, 100, 40)
    }
    # Button rectangles for pause menu
    resume_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 40, 200, 50)
    mainmenu_button_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 110, 200, 50)
    
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
        except Exception as e:
            print(f"Sound initialization failed: {e}")
            click_sound = None
            catch_sound = None
    else:
        click_sound = None
        catch_sound = None
    
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
    global thief_pos, thief_stuck_counter, last_thief_pos
    distance = manhattan_distance(thief_pos, police_pos)
    probs = difficulty_probs[difficulty]
    neighbors = get_neighbors(tuple(thief_pos))
    
    if distance <= 5 and neighbors:
        if random.random() < probs["close_astar"]:
            possible_goals = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] != 1]
            if possible_goals:
                goal = max(possible_goals, key=lambda p: manhattan_distance(p, police_pos), default=thief_pos)
                path = a_star(tuple(thief_pos), goal)
                if path:
                    return path[0]
        else:
            return random.choice(neighbors)
    
    if neighbors:
        choice = random.random()
        cumulative = 0
        for action, prob in [("random", probs["random"]), ("astar", probs["astar"]), ("stay", probs["stay"])]:
            cumulative += prob
            if choice <= cumulative:
                if action == "random":
                    return random.choice(neighbors)
                elif action == "astar":
                    possible_goals = [(x, y) for x in range(GRID_SIZE) for y in range(GRID_SIZE) if city_grid[x][y] != 1]
                    if possible_goals:
                        goal = random.choice(possible_goals)
                        path = a_star(tuple(thief_pos), goal)
                        if path:
                            return path[0]
                return thief_pos
    return thief_pos

def draw_city_background():
    for y in range(HEIGHT // 2):
        color_value = max(0, min(255, 235 - y // 3))
        pygame.draw.line(screen, (135, 206, color_value), (0, y), (WIDTH, y))
    pygame.draw.rect(screen, DARK_GRAY, (0, HEIGHT // 2, WIDTH, HEIGHT // 2))
    for _ in range(10):
        x = random.randint(0, WIDTH)
        w = random.randint(20, 50)
        h = random.randint(50, 150)
        pygame.draw.rect(screen, GRAY, (x, HEIGHT // 2 - h, w, h))

def draw_welcome():
    draw_city_background()
    title = title_font.render("Catch the Thief", True, WHITE)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    pygame.draw.rect(screen, BLACK, title_rect.inflate(20, 20))
    screen.blit(title, title_rect)
    
    mouse_pos = pygame.mouse.get_pos()
    for diff, rect in difficulty_rects.items():
        color = GREEN if diff == difficulty else GRAY
        scale = 1.1 if rect.collidepoint(mouse_pos) else 1.0
        scaled_rect = rect.inflate(rect.width * (scale - 1), rect.height * (scale - 1))
        pygame.draw.rect(screen, color, scaled_rect, border_radius=10)
        text = font.render(diff, True, BLACK)
        text_rect = text.get_rect(center=scaled_rect.center)
        screen.blit(text, text_rect)
    
    scale = 1.1 if button_rect.collidepoint(mouse_pos) else 1.0
    scaled_button = button_rect.inflate(button_rect.width * (scale - 1), button_rect.height * (scale - 1))
    pygame.draw.rect(screen, GREEN, scaled_button, border_radius=10)
    text = font.render("Play Now", True, BLACK)
    text_rect = text.get_rect(center=scaled_button.center)
    screen.blit(text, text_rect)

def draw_grid():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            rect = pygame.Rect(y * CELL_SIZE, x * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            if city_grid[x][y] == 1:
                pygame.draw.rect(screen, GRAY, rect)
            elif city_grid[x][y] == 2:
                pygame.draw.rect(screen, PURPLE, rect)
            else:
                pygame.draw.rect(screen, WHITE, rect)
            pygame.draw.rect(screen, BLACK, rect, 1)

def draw_entities(path):
    if invalid_move_timer > 0:
        pygame.draw.rect(screen, RED, (police_pos[1] * CELL_SIZE - 2, police_pos[0] * CELL_SIZE - 2, CELL_SIZE + 4, CELL_SIZE + 4))
    
    pygame.draw.rect(screen, YELLOW, (police_pos[1] * CELL_SIZE - 2, police_pos[0] * CELL_SIZE - 2, CELL_SIZE + 4, CELL_SIZE + 4))
    police_rect = pygame.Rect(police_pos[1] * CELL_SIZE, police_pos[0] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, BLUE, police_rect)
    
    pygame.draw.rect(screen, YELLOW, (thief_pos[1] * CELL_SIZE - 2, thief_pos[0] * CELL_SIZE - 2, CELL_SIZE + 4, CELL_SIZE + 4))
    thief_rect = pygame.Rect(thief_pos[1] * CELL_SIZE, thief_pos[0] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, RED, thief_rect)
    
    for x, y in path:
        path_rect = pygame.Rect(y * CELL_SIZE, x * CELL_SIZE, CELL_SIZE // 2, CELL_SIZE // 2)
        pygame.draw.rect(screen, GREEN, path_rect)
    
    distance = manhattan_distance(police_pos, thief_pos)
    elapsed = (pygame.time.get_ticks() - start_time) // 1000
    mode = "Auto" if police_auto else "Manual"
    power_up_text = f"Speed: {int(power_up_timer)}s" if power_up_active else ""
    warning_text = "Reset Grid!" if grid_warning else ""
    text = font.render(f"Diff: {difficulty} | Dist: {distance} | Time: {elapsed}s | Mode: {mode} | {power_up_text} | {warning_text}", True, BLACK)
    screen.blit(text, (10, HEIGHT - 30))
    
    # --- Draw highscore at the top left (Feature 1) ---
    hs_text = font.render(f"Highscore: {highscore}", True, YELLOW)
    screen.blit(hs_text, (10, 10))

    if paused:
        draw_pause_overlay()
        
def draw_pause_overlay():
    # --- Pause menu overlay (Feature 6) ---
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))
    text = title_font.render("Paused", True, WHITE)
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
    pygame.draw.rect(screen, BLACK, text_rect.inflate(20, 20))
    screen.blit(text, text_rect)
    # Resume Button
    pygame.draw.rect(screen, GREEN, resume_button_rect, border_radius=10)
    resume_text = font.render("Resume", True, BLACK)
    resume_text_rect = resume_text.get_rect(center=resume_button_rect.center)
    screen.blit(resume_text, resume_text_rect)
    # Main Menu Button
    pygame.draw.rect(screen, GRAY, mainmenu_button_rect, border_radius=10)
    menu_text = font.render("Main Menu", True, BLACK)
    menu_text_rect = menu_text.get_rect(center=mainmenu_button_rect.center)
    screen.blit(menu_text, menu_text_rect)

def draw_game_over():
    global highscore
    if platform.system() != "Emscripten":
        print("Drawing game over screen")
    
    draw_city_background()
    
    game_over_text = title_font.render("Game Over", True, WHITE)
    game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    pygame.draw.rect(screen, BLACK, game_over_rect.inflate(20, 20))
    screen.blit(game_over_text, game_over_rect)
    
    text = title_font.render("Thief Caught!", True, WHITE)
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    pygame.draw.rect(screen, BLACK, text_rect.inflate(20, 20))
    screen.blit(text, text_rect)
    
    elapsed = (pygame.time.get_ticks() - start_time) // 1000
    score_text = font.render(f"Score: {max(10000 - elapsed * 100, 0)} | Time: {elapsed}s", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3))
    pygame.draw.rect(screen, BLACK, score_rect.inflate(20, 20))
    screen.blit(score_text, score_rect)
    
    # --- Update and display highscore (Feature 1) ---
    score_final = max(10000 - elapsed * 100, 0)
    if score_final > highscore:
        highscore = score_final
    hs_text = font.render(f"Highscore: {highscore}", True, YELLOW)
    hs_rect = hs_text.get_rect(center=(WIDTH // 2, HEIGHT * 2 // 3 + 40))
    screen.blit(hs_text, hs_rect)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    pygame.display.flip()

async def update_loop():
    global police_pos, thief_pos, caught, game_state, difficulty, start_time, score, police_auto, paused, power_ups, power_up_active, power_up_timer, move_interval, invalid_move_timer, city_grid, grid_warning, thief_stuck_counter, police_stuck_counter, last_thief_pos, last_police_pos
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
                        if click_sound:
                            click_sound.play()
                elif game_state == "playing" and paused:
                    # --- Pause menu buttons (Feature 6) ---
                    if resume_button_rect.collidepoint(mouse_pos):
                        paused = False
                    elif mainmenu_button_rect.collidepoint(mouse_pos):
                        game_state = "welcome"
                        police_pos = [0, 0]
                        thief_pos = [GRID_SIZE-1, GRID_SIZE-1]
                        caught = False
                        police_auto = True
                        paused = False
                        power_up_active = False
                        move_interval = 0.5
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
                # No mouse interaction for game_over (auto return to welcome after 3s)
            if event.type == pygame.KEYDOWN and game_state == "playing":
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_m:
                    police_auto = not police_auto
                    if platform.system() != "Emscripten":
                        print(f"Switched to {'Auto' if police_auto else 'Manual'} mode")
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
        
        screen.fill(WHITE)
        
        if game_state == "welcome":
            draw_welcome()
        elif game_state == "playing" and not paused:
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
                if new_pos != thief_pos:
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
                    if len(police_path) > 1:  # Move to next position
                        police_pos = list(police_path[1])
                        police_stuck_counter = 0
                        if platform.system() != "Emscripten":
                            print(f"Police moved to: {police_pos}")
                    elif len(police_path) == 1:  # Adjacent to thief
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
                
                if police_pos == thief_pos:
                    caught = True
                    game_state = "game_over"
                    elapsed = (pygame.time.get_ticks() - start_time) // 1000
                    score = max(10000 - elapsed * 100, 0)
                    if score > highscore:  # --- Update highscore if beaten (Feature 1) ---
                        highscore = score
                    if catch_sound:
                        catch_sound.play()
                    if platform.system() != "Emscripten":
                        print("Thief caught! Switching to game_over state")
                
                move_timer = 0
            
            draw_grid()
            draw_entities(police_path)
        elif game_state == "playing" and paused:
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
