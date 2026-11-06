# Group number: TODO (fill this in before submission)
# Tested with Python 3.13.15
# Additional strategy packages: none (server uses Flask from requirements.txt)
# Based on the Battlesnake Python Starter Project (MIT License).

"""Perimeter-cycle expansion and rewind-based late feeding."""

import random
import typing
from collections import deque
from time import perf_counter

from cycle_expansion import expand_cycle


# ゲームIDごとのルート。
# route は頭を始点とする単純閉路。各要素は [x, y]、末尾の次は先頭。
# snake_length が増えていれば前ターンに餌を取っている。
_routes: typing.Dict[str, typing.Dict] = {}
FOOD_PLANNING_SECONDS = 0.12
FOOD_SEARCH_NODES = 2500
POST_FOOD_LOOKAHEAD = 8


def _in_bounds(x: int, y: int, width: int, height: int) -> bool:
    return 0 <= x < width and 0 <= y < height


def _adjacent(a: typing.Tuple[int, int], b: typing.Tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def _neighbors(cell: typing.Tuple[int, int], width: int,
               height: int) -> typing.List[typing.Tuple[int, int]]:
    x, y = cell
    result = []
    for nx, ny in ((x, y + 1), (x, y - 1), (x - 1, y), (x + 1, y)):
        if _in_bounds(nx, ny, width, height):
            result.append((nx, ny))
    return result


def _is_perimeter(x: int, y: int, width: int, height: int) -> bool:
    return x == 0 or y == 0 or x == width - 1 or y == height - 1


def _direction(src: typing.Tuple[int, int],
               dst: typing.Tuple[int, int]) -> typing.Optional[str]:
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
    """外周を一周するマス。yが上向きの座標では反時計回り。"""
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
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def _bfs(start: typing.Tuple[int, int], goal: typing.Tuple[int, int],
         blocked: typing.Set[typing.Tuple[int, int]],
         forbidden: typing.Set[typing.Tuple[int, int]], width: int, height: int
         ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """最短路。blocked/forbidden は通らないが、goal は forbidden でもよい。"""
    if start in blocked or goal in blocked:
        return None
    if start == goal:
        return [start]
    prev = {start: None}
    queue = deque([start])
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


def _bridge(start: typing.Tuple[int, int], goal: typing.Tuple[int, int],
            blocked: typing.Set[typing.Tuple[int, int]],
            used: typing.Set[typing.Tuple[int, int]],
            perimeter: typing.Set[typing.Tuple[int, int]], width: int, height: int
            ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """外周上の2マスを、外周以外の空きマスでつなぐ中間マス。"""
    if _adjacent(start, goal):
        return []
    passable = set(blocked)
    passable.discard(start)
    passable.discard(goal)
    forbidden = set(used) | perimeter
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


def _perimeter_ring(width: int, height: int,
                    blocked: typing.Set[typing.Tuple[int, int]]
                    ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    """餌で塞がれた外周マスは、内側へ避けてから外周へ戻る。"""
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
            while ring[next_free] in blocked and next_free != start_i and steps < n:
                next_free = (next_free + 1) % n
                steps += 1
            if next_free == start_i or ring[next_free] in blocked:
                break
            target = ring[next_free]
            if target in used:
                idx = (next_free + 1) % n
                continue
            bridge = _bridge(path[-1], target, blocked, used, perimeter, width, height)
            if bridge is None:
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
            bridge = _bridge(path[-1], cell, blocked, used, perimeter, width, height)
            if bridge is None:
                idx = (idx + 1) % n
                continue
            path.extend(bridge)
            used.update(bridge)
        path.append(cell)
        used.add(cell)
        idx = (idx + 1) % n
    if not _adjacent(path[-1], path[0]):
        bridge = _bridge(path[-1], path[0], blocked, used, perimeter, width, height)
        if bridge is None:
            return None
        path.extend(bridge)
    if not _is_valid_cycle(path):
        return None
    return path


def _rotate_cycle(cycle: typing.Sequence[typing.Tuple[int, int]],
                  head: typing.Tuple[int, int],
                  neck: typing.Optional[typing.Tuple[int, int]]
                  ) -> typing.List[typing.List[typing.Tuple[int, int]]]:
    """両方の巡回方向を試し、最初に首へ戻る方向を除く。"""
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


def _directed_arc(ring: typing.Sequence[typing.Tuple[int, int]], start_index: int,
                  goal: typing.Tuple[int, int], step: int
                  ) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
    n = len(ring)
    arc = []
    index = start_index
    while len(arc) <= n:
        arc.append(ring[index])
        if ring[index] == goal and len(arc) > 1:
            return arc
        index = (index + step) % n
    return None


def _splice_head(ring: typing.Sequence[typing.Tuple[int, int]],
                 head: typing.Tuple[int, int],
                 neck: typing.Optional[typing.Tuple[int, int]],
                 blocked: typing.Set[typing.Tuple[int, int]], width: int, height: int
                 ) -> typing.List[typing.List[typing.Tuple[int, int]]]:
    """頭から外周の2マスへ交わらない路を引き、外周の弧とつなぐ。"""
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
        for v, path_v in paths[i + 1:]:
            pu, pv = path_u, path_v
            if set(pu[1:-1]) & set(pv[1:-1]):
                pv = _bfs(head, v, blocked | set(pu[1:-1]), ring_set - {v}, width, height)
                if pv is None:
                    pu = _bfs(head, u, blocked | set(path_v[1:-1]), ring_set - {u}, width, height)
                    if pu is None:
                        continue
                    pv = path_v
            arcs = (_directed_arc(ring, index_of[u], v, 1),
                    _directed_arc(ring, index_of[u], v, -1))
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


def _count_perimeter(cycle: typing.Sequence[typing.Tuple[int, int]],
                     width: int, height: int) -> int:
    return sum(1 for x, y in cycle if _is_perimeter(x, y, width, height))


def _steps_to_perimeter(cycle: typing.Sequence[typing.Tuple[int, int]],
                        width: int, height: int) -> int:
    for i, (x, y) in enumerate(cycle):
        if _is_perimeter(x, y, width, height):
            return i
    return len(cycle)


def _cycle_blocked(width: int, height: int,
                   food: typing.Set[typing.Tuple[int, int]]) -> typing.Set[typing.Tuple[int, int]]:
    """餌と、餌を除いた格子で次数が2未満になるマスを除外する。"""
    alive = {(x, y) for x in range(width) for y in range(height) if (x, y) not in food}
    changed = True
    while changed:
        remove = []
        for cell in alive:
            degree = sum(1 for nxt in _neighbors(cell, width, height) if nxt in alive)
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


def build_cycle(head: typing.Tuple[int, int],
                body: typing.Sequence[typing.Tuple[int, int]],
                food: typing.Iterable[typing.Tuple[int, int]], width: int, height: int
                ) -> typing.Optional[typing.List[typing.List[int]]]:
    """元コードの外周優先閉路を作り、左右の空き2マスへ繰り返し拡張する。"""
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
    best = max(candidates, key=lambda cycle: (
        _count_perimeter(cycle, width, height),
        -_steps_to_perimeter(cycle, width, height), len(cycle)))

    # 追加: A->B を、左右に並ぶ空き2マスを使う A->C->D->B に変更。
    # 頭を先頭に保ち、拡張によって最初の1手が首へ戻ることも防ぐ。
    return expand_cycle(best, blocked, width, height,
                        first_step_forbidden=() if neck is None else (neck,))


def _head_and_neck(game_state: typing.Dict
                   ) -> typing.Tuple[typing.Tuple[int, int], typing.Optional[typing.Tuple[int, int]]]:
    body = game_state["you"]["body"]
    head = (body[0]["x"], body[0]["y"])
    neck = (body[1]["x"], body[1]["y"]) if len(body) > 1 else None
    return head, neck


def _store_route(game_state: typing.Dict, reason: str) -> None:
    game_id = game_state.get("game", {}).get("id", "default")
    head, _neck = _head_and_neck(game_state)
    width, height = game_state["board"]["width"], game_state["board"]["height"]
    body = [(part["x"], part["y"]) for part in game_state["you"]["body"]]
    food = [(item["x"], item["y"]) for item in game_state["board"]["food"]]
    route = build_cycle(head, body, food, width, height)
    if route is None:
        route = []
    perimeter = _count_perimeter([(cell[0], cell[1]) for cell in route], width, height)
    print(f"ROUTE {reason}: cells={len(route)} perimeter={perimeter} head={list(head)}")
    _routes[game_id] = {"route": route, "snake_length": game_state["you"]["length"],
                        "feeding": None}


def _next_move_on_route(route: typing.Sequence[typing.Sequence[int]],
                        head: typing.Tuple[int, int]) -> typing.Optional[str]:
    for i, cell in enumerate(route):
        if cell[0] == head[0] and cell[1] == head[1]:
            nxt = route[(i + 1) % len(route)]
            return _direction(head, (nxt[0], nxt[1]))
    return None


def _simulate_step(body, destination, food, health, width, height, blocked=frozenset()):
    """頭追加→尾除去→給餌・成長→衝突判定。成長時は移動後の尾を重ねる。"""
    if (not _adjacent(body[0], destination)
            or not _in_bounds(*destination, width, height) or destination in blocked):
        return None
    moved = (destination,) + body[:-1]
    if destination in food:
        moved += (moved[-1],)
        next_health = 100
    else:
        next_health = health - 1
    if next_health <= 0 or destination in moved[1:]:
        return None
    return moved, next_health


def _predict_cycle(body, health, route, food, width, height, blocked=frozenset()):
    """実際には動かず、周回予定と各時点の胴体・体力を保存する。

    starvation は餌なしで周回を続けた場合に体力が0になる位置。
    それ以前に衝突や餌があれば、その手前までを離脱候補にする。
    """
    cycle = [tuple(cell) for cell in route]
    if not cycle or body[0] not in cycle:
        return None
    index = cycle.index(body[0])
    starvation = cycle[(index + health) % len(cycle)]
    snapshots, prefix = [(body, health)], []
    current, hp = body, health
    stop_reason = 'starvation'
    for offset in range(1, health + 1):
        destination = cycle[(index + offset) % len(cycle)]
        if destination in food:
            stop_reason = 'food_on_cycle'
            break
        result = _simulate_step(current, destination, food, hp, width, height, blocked)
        if result is None:
            stop_reason = 'starvation' if hp == 1 else 'collision'
            break
        current, hp = result
        prefix.append(destination)
        snapshots.append((current, hp))
    return dict(snapshots=snapshots, prefix=prefix, starvation=starvation,
                starvation_after=health, stop_reason=stop_reason)


def _survives_after_food(body, food, width, height, blocked, deadline):
    """食後8手の生存経路の存在確認。制限到達は False ではなく None。"""
    seen = set()
    checked = 0

    def search(current, foods, health, depth):
        nonlocal checked
        if depth == 0:
            return True
        if checked >= FOOD_SEARCH_NODES or perf_counter() >= deadline:
            return None
        key = current, foods, health, depth
        if key in seen:
            return False
        seen.add(key)
        checked += 1
        unknown = False
        for destination in _neighbors(current[0], width, height):
            result = _simulate_step(current, destination, foods, health,
                                    width, height, blocked)
            if result is None:
                continue
            answer = search(result[0], foods - {destination}, result[1], depth - 1)
            if answer is True:
                return True
            unknown |= answer is None
        return None if unknown else False

    return search(body, frozenset(food), 100, POST_FOOD_LOOKAHEAD)


def _find_food_path(body, food, health, width, height, blocked, deadline):
    """尾が退くタイミングを含め、最初の餌までの安全な経路を探す。"""
    if not food:
        return []
    queue = deque([(body, health, [])])
    seen = {body}
    checked = 0
    while queue and checked < FOOD_SEARCH_NODES and perf_counter() < deadline:
        current, hp, path = queue.popleft()
        checked += 1
        neighbors = _neighbors(current[0], width, height)
        neighbors.sort(key=lambda p: min(abs(p[0]-f[0]) + abs(p[1]-f[1]) for f in food))
        for destination in neighbors:
            result = _simulate_step(current, destination, food, hp, width, height, blocked)
            if result is None:
                continue
            if destination in food:
                if _survives_after_food(result[0], food - {destination}, width,
                                        height, blocked, deadline) is True:
                    return path + [destination]
                continue
            if result[0] not in seen:
                seen.add(result[0])
                queue.append((result[0], result[1], path + [destination]))
    return []


def _plan_feeding(body, health, route, food, width, height, blocked, deadline):
    """体力切れ側から巻き戻し、最も遅い安全な隣接給餌を選ぶ。"""
    prediction = _predict_cycle(body, health, route, food, width, height, blocked)
    if prediction is None or not food:
        return None
    snapshots, prefix = prediction['snapshots'], prediction['prefix']
    for offset in range(len(snapshots) - 1, -1, -1):
        current, hp = snapshots[offset]
        for destination in _neighbors(current[0], width, height):
            if destination not in food:
                continue
            result = _simulate_step(current, destination, food, hp, width, height, blocked)
            if result is not None and _survives_after_food(
                    result[0], food - {destination}, width, height, blocked, deadline) is True:
                return dict(steps=prefix[:offset] + [destination], departure_after=offset,
                            target=destination, starvation=prediction['starvation'],
                            mode='rewind-adjacent')
        if perf_counter() >= deadline:
            return None

    # 閉路に隣接する餌がなければ、数手の離脱経路を各時点から探す。
    for offset in range(len(snapshots) - 1, -1, -1):
        current, hp = snapshots[offset]
        if min(abs(current[0][0]-f[0]) + abs(current[0][1]-f[1]) for f in food) > hp:
            continue
        # ある離脱地点の探索が全予算を消費しないようにする。
        search_deadline = min(deadline, perf_counter() + 0.01)
        detour = _find_food_path(current, food, hp, width, height, blocked, search_deadline)
        if detour:
            return dict(steps=prefix[:offset] + detour, departure_after=offset,
                        target=detour[-1], starvation=prediction['starvation'],
                        mode='rewind-detour')
        if perf_counter() >= deadline:
            break
    return None


def _fallback_move(game_state: typing.Dict) -> str:
    """盤外・自己衝突・他の蛇の現位置を避け、餌なしの手を優先する。"""
    head, neck = _head_and_neck(game_state)
    width, height = game_state["board"]["width"], game_state["board"]["height"]
    food = {(f["x"], f["y"]) for f in game_state["board"]["food"]}
    body = tuple((p['x'], p['y']) for p in game_state['you']['body'])
    blocked = _opponent_cells(game_state)
    avoiding_food, allowing_food = [], []
    for name, dx, dy in (("up", 0, 1), ("down", 0, -1), ("left", -1, 0), ("right", 1, 0)):
        nxt = (head[0] + dx, head[1] + dy)
        if _simulate_step(body, nxt, food, game_state['you'].get('health', 100),
                          width, height, blocked) is None:
            continue
        allowing_food.append(name)
        if nxt not in food:
            avoiding_food.append(name)
    choices = avoiding_food or allowing_food
    if not choices:
        print(f"MOVE {game_state['turn']}: 安全な退避手がない")
        return "down"
    return random.choice(choices)


def _opponent_cells(game_state):
    return frozenset((p['x'], p['y'])
                     for snake in game_state['board'].get('snakes', [])
                     if snake.get('id') != game_state['you'].get('id')
                     for p in snake['body'])


def info() -> typing.Dict:
    print("INFO")
    return {"apiversion": "1", "author": "", "color": "#888888",
            "head": "default", "tail": "default"}


def start(game_state: typing.Dict):
    print("GAME START")
    _store_route(game_state, "ゲーム開始")


def end(game_state: typing.Dict):
    game_id = game_state.get("game", {}).get("id", "default")
    _routes.pop(game_id, None)
    print("GAME OVER\n")


def move(game_state: typing.Dict) -> typing.Dict:
    began = perf_counter()
    game_id = game_state.get("game", {}).get("id", "default")
    length = game_state["you"]["length"]
    state = _routes.get(game_id)
    # 外周優先・2マス拡張の閉路作成と、食後の作り直しはそのまま使う。
    if state is None:
        _store_route(game_state, "ルート未作成")
        state = _routes[game_id]
    elif length > state["snake_length"]:
        _store_route(game_state, "餌を取った次のターン")
        state = _routes[game_id]
    else:
        state["snake_length"] = length

    width, height = game_state['board']['width'], game_state['board']['height']
    body = tuple((p['x'], p['y']) for p in game_state['you']['body'])
    health = game_state['you'].get('health', 100)
    food = frozenset((f['x'], f['y']) for f in game_state['board']['food'])
    blocked = _opponent_cells(game_state)
    signature = food, blocked, width, height
    feeding = state.get('feeding')
    # 初期餌の補充、移動失敗、再送、他の蛇の移動などでは給餌計画を再評価。
    if feeding is not None and (
            feeding.get('expected_body') != body
            or feeding.get('expected_health') != health
            or feeding.get('expected_turn') != game_state['turn']
            or feeding.get('signature') != signature):
        feeding = None
        state['feeding'] = None

    if feeding is None and food:
        deadline = began + FOOD_PLANNING_SECONDS
        feeding = _plan_feeding(body, health, state['route'], food, width, height,
                                blocked, min(deadline, perf_counter() + 0.10))
        if feeding is None:
            path = _find_food_path(body, food, health, width, height, blocked, deadline)
            if path:
                feeding = dict(steps=path, departure_after=0, target=path[-1],
                                starvation=None, mode='food-fallback')
        state['feeding'] = feeding
        if feeding is not None:
            print(f"FEED PLAN: starvation={feeding['starvation']} "
                  f"wait={feeding['departure_after']} target={feeding['target']} "
                  f"steps={len(feeding['steps'])}")

    next_move = None
    mode = 'cycle'
    if feeding is not None and feeding['steps']:
        destination = feeding['steps'][0]
        result = _simulate_step(body, destination, food, health, width, height, blocked)
        if result is not None:
            next_move = _direction(body[0], destination)
            mode = feeding['mode']
            feeding['steps'].pop(0)
            feeding.update(expected_body=result[0], expected_health=result[1],
                           expected_turn=game_state['turn'] + 1, signature=signature)
            if destination in food:
                state['feeding'] = None
        else:
            state['feeding'] = None

    if next_move is None:
        route_move = _next_move_on_route(state['route'], body[0]) if state['route'] else None
        if route_move is not None:
            delta = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}[route_move]
            destination = body[0][0] + delta[0], body[0][1] + delta[1]
            # 選べる限り、次の1手が自己衝突する閉路には踏み込まない。
            if _simulate_step(body, destination, food, health, width, height, blocked) is not None:
                next_move = route_move
        if next_move is None:
            next_move = _fallback_move(game_state)
            mode = 'fallback'
    print(f"MOVE {game_state['turn']}: {next_move} ({mode}, health={health})")
    return {"move": next_move}


if __name__ == "__main__":
    from server import run_server

    run_server({"info": info, "start": start, "move": move, "end": end})
