import random
from typing import List, Set
from constants import (
    BOARD_WIDTH,
    BOARD_HEIGHT,
    STARTING_HEALTH,
    PIE_REWARD,
    COLLISION_DAMAGE,
    MATCH_TIME_SECONDS,
    MATCH_STATUS_RUNNING,
    MATCH_STATUS_FINISHED,
    MATCH_STATUS_DRAW,
    DIRECTION_UP,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    TICK_RATE,
    MAX_PIES,
    NORMAL_PIES_BEFORE_POWER_PIE,
    POWER_DURATION_PIES,
)
from models import Position, Pie, Obstacle, Snake, MatchState

LAST_SAFE_BODIES = {}


def create_default_obstacles() -> List[Obstacle]:
    obstacle_coords = [ (2, 2), (3, 2), (8, 2), (8, 3),(2, 5), (10, 5),(5, 7), (0, 9),(5, 10), (8, 10), (9, 10),(2, 11), (2, 12), (7, 13), ]

    return [ Obstacle(position=Position(x, y), damage=COLLISION_DAMAGE) for x, y in obstacle_coords]


def create_initial_pie() -> Pie:
    return Pie(
        position=Position(BOARD_WIDTH // 2, BOARD_HEIGHT // 2),
        reward=PIE_REWARD,
        is_power=False,
    )


def create_match(
    player1_username: str,
    player2_username: str,
    player1_color: str = "pink",
    player2_color: str = "pink",
) -> MatchState:
    player1_body = [
        Position(2, 1),
        Position(1, 1),
        Position(0, 1),
    ]

    player2_body = [
        Position(9, 12),
        Position(10, 12),
        Position(11, 12),
    ]

    player1 = Snake(
        player_id="P1",
        username=player1_username,
        body=player1_body,
        direction=DIRECTION_RIGHT,
        next_direction=DIRECTION_RIGHT,
        health=STARTING_HEALTH,
        color=player1_color,
    )

    player2 = Snake(
        player_id="P2",
        username=player2_username,
        body=player2_body,
        direction=DIRECTION_LEFT,
        next_direction=DIRECTION_LEFT,
        health=STARTING_HEALTH,
        color=player2_color,
    )

    LAST_SAFE_BODIES.clear()
    LAST_SAFE_BODIES[player1.player_id] = player1.body.copy()
    LAST_SAFE_BODIES[player2.player_id] = player2.body.copy()

    return MatchState(
        width=BOARD_WIDTH,
        height=BOARD_HEIGHT,
        player1=player1,
        player2=player2,
        pies=[create_initial_pie()],
        obstacles=create_default_obstacles(),
        status=MATCH_STATUS_RUNNING,
        remaining_time=MATCH_TIME_SECONDS,
        normal_pies_since_power=1,
    )


def get_snake_by_player_id(match: MatchState, player_id: str) -> Snake:
    if match.player1.player_id == player_id:
        return match.player1
    if match.player2.player_id == player_id:
        return match.player2
    raise ValueError(f"Unknown player_id: {player_id}")


def is_opposite_direction(current_direction: str, new_direction: str) -> bool:
    opposites = {
        DIRECTION_UP: DIRECTION_DOWN,
        DIRECTION_DOWN: DIRECTION_UP,
        DIRECTION_LEFT: DIRECTION_RIGHT,
        DIRECTION_RIGHT: DIRECTION_LEFT,
    }
    return opposites[current_direction] == new_direction


def set_player_direction(match: MatchState, player_id: str, new_direction: str) -> bool:
    valid_directions = {
        DIRECTION_UP,
        DIRECTION_DOWN,
        DIRECTION_LEFT,
        DIRECTION_RIGHT,
    }

    if new_direction not in valid_directions:
        return False

    snake = get_snake_by_player_id(match, player_id)

    if is_opposite_direction(snake.direction, new_direction):
        return False

    snake.next_direction = new_direction
    return True


def get_next_head_position(head: Position, direction: str) -> Position:
    if direction == DIRECTION_UP:
        return Position(head.x, head.y - 1)
    if direction == DIRECTION_DOWN:
        return Position(head.x, head.y + 1)
    if direction == DIRECTION_LEFT:
        return Position(head.x - 1, head.y)
    if direction == DIRECTION_RIGHT:
        return Position(head.x + 1, head.y)

    raise ValueError(f"Invalid direction: {direction}")


def build_next_body(snake: Snake) -> List[Position]:
    new_head = get_next_head_position(snake.body[0], snake.next_direction)
    return [new_head] + snake.body[:-1]


def is_out_of_bounds(position: Position, match: MatchState) -> bool:
    return (
        position.x < 0
        or position.x >= match.width
        or position.y < 0
        or position.y >= match.height
    )


def hits_obstacle(position: Position, obstacles: List[Obstacle]) -> bool:
    return any(obstacle.position == position for obstacle in obstacles)


def get_collision_type_for_body(
    match: MatchState,
    body: List[Position],
    other_body: List[Position],
):
    head = body[0]

    if is_out_of_bounds(head, match):
        return "wall"

    if hits_obstacle(head, match.obstacles):
        return "obstacle"

    if head in body[1:]:
        return "self"

    if head in other_body:
        return "snake"

    return None


def rollback_to_last_safe_body(snake: Snake, fallback_body: List[Position]) -> None:
    safe_body = LAST_SAFE_BODIES.get(snake.player_id)

    if safe_body is None:
        snake.body = fallback_body.copy()
    else:
        snake.body = safe_body.copy()


def apply_collision_damage(snake: Snake) -> None:
    snake.health = max(0, snake.health - COLLISION_DAMAGE)
    snake.took_damage = True
    if snake.health == 0:
        snake.alive = False 

def snake_has_crown(match: MatchState, snake: Snake) -> bool:
    return match.crown_owner == snake.player_id


def apply_snake_contact_damage(
    match: MatchState,
    player1_touched_player2: bool,
    player2_touched_player1: bool,
) -> None:
    p1_has_crown = snake_has_crown(match, match.player1)
    p2_has_crown = snake_has_crown(match, match.player2)

    if p1_has_crown and not p2_has_crown:
        apply_collision_damage(match.player2)
        return

    if p2_has_crown and not p1_has_crown:
        apply_collision_damage(match.player1)
        return

    if player1_touched_player2:
        apply_collision_damage(match.player1)

    if player2_touched_player1:
        apply_collision_damage(match.player2)


def finalize_health_result(match: MatchState) -> None:
    p1_dead = match.player1.health <= 0
    p2_dead = match.player2.health <= 0

    if p1_dead and p2_dead:
        match.status = MATCH_STATUS_DRAW
        match.winner = None
    elif p1_dead:
        match.status = MATCH_STATUS_FINISHED
        match.winner = match.player2.username
    elif p2_dead:
        match.status = MATCH_STATUS_FINISHED
        match.winner = match.player1.username


def get_occupied_positions(match: MatchState) -> Set[Position]:
    occupied = set()

    for segment in match.player1.body:
        occupied.add(segment)

    for segment in match.player2.body:
        occupied.add(segment)

    for obstacle in match.obstacles:
        occupied.add(obstacle.position)

    for pie in match.pies:
        occupied.add(pie.position)

    return occupied


def spawn_pie(match: MatchState) -> Pie:
    occupied = get_occupied_positions(match)
    free_positions = []

    for y in range(match.height):
        for x in range(match.width):
            pos = Position(x, y)
            if pos not in occupied:
                free_positions.append(pos)

    if not free_positions:
        raise RuntimeError("No free position available to spawn a pie.")

    chosen_position = random.choice(free_positions)

    is_power_pie = match.normal_pies_since_power >= NORMAL_PIES_BEFORE_POWER_PIE

    if is_power_pie:
        match.normal_pies_since_power = 0
    else:
        match.normal_pies_since_power += 1

    return Pie(
        position=chosen_position,
        reward=PIE_REWARD,
        is_power=is_power_pie,
    )


def handle_pie_collection(match: MatchState) -> None:
    if not match.pies:
        return

    remaining_pies = []

    for pie in match.pies:
        collected_by = None

        if match.player1.body[0] == pie.position:
            collected_by = match.player1

        elif match.player2.body[0] == pie.position:
            collected_by = match.player2

        if collected_by is not None:
            collected_by.health += pie.reward

            if pie.is_power:
                match.crown_owner = collected_by.player_id
                match.pies_eaten_after_power = 0

            elif match.crown_owner is not None:
                match.pies_eaten_after_power += 1

                if match.pies_eaten_after_power >= POWER_DURATION_PIES:
                    match.crown_owner = None
                    match.pies_eaten_after_power = 0

        else:
            remaining_pies.append(pie)

    match.pies = remaining_pies

    while len(match.pies) < MAX_PIES:
        match.pies.append(spawn_pie(match))


def finalize_time_result(match: MatchState) -> None:
    if match.remaining_time > 0:
        return

    if match.player1.health > match.player2.health:
        match.status = MATCH_STATUS_FINISHED
        match.winner = match.player1.username
    elif match.player2.health > match.player1.health:
        match.status = MATCH_STATUS_FINISHED
        match.winner = match.player2.username
    else:
        match.status = MATCH_STATUS_DRAW
        match.winner = None


def advance_tick(match: MatchState) -> None:
    if match.status != MATCH_STATUS_RUNNING:
        return

    match.player1.took_damage = False
    match.player2.took_damage = False

    p1_current_body = match.player1.body.copy()
    p2_current_body = match.player2.body.copy()

    p1_next_body = build_next_body(match.player1)
    p2_next_body = build_next_body(match.player2)

    p1_next_head = p1_next_body[0]
    p2_next_head = p2_next_body[0]

    if p1_next_head == p2_next_head:
        rollback_to_last_safe_body(match.player1, p1_current_body)
        rollback_to_last_safe_body(match.player2, p2_current_body)

        apply_snake_contact_damage(
            match,
            player1_touched_player2=True,
            player2_touched_player1=True,
        )

    else:
        p1_collision_type = get_collision_type_for_body(match, p1_next_body, p2_next_body)
        p2_collision_type = get_collision_type_for_body(match, p2_next_body, p1_next_body)

        p1_touched_p2 = p1_collision_type == "snake"
        p2_touched_p1 = p2_collision_type == "snake"

        if p1_collision_type in {"wall", "obstacle"}:
            rollback_to_last_safe_body(match.player1, p1_current_body)
            apply_collision_damage(match.player1)

        elif p1_collision_type == "snake":
            rollback_to_last_safe_body(match.player1, p1_current_body)

        elif p1_collision_type is not None:
            apply_collision_damage(match.player1)

        else:
            LAST_SAFE_BODIES[match.player1.player_id] = p1_current_body.copy()
            match.player1.body = p1_next_body
            match.player1.direction = match.player1.next_direction

        if p2_collision_type in {"wall", "obstacle"}:
            rollback_to_last_safe_body(match.player2, p2_current_body)
            apply_collision_damage(match.player2)

        elif p2_collision_type == "snake":
            rollback_to_last_safe_body(match.player2, p2_current_body)

        elif p2_collision_type is not None:
            apply_collision_damage(match.player2)

        else:
            LAST_SAFE_BODIES[match.player2.player_id] = p2_current_body.copy()
            match.player2.body = p2_next_body
            match.player2.direction = match.player2.next_direction

        if p1_touched_p2 or p2_touched_p1:
            apply_snake_contact_damage(
                match,
                player1_touched_player2=p1_touched_p2,
                player2_touched_player1=p2_touched_p1,
            )

    finalize_health_result(match)

    if match.status == MATCH_STATUS_RUNNING:
        handle_pie_collection(match)

    match.tick_count += 1

    if match.status == MATCH_STATUS_RUNNING and match.remaining_time > 0:
        if match.remaining_time == 1:
            match.remaining_time = 0
        elif match.tick_count % TICK_RATE == 0:
            match.remaining_time -= 1

        finalize_time_result(match)


def serialize_position(position: Position) -> dict:
    return {
        "x": position.x,
        "y": position.y,
    }


def serialize_snake(snake: Snake, has_crown: bool = False) -> dict:
    return {
        "player_id": snake.player_id,
        "username": snake.username,
        "body": [serialize_position(segment) for segment in snake.body],
        "direction": snake.direction,
        "health": snake.health,
        "alive": snake.alive,
        "color": snake.color,
        "took_damage": snake.took_damage,
        "has_crown": has_crown,
    }


def serialize_pie(pie: Pie) -> dict:
    return {
        "position": serialize_position(pie.position),
        "reward": pie.reward,
        "is_power": pie.is_power,
    }


def serialize_obstacle(obstacle: Obstacle) -> dict:
    return {
        "position": serialize_position(obstacle.position),
        "damage": obstacle.damage,
    }


def serialize_match_state(match: MatchState) -> dict:
    return {
        "type": "game_state",
        "status": match.status,
        "winner": match.winner,
        "tick_count": match.tick_count,
        "remaining_time": match.remaining_time,
        "board": {
            "width": match.width,
            "height": match.height,
        },
        "player1": serialize_snake(
            match.player1,
            has_crown=match.crown_owner == match.player1.player_id,
        ),
        "player2": serialize_snake(
            match.player2,
            has_crown=match.crown_owner == match.player2.player_id,
        ),
        "pies": [serialize_pie(pie) for pie in match.pies],
        "obstacles": [serialize_obstacle(obstacle) for obstacle in match.obstacles], 
        "power": {
            "crown_owner": match.crown_owner,
            "pies_eaten_after_power": match.pies_eaten_after_power,
            "duration_pies": POWER_DURATION_PIES,
        },
    }


def process_player_input(match: MatchState, player_id: str, direction: str) -> bool:
    return set_player_direction(match, player_id, direction)


def get_match_state(match: MatchState) -> dict:
    return serialize_match_state(match)


def is_match_over(match: MatchState) -> bool:
    return match.status in {MATCH_STATUS_FINISHED, MATCH_STATUS_DRAW}


def get_match_result(match: MatchState) -> dict:
    player1_username = match.player1.username
    player2_username = match.player2.username

    return {
        "status": match.status,
        "winner": match.winner,
        "player1_username": player1_username,
        "player2_username": player2_username,
        "player1_health": match.player1.health,
        "player2_health": match.player2.health,
        "final_health": {
            player1_username: match.player1.health,
            player2_username: match.player2.health,
        },
        "remaining_time": match.remaining_time,
        "tick_count": match.tick_count,
    }