"""Checks for the pasted perimeter strategy with pair expansion integrated."""

import copy
import unittest
from unittest.mock import patch

import main as snake


def game_state():
    return {
        'game': {'id': 'pasted-test'}, 'turn': 0,
        'board': {'width': 6, 'height': 6, 'food': []},
        'you': {'length': 3, 'health': 100,
                'body': [{'x': 0, 'y': 0}, {'x': 0, 'y': 1}, {'x': 0, 'y': 2}]},
    }


class PastedStrategyTests(unittest.TestCase):
    def tearDown(self):
        snake._routes.clear()

    def test_build_cycle_integrates_pair_expansion(self):
        route = snake.build_cycle((0, 0), [(0, 0), (0, 1), (0, 2)], [], 6, 6)
        self.assertGreater(len(route), len(snake._perimeter_cells(6, 6)))
        self.assertEqual(route[0], [0, 0])
        self.assertNotEqual(route[1], [0, 1])
        self.assertTrue(snake._is_valid_cycle([tuple(p) for p in route]))
        self.assertTrue(set(snake._perimeter_cells(6, 6)) <= set(map(tuple, route)))

    def test_expansion_keeps_head_and_food_avoidance(self):
        foods = {(2, 2), (3, 3), (2, 4)}
        route = snake.build_cycle((0, 0), [(0, 0), (0, 1)], foods, 6, 6)
        self.assertIsNotNone(route)
        self.assertTrue(snake._is_valid_cycle([tuple(p) for p in route]))
        self.assertFalse(set(map(tuple, route)) & foods)
        self.assertTrue(all(snake._in_bounds(x, y, 6, 6) for x, y in route))

    def test_build_cycle_can_splice_interior_head(self):
        route = snake.build_cycle((2, 2), [(2, 2), (2, 1), (2, 0)], [], 6, 6)
        self.assertIsNotNone(route)
        self.assertEqual(route[0], [2, 2])
        self.assertNotEqual(route[1], [2, 1])
        self.assertTrue(snake._is_valid_cycle([tuple(p) for p in route]))

    def test_neck_is_not_inserted_as_first_step(self):
        route = snake.build_cycle((1, 0), [(1, 0), (1, 1), (1, 2)], [], 4, 4)
        self.assertIsNotNone(route)
        self.assertEqual(route[0], [1, 0])
        self.assertNotEqual(route[1], [1, 1])

    def test_no_loop_preserves_failure_behavior(self):
        foods = {(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)}
        self.assertIsNone(snake.build_cycle((1, 1), [(1, 1)], foods, 3, 3))

    def test_move_follows_saved_expanded_loop_without_rebuilding(self):
        state = game_state()
        snake.start(state)
        saved = copy.deepcopy(snake._routes['pasted-test']['route'])
        expected = snake._next_move_on_route(saved, (0, 0))
        with patch.object(snake, 'build_cycle', side_effect=AssertionError('rebuilt unexpectedly')):
            actual = snake.move(state)
        self.assertEqual(actual['move'], expected)
        self.assertEqual(snake._routes['pasted-test']['route'], saved)

    def test_growth_rebuilds_loop(self):
        state = game_state()
        snake.start(state)
        state['you']['length'] += 1
        state['you']['body'].append({'x': 0, 'y': 2})
        state['turn'] += 1
        with patch.object(snake, 'build_cycle', wraps=snake.build_cycle) as builder:
            snake.move(state)
            self.assertEqual(builder.call_count, 1)
        self.assertEqual(snake._routes['pasted-test']['snake_length'], 4)

    def test_next_move_wraps_last_cell_to_head(self):
        route = [[0, 0], [1, 0], [1, 1], [0, 1]]
        self.assertEqual(snake._next_move_on_route(route, (0, 1)), 'down')

    def test_end_discards_only_its_game(self):
        state = game_state()
        snake.start(state)
        snake._routes['another-game'] = {'route': [], 'snake_length': 3}
        snake.end(state)
        self.assertNotIn('pasted-test', snake._routes)
        self.assertIn('another-game', snake._routes)


if __name__ == '__main__':
    unittest.main()
