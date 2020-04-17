import lib
import unittest

# show how to do a unittest of a naked function

class TestRandom(unittest.TestCase):
    def test_random(self):
        x = lib.random_data()
        print(x)
        self.assertEqual(1000000, len(x), 'size must be 1e6')

if __name__ == '__main__':
    unittest.main()

