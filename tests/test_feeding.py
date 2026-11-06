from time import perf_counter
import unittest
from unittest.mock import patch

import main as snake


CYCLE = [[1, 1], [2, 1], [2, 2], [1, 2]]
BODY = ((1, 1), (1, 2), (2, 2))


class FeedingTests(unittest.TestCase):
    def tearDown(self):
        snake._routes.clear()

    def test_predicts_position_where_health_would_reach_zero(self):
        prediction = snake._predict_cycle(BODY, 8, CYCLE, {(0, 2)}, 6, 6)
        self.assertEqual(prediction['starvation'], (1, 1))
        self.assertEqual(prediction['starvation_after'], 8)
        self.assertEqual(len(prediction['prefix']), 7)
        self.assertEqual(prediction['snapshots'][-1][1], 1)

    def test_rewinds_to_latest_adjacent_food_and_eats_at_health_one(self):
        foods = {(0, 2)}
        plan = snake._plan_feeding(BODY, 8, CYCLE, foods, 6, 6,
                                   frozenset(), perf_counter() + 1)
        self.assertEqual(plan['departure_after'], 7)
        self.assertEqual(len(plan['steps']), 8)
        body, hp = BODY, 8
        for point in plan['steps']:
            result = snake._simulate_step(body, point, foods, hp, 6, 6)
            self.assertIsNotNone(result)
            body, hp = result
        self.assertEqual(body[0], (0, 2))
        self.assertEqual(hp, 100)
        self.assertEqual(len(body), 4)

    def test_simulation_distinguishes_free_and_overlapping_tail(self):
        body = ((1, 1), (1, 0), (0, 0), (0, 1))
        self.assertIsNotNone(snake._simulate_step(body, (0, 1), set(), 10, 6, 6))
        duplicate = ((1, 1), (1, 0), (0, 1), (0, 1))
        self.assertIsNone(snake._simulate_step(duplicate, (0, 1), set(), 10, 6, 6))

    def test_food_step_grows_new_tail_and_works_at_health_one(self):
        moved, hp = snake._simulate_step(BODY, (2, 1), {(2, 1)}, 1, 6, 6)
        self.assertEqual(moved, ((2, 1), (1, 1), (1, 2), (1, 2)))
        self.assertEqual(hp, 100)

    def test_prediction_stops_before_body_collision(self):
        body = ((1, 1), (2, 1), (2, 2))
        prediction = snake._predict_cycle(body, 20, CYCLE, set(), 6, 6)
        self.assertEqual(prediction['stop_reason'], 'collision')
        self.assertEqual(prediction['prefix'], [])

    def test_new_food_on_cycle_is_not_assumed_to_be_empty(self):
        prediction = snake._predict_cycle(BODY, 20, CYCLE, {(2, 1)}, 6, 6)
        self.assertEqual(prediction['stop_reason'], 'food_on_cycle')
        self.assertEqual(prediction['prefix'], [])

    def test_rejects_food_exit_with_a_two_step_dead_end(self):
        trapped = ((0, 1), (1, 1), (1, 0), (2, 0), (2, 1),
                   (2, 2), (1, 2), (0, 2), (0, 2))
        self.assertIsNotNone(snake._simulate_step(trapped, (0, 0), set(), 100, 3, 3))
        self.assertFalse(snake._survives_after_food(trapped, set(), 3, 3,
                                                   frozenset(), perf_counter() + 1))

    def test_expired_search_is_unknown_not_proven_impossible(self):
        answer = snake._survives_after_food(BODY, set(), 6, 6,
                                            frozenset(), perf_counter() - 1)
        self.assertIsNone(answer)

    def test_no_food_has_no_feeding_plan(self):
        self.assertIsNone(snake._plan_feeding(BODY, 20, CYCLE, set(), 6, 6,
                                              frozenset(), perf_counter() + 1))

    def test_detours_to_food_not_adjacent_to_cycle(self):
        foods = {(5, 5)}
        plan = snake._plan_feeding(BODY, 12, CYCLE, foods, 6, 6,
                                   frozenset(), perf_counter() + 1)
        self.assertIsNotNone(plan)
        self.assertEqual(plan['mode'], 'rewind-detour')
        self.assertLessEqual(len(plan['steps']), 12)
        self.assertEqual(plan['steps'][-1], (5, 5))

    def test_move_caches_trip_and_rebuilds_cycle_after_eating(self):
        body, hp = BODY, 8
        state = {'game': {'id': 'feed'}, 'turn': 0,
                 'board': {'width': 6, 'height': 6, 'food': [{'x': 0, 'y': 2}]},
                 'you': {'length': 3, 'health': hp, 'body': []}}
        snake._routes['feed'] = dict(route=CYCLE, snake_length=3, feeding=None)
        for turn in range(8):
            state['turn'] = turn
            state['you'].update(health=hp, body=[dict(x=x, y=y) for x, y in body])
            with patch.object(snake, 'build_cycle', side_effect=AssertionError('unexpected rebuild')):
                result = snake.move(state)
            deltas = {'up': (0, 1), 'down': (0, -1), 'left': (-1, 0), 'right': (1, 0)}
            dx, dy = deltas[result['move']]
            body, hp = snake._simulate_step(body, (body[0][0]+dx, body[0][1]+dy),
                                            {(0, 2)}, hp, 6, 6)
        self.assertEqual(hp, 100)
        self.assertIsNone(snake._routes['feed']['feeding'])
        state['turn'] = 8
        state['board']['food'] = []
        state['you'].update(length=4, health=hp, body=[dict(x=x, y=y) for x, y in body])
        with patch.object(snake, 'build_cycle', wraps=snake.build_cycle) as builder:
            snake.move(state)
            self.assertEqual(builder.call_count, 1)

    def test_changed_food_invalidates_saved_trip(self):
        state = {'game': {'id': 'feed'}, 'turn': 0,
                 'board': {'width': 6, 'height': 6, 'food': [{'x': 0, 'y': 2}]},
                 'you': {'length': 3, 'health': 8, 'body': [dict(x=x, y=y) for x, y in BODY]}}
        snake._routes['feed'] = dict(route=CYCLE, snake_length=3, feeding=None)
        snake.move(state)
        expected = snake._routes['feed']['feeding']
        state['turn'] = expected['expected_turn']
        state['you'].update(health=expected['expected_health'],
                            body=[dict(x=x, y=y) for x, y in expected['expected_body']])
        state['board']['food'] = [{'x': 5, 'y': 5}]
        with patch.object(snake, '_plan_feeding', wraps=snake._plan_feeding) as planner:
            snake.move(state)
            self.assertEqual(planner.call_count, 1)
        self.assertEqual(snake._routes['feed']['feeding']['target'], (5, 5))

    def test_unchanged_board_reuses_plan_after_a_real_step(self):
        state = {'game': {'id': 'feed'}, 'turn': 0,
                 'board': {'width': 6, 'height': 6, 'food': [{'x': 0, 'y': 2}]},
                 'you': {'length': 3, 'health': 8, 'body': [dict(x=x, y=y) for x, y in BODY]}}
        snake._routes['feed'] = dict(route=CYCLE, snake_length=3, feeding=None)
        snake.move(state)
        expected = snake._routes['feed']['feeding']
        state['turn'] = expected['expected_turn']
        state['you'].update(health=expected['expected_health'],
                            body=[dict(x=x, y=y) for x, y in expected['expected_body']])
        with patch.object(snake, '_plan_feeding', side_effect=AssertionError('unexpected replan')):
            result = snake.move(state)
        self.assertEqual(result['move'], 'up')


if __name__ == '__main__':
    unittest.main()
