import unittest

from cycle_expansion import expand_cycle


class ExpansionTests(unittest.TestCase):
    def assert_simple_cycle(self, cycle):
        points = [tuple(p) for p in cycle]
        self.assertEqual(len(points), len(set(points)))
        self.assertTrue(all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
                            for a, b in zip(points, points[1:] + points[:1])))

    def test_left_pair(self):
        original = [[0, 0], [1, 0], [1, 1], [0, 1]]
        result = expand_cycle(original, [], 3, 2)
        self.assertEqual(result, [[0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [0, 1]])
        self.assertEqual(original, [[0, 0], [1, 0], [1, 1], [0, 1]])
        self.assert_simple_cycle(result)

    def test_right_pair_in_reverse_traversal(self):
        clockwise = [[0, 0], [0, 1], [1, 1], [1, 0]]
        result = expand_cycle(clockwise, [], 3, 2)
        self.assertEqual(result, [[0, 0], [0, 1], [1, 1], [2, 1], [2, 0], [1, 0]])
        self.assert_simple_cycle(result)

    def test_either_blocked_cell_rejects_pair(self):
        cycle = [[0, 0], [1, 0], [1, 1], [0, 1]]
        for food in ([2, 0], [2, 1]):
            with self.subTest(food=food):
                self.assertEqual(expand_cycle(cycle, [food], 3, 2), cycle)

    def test_closing_edge_can_expand_without_rotating_head(self):
        cycle = [[1, 0], [2, 0], [2, 1], [1, 1]]
        result = expand_cycle(cycle, [], 3, 2)
        self.assertEqual(result, cycle + [[0, 1], [0, 0]])
        self.assert_simple_cycle(result)

    def test_no_space_and_failed_search(self):
        cycle = [[0, 0], [1, 0], [1, 1], [0, 1]]
        self.assertEqual(expand_cycle(cycle, [], 2, 2), cycle)
        self.assertIsNone(expand_cycle(None, [], 6, 6))
        self.assertEqual(expand_cycle([], [], 6, 6), [])

    def test_invalid_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            expand_cycle([[0, 0], [1, 0], [0, 1], [1, 1]], [], 3, 3)

    def test_first_step_forbidden_does_not_block_neck_elsewhere_in_loop(self):
        cycle = [[1, 0], [2, 0], [2, 1], [1, 1]]
        result = expand_cycle(cycle, [], 4, 3, first_step_forbidden=[(1, 1)])
        self.assertEqual(result[0], [1, 0])
        self.assertNotEqual(result[1], [1, 1])
        self.assertIn([1, 1], result)
        self.assert_simple_cycle(result)


if __name__ == '__main__':
    unittest.main()
