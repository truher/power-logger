import io
import lib
import unittest

# show how to do a unittest of a naked function

class TestRandom(unittest.TestCase):
    def test_parse(self):
        self.assertIsNone(lib.parse(""))
        self.assertIsNone(lib.parse("a b c d"))
        self.assertIsNone(lib.parse("2020-04-18T17:04:27.322422 b c d"))
        self.assertIsNone(lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr c d"))
        self.assertIsNone(lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr xyz d"))
        x = lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr xyz 1.0")
        self.assertEqual("2020-04-18 17:04:27.322422", str(x['time']))
        self.assertEqual("abcdefghijklmnopqr", x['id'])
        self.assertEqual("xyz", x['ct'])
        self.assertAlmostEqual(1.0, x['measure'], 3)

    def test_transcribe(self):
        sink = io.StringIO()
        source = io.BytesIO(b"asdf\n")
        f = lib.transcribe(sink)
        f(source)
        content = sink.getvalue()
        self.assertEqual("asdf\n", content[-5:])

    def test_io_write_str(self):
        output = io.StringIO()
        output.write('hi')
        content = output.getvalue()
        output.close()
        self.assertEqual("hi", content)

    def test_io_write(self):
        output = io.BytesIO()
        output.write(b'hi')
        content = output.getvalue().decode('ascii')
        output.close()
        self.assertEqual("hi", content)

    def test_io_read_str(self):
        buf = io.StringIO('hello\nthere\n')
        self.assertEqual("hello\n", buf.readline())
        self.assertEqual("there\n", buf.readline())
        self.assertFalse(buf.readline())

    def test_io_read(self):
        buf = io.BytesIO(b'hello\nthere\n')
        self.assertEqual("hello\n", buf.readline().decode('ascii'))
        self.assertEqual("there\n", buf.readline().decode('ascii'))
        self.assertFalse(buf.readline())

    def test_jitter_time(self):
        x = lib.jitter_time(10)
        self.assertEqual(10, len(x))

    def test_random_data(self):
        x = lib.random_data()
        self.assertEqual(1000000, len(x), 'size must be 1e6')

    def test_multi_random_data(self):
        x = lib.multi_random_data()
        self.assertEqual(1000000, len(x), 'size must be 1e6')

    def test_read_raw(self):
        raw_data = lib.read_raw('test_data.csv')
        self.assertEqual(3, len(raw_data))
        self.assertCountEqual(['measure'], list(raw_data.columns))
        raw_data = lib.read_raw('test_data_multi.csv')
        self.assertEqual(24, len(raw_data))
        self.assertCountEqual(['id','ct','measure'], list(raw_data.columns))
        raw_data = lib.read_raw_no_header('test_data_long.csv')
        self.assertEqual(24112, len(raw_data))
        self.assertCountEqual(['id','ct','measure'], list(raw_data.columns))

    def test_resolve_name(self):
        raw_data = lib.read_raw('test_data_multi.csv')
        load_data = lib.resolve_name(raw_data)
        self.assertEqual(24, len(load_data))

    def test_make_multi_hourly(self):
        raw_data = lib.read_raw('test_data_multi.csv')
        load_data = lib.resolve_name(raw_data)
        hourly = lib.make_multi_hourly(load_data)
        self.assertEqual(16, len(hourly),'one per load plus total')

    def test_make_hourly(self):
        raw_data = lib.read_raw('test_data.csv')
        hourly = lib.make_hourly(raw_data)
        self.assertEqual(1, len(hourly), 'all data is in 14:00')
        self.assertAlmostEqual(0.0001667, hourly.iloc[0].at['measure'],
            places=7, msg='total is 0.0001667')


if __name__ == '__main__':
    unittest.main()

