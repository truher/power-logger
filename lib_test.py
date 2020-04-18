import lib
import unittest

# show how to do a unittest of a naked function

class TestRandom(unittest.TestCase):
    def test_load_name(self):
        x = lib.load_name({'id':'5737333034370D0E14','ct':'ct4'})
        self.assertEqual('load4', x)

    def test_jitter_time(self):
        x = lib.jitter_time(10)
        #print(x)
        self.assertEqual(10, len(x))

    def test_random_data(self):
        x = lib.random_data()
        #print(x)
        self.assertEqual(1000000, len(x), 'size must be 1e6')

    def test_multi_random_data(self):
        x = lib.multi_random_data()
        #print(x)
        self.assertEqual(1000000, len(x), 'size must be 1e6')

    def test_read_raw(self):
        raw_data = lib.read_raw('test_data.csv')
        #print(raw_data)
        self.assertEqual(3, len(raw_data), 'three observations')
        raw_data = lib.read_raw('test_data_multi.csv')
        #print(raw_data)
        self.assertEqual(24, len(raw_data), 'three observations')

    def test_make_multi_hourly(self):
        raw_data = lib.read_raw('test_data_multi.csv')
        #print("raw_data")
        #print(raw_data)
        hourly = lib.make_multi_hourly(raw_data)
        #print("hourly")
        #print(hourly)
        self.assertEqual(16, len(hourly),'one per load plus total')

    def test_make_hourly(self):
        raw_data = lib.read_raw('test_data.csv')
        hourly = lib.make_hourly(raw_data)
        #print(hourly)
        self.assertEqual(1, len(hourly), 'all data is in 14:00')
        self.assertAlmostEqual(0.0001667, hourly.iloc[0].at['measure'],
            places=7, msg='total is 0.0001667')


if __name__ == '__main__':
    unittest.main()

