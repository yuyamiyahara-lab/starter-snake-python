# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/\__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import random
import typing
from collections import deque


# ゲームIDごとのルート。
# route は頭を始点とする単純閉路で、各要素は [x, y]。末尾の次は先頭に戻る。
# snake_length は前回の move 時点の体長。増えていれば前ターンに餌を取っている。
_routes: typing.Dict[str, typing.Dict] = {}


def _in_bounds(x: int, y: int, width: int, height: int) -> bool:
    return 0 <= x < width and 0 <= y < height


def _adjacent(a: typing.Tuple[int, int], b: typing.Tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def _neighbors(
    cell: typing.Tuple[int, int], width: int, height: int
) -> typing.List[typing.Tuple[int, int]]:
    x, y = cell
    result = []
    for nx, ny in ((x, y + 1), (x, y - 1), (x - 1, y), (x + 1, y)):
        if _in_bounds(nx, ny, width, height):
            result.append((nx, ny))
    return result


def _is_perimeter(x: int, y: int, width: int, height: int) -> bool:
    return x == 0 or y == 0 or x == width - 1 or y == height - 1


def _direction(
    src: typing.Tuple[int, int], dst: typing.Tuple[int, int]
) -> typing.Optional[str]:
    if dst[0] == src[0] + 1 and dst[1] == src[1]:
        return "right"
    if dst[0] == src[0] - 1 and dst[1] == src[1]:
        return "left"
    if dst[1] == src[1] + 1 and dst[0] == src[0]:
        return "up"
    if dst[1] == src[1] - 1 and dst[0] == src[0]:
        return "down"
    return None


def _perimeter_cells(width: int, height: int) -> typing.List[typing.Tuple[int, int]]:
    """時計回りの外周マス。角は一度だけ含む。"""
    cells = []
    for x in range(width):
        cells.append((x, 0))
    for y in range(1, height):
        cells.append((width - 1, y))
    for x in range(width - 2, -1, -1):
        cells.append((x, height - 1))
    for y in range(height - 2, 0, -1):
        cells.append((0, y))
    return cells


def _reconstruct(
    prev: typing.Dict[typing.Tuple[int, int], typing.Optional[typing.Tuple[int, int]]],
    goal: typing.Tuple[int, int],
) -> typing.List[typing.Tuple[int, int]]:
    path = []
    cur: typing.Optional[typing.Tuple[int, int]] = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def _bfs(
    start: typing.Tuple[int, int],
    goal: typing.Tuple[int, int],
    blocked: typing.Set[typing.Tuple[int, int]],
    forbidden: typing.Set[typing.Tuple[int, int]],
    width: int,
    height: int,
) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """start から goal への最短路。blocked と forbidden は通らない。goal は forbidden でもよい。"""
    if start in blocked or goal in blocked:
        return None
    if start == goal:
        return [start]

    prev: typing.Dict[
        typing.Tuple[int, int], typing.Optional[typing.Tuple[int, int]]
    ] = {start: None}
    queue: typing.Deque[typing.Tuple[int, int]] = deque([start])
    while queue:
        cur = queue.popleft()
        for nxt in _neighbors(cur, width, height):
            if nxt in prev or nxt in blocked:
                continue
            if nxt != goal and nxt in forbidden:
                continue
            prev[nxt] = cur
            if nxt == goal:
                return _reconstruct(prev, goal)
            queue.append(nxt)
    return None


def _bridge(
    start: typing.Tuple[int, int],
    goal: typing.Tuple[int, int],
    blocked: typing.Set[typing.Tuple[int, int]],
    used: typing.Set[typing.Tuple[int, int]],
    perimeter: typing.Set[typing.Tuple[int, int]],
    width: int,
    height: int,
) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """外周上の2マスをつなぐ、外周以外だけを通る中間マス。隣接していれば空リスト。"""
    if _adjacent(start, goal):
        return []
    passable = set(blocked)
    passable.discard(start)
    passable.discard(goal)
    forbidden = set(used)
    forbidden |= perimeter
    forbidden.discard(goal)
    path = _bfs(start, goal, passable, forbidden, width, height)
    if path is None:
        return None
    return path[1:-1]


def _is_valid_cycle(path: typing.Sequence[typing.Tuple[int, int]]) -> bool:
    if len(path) < 4 or len(path) != len(set(path)):
        return False
    for a, b in zip(path, path[1:]):
        if not _adjacent(a, b):
            return False
    return _adjacent(path[-1], path[0])


def _perimeter_ring(
    width: int,
    height: int,
    blocked: typing.Set[typing.Tuple[int, int]],
) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """餌で塞がれた外周マスは、内側へ一度避けてから外周へ戻る閉路にする。"""
    ring = _perimeter_cells(width, height)
    perimeter = set(ring)
    n = len(ring)
    start_i = next((i for i, cell in enumerate(ring) if cell not in blocked), None)
    if start_i is None:
        return None

    path = [ring[start_i]]
    used = {ring[start_i]}
    idx = (start_i + 1) % n
    guard = 0

    while idx != start_i and guard <= n:
        guard += 1
        cell = ring[idx]
        if cell in blocked:
            next_free = (idx + 1) % n
            steps = 0
            while (
                ring[next_free] in blocked
                and next_free != start_i
                and steps < n
            ):
                next_free = (next_free + 1) % n
                steps += 1
            if next_free == start_i or ring[next_free] in blocked:
                break
            target = ring[next_free]
            if target in used:
                idx = (next_free + 1) % n
                continue
            bridge = _bridge(
                path[-1], target, blocked, used, perimeter, width, height
            )
            if bridge is None:
                # この外周マスは閉路に入れず、次のマスへつなぐ。
                idx = (next_free + 1) % n
                continue
            path.extend(bridge)
            used.update(bridge)
            path.append(target)
            used.add(target)
            idx = (next_free + 1) % n
            continue

        if cell in used:
            idx = (idx + 1) % n
            continue
        if not _adjacent(path[-1], cell):
            bridge = _bridge(
                path[-1], cell, blocked, used, perimeter, width, height
            )
            if bridge is None:
                idx = (idx + 1) % n
                continue
            path.extend(bridge)
            used.update(bridge)
        path.append(cell)
        used.add(cell)
        idx = (idx + 1) % n

    if not _adjacent(path[-1], path[0]):
        bridge = _bridge(
            path[-1], path[0], blocked, used, perimeter, width, height
        )
        if bridge is None:
            return None
        path.extend(bridge)

    if not _is_valid_cycle(path):
        return None
    return path


def _rotate_cycle(
    cycle: typing.Sequence[typing.Tuple[int, int]],
    head: typing.Tuple[int, int],
    neck: typing.Optional[typing.Tuple[int, int]],
) -> typing.List[typing.List[typing.Tuple[int, int]]]:
    """頭を先頭にした時計回りと反時計回りのうち、首へ踏み込まないものを返す。"""
    index = list(cycle).index(head)
    clockwise = list(cycle[index:]) + list(cycle[:index])
    counter = [head] + list(reversed(clockwise[1:]))
    options = []
    for cand in (clockwise, counter):
        if neck is not None and cand[1] == neck:
            continue
        if _is_valid_cycle(cand):
            options.append(cand)
    return options


def _directed_arc(
    ring: typing.Sequence[typing.Tuple[int, int]],
    start_index: int,
    goal: typing.Tuple[int, int],
    step: int,
) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """ring 上を step 方向に進み、goal までの弧を返す。"""
    n = len(ring)
    arc = []
    index = start_index
    while len(arc) <= n:
        arc.append(ring[index])
        if ring[index] == goal and len(arc) > 1:
            return arc
        index = (index + step) % n
    return None


def _splice_head(
    ring: typing.Sequence[typing.Tuple[int, int]],
    head: typing.Tuple[int, int],
    neck: typing.Optional[typing.Tuple[int, int]],
    blocked: typing.Set[typing.Tuple[int, int]],
    width: int,
    height: int,
) -> typing.List[typing.List[typing.Tuple[int, int]]]:
    """頭から外周上の2マスへ交わりのない路を引き、その間の弧と合わせて閉路にする。"""
    ring_set = set(ring)
    index_of = {cell: i for i, cell in enumerate(ring)}
    paths = []
    for cell in ring:
        path = _bfs(head, cell, blocked, ring_set - {cell}, width, height)
        if path is not None:
            paths.append((cell, path))
    paths.sort(key=lambda item: len(item[1]))

    ring_perimeter = _count_perimeter(ring, width, height)
    candidates = []
    for i, (u, path_u) in enumerate(paths):
        for v, path_v in paths[i + 1 :]:
            pu, pv = path_u, path_v
            if set(pu[1:-1]) & set(pv[1:-1]):
                pv = _bfs(
                    head,
                    v,
                    blocked | set(pu[1:-1]),
                    ring_set - {v},
                    width,
                    height,
                )
                if pv is None:
                    pu = _bfs(
                        head,
                        u,
                        blocked | set(path_v[1:-1]),
                        ring_set - {u},
                        width,
                        height,
                    )
                    if pu is None:
                        continue
                    pv = path_v
            arcs = (
                _directed_arc(ring, index_of[u], v, 1),
                _directed_arc(ring, index_of[u], v, -1),
            )
            for arc in arcs:
                if not arc:
                    continue
                cycle = list(pu) + arc[1:]
                cycle.extend(list(reversed(pv))[1:-1])
                options = [cycle]
                if len(cycle) > 1:
                    options.append([cycle[0]] + list(reversed(cycle[1:])))
                for cand in options:
                    if neck is not None and cand[1] == neck:
                        continue
                    if not (_is_valid_cycle(cand) and cand[0] == head):
                        continue
                    if _count_perimeter(cand, width, height) >= ring_perimeter:
                        return [cand]
                    candidates.append(cand)
    return candidates


def _count_perimeter(
    cycle: typing.Sequence[typing.Tuple[int, int]], width: int, height: int
) -> int:
    return sum(1 for x, y in cycle if _is_perimeter(x, y, width, height))


def _steps_to_perimeter(
    cycle: typing.Sequence[typing.Tuple[int, int]], width: int, height: int
) -> int:
    for i, (x, y) in enumerate(cycle):
        if _is_perimeter(x, y, width, height):
            return i
    return len(cycle)


def _cycle_blocked(
    width: int, height: int, food: typing.Set[typing.Tuple[int, int]]
) -> typing.Set[typing.Tuple[int, int]]:
    """閉路に入れないマス。餌と、餌を除いた格子で次数が2未満になるマス。"""
    alive = {
        (x, y)
        for x in range(width)
        for y in range(height)
        if (x, y) not in food
    }
    changed = True
    while changed:
        remove = []
        for cell in alive:
            degree = sum(
                1 for nxt in _neighbors(cell, width, height) if nxt in alive
            )
            if degree < 2:
                remove.append(cell)
        changed = bool(remove)
        for cell in remove:
            alive.discard(cell)

    blocked = set(food)
    for x in range(width):
        for y in range(height):
            if (x, y) not in alive:
                blocked.add((x, y))
    return blocked


def build_cycle(
    head: typing.Tuple[int, int],
    body: typing.Sequence[typing.Tuple[int, int]],
    food: typing.Iterable[typing.Tuple[int, int]],
    width: int,
    height: int,
) -> typing.Optional[typing.List[typing.List[int]]]:
    """頭を始点かつ終点とし、餌を避け、外周マスをできるだけ多く含む単純閉路。"""
    neck = body[1] if len(body) > 1 else None
    food_set = set(food)
    blocked = _cycle_blocked(width, height, food_set)
    if head in blocked:
        print("ROUTE: 頭を含む閉路が存在しない")
        return None

    ring = _perimeter_ring(width, height, blocked)
    if ring is None:
        print("ROUTE: 外周の閉路を作れなかった")
        return None

    if head in set(ring):
        candidates = _rotate_cycle(ring, head, neck)
    else:
        candidates = _splice_head(ring, head, neck, blocked, width, height)

    if not candidates:
        print("ROUTE: 頭を外周閉路へ接続できなかった")
        return None

    best = max(
        candidates,
        key=lambda cycle: (
            _count_perimeter(cycle, width, height),
            -_steps_to_perimeter(cycle, width, height),
            len(cycle),
        ),
    )
    return [[x, y] for x, y in best]


def _head_and_neck(
    game_state: typing.Dict,
) -> typing.Tuple[typing.Tuple[int, int], typing.Optional[typing.Tuple[int, int]]]:
    body = game_state["you"]["body"]
    head = (body[0]["x"], body[0]["y"])
    neck = (body[1]["x"], body[1]["y"]) if len(body) > 1 else None
    return head, neck


def _store_route(game_state: typing.Dict, reason: str) -> None:
    game_id = game_state.get("game", {}).get("id", "default")
    head, _neck = _head_and_neck(game_state)
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    body = [(part["x"], part["y"]) for part in game_state["you"]["body"]]
    food = [(item["x"], item["y"]) for item in game_state["board"]["food"]]
    route = build_cycle(head, body, food, width, height)
    if route is None:
        route = []
    perimeter = _count_perimeter(
        [(cell[0], cell[1]) for cell in route], width, height
    )
    print(f"ROUTE {reason}: cells={len(route)} perimeter={perimeter} head={list(head)}")
    _routes[game_id] = {
        "route": route,
        "snake_length": game_state["you"]["length"],
    }


def _next_move_on_route(
    route: typing.Sequence[typing.Sequence[int]], head: typing.Tuple[int, int]
) -> typing.Optional[str]:
    for i, cell in enumerate(route):
        if cell[0] == head[0] and cell[1] == head[1]:
            nxt = route[(i + 1) % len(route)]
            return _direction(head, (nxt[0], nxt[1]))
    return None


def _fallback_move(game_state: typing.Dict) -> str:
    """閉路に乗れないときの退避。盤外と、直後の後退だけ避ける。"""
    head, neck = _head_and_neck(game_state)
    width = game_state["board"]["width"]
    height = game_state["board"]["height"]
    food = {(f["x"], f["y"]) for f in game_state["board"]["food"]}
    avoiding_food = []
    allowing_food = []
    for name, dx, dy in (
        ("up", 0, 1),
        ("down", 0, -1),
        ("left", -1, 0),
        ("right", 1, 0),
    ):
        nxt = (head[0] + dx, head[1] + dy)
        if not _in_bounds(nxt[0], nxt[1], width, height):
            continue
        if neck is not None and nxt == neck:
            continue
        allowing_food.append(name)
        if nxt not in food:
            avoiding_food.append(name)
    choices = avoiding_food or allowing_food
    if not choices:
        print(f"MOVE {game_state['turn']}: 安全な退避手がない")
        return "down"
    return random.choice(choices)


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#6f4b3e",  # TODO: Choose color
        "head": "flytrap",  # TODO: Choose head
        "tail": "mouse",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")
    _store_route(game_state, "ゲーム開始")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    game_id = game_state.get("game", {}).get("id", "default")
    _routes.pop(game_id, None)
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def move(game_state: typing.Dict) -> typing.Dict:
    game_id = game_state.get("game", {}).get("id", "default")
    length = game_state["you"]["length"]
    state = _routes.get(game_id)

    # ルートを決めるのはゲーム開始時と、餌を取った次のターンだけ。
    if state is None:
        _store_route(game_state, "ルート未作成")
        state = _routes[game_id]
    elif length > state["snake_length"]:
        _store_route(game_state, "餌を取った次のターン")
        state = _routes[game_id]
    else:
        state["snake_length"] = length

    head, _neck = _head_and_neck(game_state)
    route = state["route"]
    next_move = _next_move_on_route(route, head) if route else None
    if next_move is None:
        print(f"MOVE {game_state['turn']}: ルート上に頭がない。退避する")
        next_move = _fallback_move(game_state)

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}


# Start server when `python main.py` is run
if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
