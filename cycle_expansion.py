"""Expand a simple grid cycle by inserting clear two-cell detours.

For build_cycle-style callers:
    route = build_cycle(head, body, food, width, height)
    route = expand_cycle(route, food, width, height)

The route contains its start once; its last cell connects back to its first.
Body movement/collision checks belong to the caller, not this geometry step.
"""

import typing

Point = typing.Tuple[int, int]


def expand_cycle(
    route: typing.Optional[typing.Sequence[typing.Sequence[int]]],
    forbidden: typing.Iterable[typing.Sequence[int]],
    width: int,
    height: int,
    right_first: bool = False,
    first_step_forbidden: typing.Iterable[typing.Sequence[int]] = (),
) -> typing.Optional[typing.List[typing.List[int]]]:
    """Return an expanded copy, preserving the start and traversal direction.

    For an edge A->B, check the left and right parallel pair C,D. If both
    cells are in bounds, unblocked, and absent from the cycle, replace the
    edge by A->C->D->B. Repeat until no such pair remains. This is a greedy
    extension, not a guarantee of a globally longest cycle.

    None and an empty route are preserved for callers whose loop search failed.
    Other inputs must describe a simple, food-free, in-bounds closed grid path.
    """
    if route is None:
        return None
    cycle = [(cell[0], cell[1]) for cell in route]
    if not cycle:
        return []
    blocked = {(cell[0], cell[1]) for cell in forbidden}
    occupied = set(cycle)
    forbidden_first = {(cell[0], cell[1]) for cell in first_step_forbidden}

    def inside(point: Point) -> bool:
        return 0 <= point[0] < width and 0 <= point[1] < height

    edges = zip(cycle, cycle[1:] + cycle[:1])
    if (len(cycle) < 4 or len(occupied) != len(cycle)
            or occupied & blocked or not all(inside(p) for p in cycle)
            or any(abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1 for a, b in edges)):
        raise ValueError('route must be a simple, unblocked, in-bounds grid cycle')

    while True:
        inserted = False
        for index, a in enumerate(cycle):
            b = cycle[(index + 1) % len(cycle)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            left, right = (-dy, dx), (dy, -dx)
            for sx, sy in ((right, left) if right_first else (left, right)):
                c = a[0] + sx, a[1] + sy
                d = b[0] + sx, b[1] + sy
                if index == 0 and c in forbidden_first:
                    continue
                if (inside(c) and inside(d)
                        and not ({c, d} & (occupied | blocked))):
                    # Inserting after the last cell also handles the closing
                    # edge without moving the original start/head.
                    cycle[index + 1:index + 1] = [c, d]
                    occupied.update((c, d))
                    inserted = True
                    break
            if inserted:
                break
        if not inserted:
            return [[x, y] for x, y in cycle]
