"""外周閉路の生成と、ルート追従の検証。"""

import random

import main


DELTAS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}


def assert_cycle(route, head, body, food, width, height):
    assert route, "閉路が空"
    assert route[0] == [head[0], head[1]], (route[0], head)
    cells = [(c[0], c[1]) for c in route]
    assert len(cells) == len(set(cells)), "マスが重複している"
    assert len(cells) >= 4
    for a, b in zip(cells, cells[1:]):
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, (a, b)
    a, b = cells[-1], cells[0]
    assert abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1, (a, b)
    food_set = set(food)
    for cell in cells:
        assert cell not in food_set, cell
    blocked = main._cycle_blocked(width, height, food_set)
    expected = {
        (x, y)
        for x in range(width)
        for y in range(height)
        if (x == 0 or y == 0 or x == width - 1 or y == height - 1)
        and (x, y) not in blocked
    }
    missing = expected - set(cells)
    # 迂回路が互いに塞ぎ合うとき、入れない外周マスだけ欠ける。
    assert len(missing) <= 4, missing


def simulate(width, height, snake, food, steps=300):
    head = snake[0]
    route = main.build_cycle(head, snake, food, width, height)
    assert_cycle(route, head, snake, food, width, height)
    food_set = set(food)
    body = list(snake)
    for step in range(steps):
        move = main._next_move_on_route(route, body[0])
        assert move is not None, step
        dx, dy = DELTAS[move]
        nxt = (body[0][0] + dx, body[0][1] + dy)
        assert 0 <= nxt[0] < width and 0 <= nxt[1] < height, nxt
        assert nxt not in food_set, (step, nxt)
        body = [nxt] + body[:-1]
    return route


def random_snake(width, height, rng):
    occupied = set()
    head = (rng.randrange(width), rng.randrange(height))
    snake = [head]
    occupied.add(head)
    for _ in range(2):
        options = []
        x, y = snake[-1]
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in occupied:
                options.append((nx, ny))
        if not options:
            return None
        nxt = rng.choice(options)
        snake.append(nxt)
        occupied.add(nxt)
    return snake


def test_fixed_cases():
    cases = [
        ((5, 5), [(5, 4), (5, 3)], []),
        ((0, 0), [(1, 0), (2, 0)], []),
        ((10, 5), [(9, 5), (8, 5)], [(0, 0), (3, 0), (10, 10)]),
        ((1, 1), [(1, 0), (2, 0)], [(0, 5), (5, 0), (5, 10), (10, 5)]),
        ((7, 2), [(7, 1), (7, 0)], [(0, 0), (1, 0), (10, 1)]),
    ]
    for head, body, food in cases:
        snake = [head] + body
        simulate(11, 11, snake, food, steps=200)
    print("fixed cases ok")


def test_random(n=80):
    rng = random.Random(0)
    ok = 0
    for _ in range(n):
        snake = random_snake(11, 11, rng)
        if snake is None:
            continue
        cells = [(x, y) for x in range(11) for y in range(11) if (x, y) not in snake]
        rng.shuffle(cells)
        food = cells[: rng.randint(0, 6)]
        try:
            simulate(11, 11, snake, food, steps=120)
        except AssertionError as exc:
            print("FAIL", snake, food, exc)
            raise
        ok += 1
    print(f"random ok {ok}")


def game_state(game_id, turn, snake, food, width=11, height=11):
    return {
        "game": {"id": game_id},
        "turn": turn,
        "board": {
            "width": width,
            "height": height,
            "food": [{"x": x, "y": y} for x, y in food],
            "snakes": [],
        },
        "you": {
            "length": len(snake),
            "body": [{"x": x, "y": y} for x, y in snake],
        },
    }


def test_recompute_timing():
    main._routes.clear()
    snake = [(5, 5), (5, 4), (5, 3)]
    food = [(0, 0), (10, 3)]
    state = game_state("g1", 0, snake, food)
    main.start(state)
    route_at_start = [tuple(c) for c in main._routes["g1"]["route"]]
    assert route_at_start[0] == (5, 5)

    # 餌を取っていないターンは同じ配列を使い続ける。
    for turn in range(1, 5):
        move = main.move(state)
        assert move["move"] in {"up", "down", "left", "right"}
        state = game_state("g1", turn, snake, food)
        # 頭は動かさず同じ状態で呼ぶと、長さが変わらなければ再計算しない。
        # ただし頭がルート上にないと退避するので、ルート先頭のままにする。
    assert [tuple(c) for c in main._routes["g1"]["route"]] == route_at_start

    # 体長が増えた次のターンだけ作り直す。
    grown = [(4, 5), (5, 5), (5, 4), (5, 3)]
    state = game_state("g2", 0, snake, food)
    main.start(state)
    before = main._routes["g2"]["route"]
    main.move(game_state("g2", 1, snake, food))
    assert main._routes["g2"]["route"] == before
    main.move(game_state("g2", 2, grown, [(10, 3)]))
    after = main._routes["g2"]["route"]
    assert after[0] == [4, 5]
    assert after != before
    main.end(game_state("g2", 3, grown, [(10, 3)]))
    assert "g2" not in main._routes
    print("recompute timing ok")


if __name__ == "__main__":
    test_fixed_cases()
    test_random()
    test_recompute_timing()
    print("all passed")
