import io
import lib
import unittest
from typing import List

# show how to do a unittest of a naked function

class TestLib(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertIsNone(lib.parse(""))
        self.assertIsNone(lib.parse("a b c d"))
        self.assertIsNone(lib.parse("2020-04-18T17:04:27.322422 b c d"))
        self.assertIsNone(lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr c d"))
        self.assertIsNone(lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr xyz d"))
        x = lib.parse(
            "2020-04-18T17:04:27.322422 abcdefghijklmnopqr xyz 1.0")
        self.assertEqual("2020-04-18 17:04:27.322422", str(x['time'])) #type:ignore
        self.assertEqual("abcdefghijklmnopqr", x['id']) #type:ignore
        self.assertEqual("xyz", x['ct']) #type:ignore
        self.assertAlmostEqual(1.0, x['measure'], 3) #type:ignore

    def test_transcribe(self) -> None:
        sink = io.StringIO()
        source = io.BytesIO(b"asdf\n")
        f = lib.transcribe(sink)
        f(source)
        content = sink.getvalue()
        self.assertEqual("asdf\n", content[-5:])

    def test_io_write_str(self) -> None:
        output = io.StringIO()
        output.write('hi')
        content = output.getvalue()
        output.close()
        self.assertEqual("hi", content)

    def test_io_write(self) -> None:
        output = io.BytesIO()
        output.write(b'hi')
        content = output.getvalue().decode('ascii')
        output.close()
        self.assertEqual("hi", content)

    def test_io_read_str(self) -> None:
        buf = io.StringIO('hello\nthere\n')
        self.assertEqual("hello\n", buf.readline())
        self.assertEqual("there\n", buf.readline())
        self.assertFalse(buf.readline())

    def test_io_read(self) -> None:
        buf = io.BytesIO(b'hello\nthere\n')
        self.assertEqual("hello\n", buf.readline().decode('ascii'))
        self.assertEqual("there\n", buf.readline().decode('ascii'))
        self.assertFalse(buf.readline())

    def test_read_raw_no_header(self) -> None:
        raw_data = lib.read_raw_no_header('test_data_multi.csv')
        self.assertEqual(24, len(raw_data))
        self.assertCountEqual(['id','ct','measure'], list(raw_data.columns))
        raw_data = lib.read_raw_no_header('test_data_long.csv')
        self.assertEqual(24112, len(raw_data))
        self.assertCountEqual(['id','ct','measure'], list(raw_data.columns))

    def test_resolve_name(self) -> None:
        raw_data = lib.read_raw_no_header('test_data_multi.csv')
        load_data = lib.resolve_name(raw_data)
        self.assertEqual(24, len(load_data))

    def test_make_multi_hourly(self) -> None:
        raw_data = lib.read_raw_no_header('test_data_multi.csv')
        load_data = lib.resolve_name(raw_data)
        hourly = lib.make_multi_hourly(load_data)
        self.assertEqual(16, len(hourly),'one per load plus total')

    def test_make_hourly(self) -> None:
        raw_data = lib.read_raw_no_header('test_data_multi.csv')
        load_data = lib.resolve_name(raw_data)
        hourly = lib.make_hourly(
                 load_data[load_data['load']=='load1'][['measure']])
        self.assertEqual(1, len(hourly), 'all data is in 14:00')
        self.assertAlmostEqual(0.0001667, hourly.iloc[0].at['measure'],
            places=7, msg='total is 0.0001667')

    def test_readfile(self) -> None:
        raw_data = lib.readfile('new_raw.csv')
        self.assertEqual(1, len(raw_data))

    def test_read_new_raw(self) -> None:
        raw_data = lib.read_new_raw('new_raw.csv')
        self.assertEqual(1, len(raw_data))

    def test_bytes_to_array(self) -> None:
        def i(x:List[int])->List[int]:
            return x
        # no data
        self.assertIsNone(lib.bytes_to_array(i,[], 0, 0, True))
        # data col out of range
        self.assertIsNone(lib.bytes_to_array(i,[b'asdf'], 5, 4, True))
        self.assertIsNone(lib.bytes_to_array(i,[b'asdf'], 5, 4, True))
        # if we observe 10,11,12,13,14
        # then we record first = 10, deltas = 0,1,2,3,4
        # add 128, hex, so 80, 81, 81, 81, 81
        # note the first observation needs to be zero TODO fix that
        # note the interpolator is a passthrough, and we trim the first
        data = [b'10',b'8081818181']
        self.assertCountEqual([11,12,13,14],
                             lib.bytes_to_array(i,data, 1, 0, True))

    def test_interpolator(self) -> None:
        i = lib.interpolator(5)
        r = i([1,2,3,4,5])
        # interpolates the midpoints
        self.assertEqual(9, len(r))
        self.assertCountEqual([1,1.5,2,2.5,3,3.5,4,4.5,5], r)

    def test_goodrow(self) -> None:
        # None => bad
        self.assertFalse(lib.goodrow(None)) #type:ignore
        # empty => bad
        self.assertFalse(lib.goodrow([]))
        # error col not zero => bad
        self.assertFalse(lib.goodrow([b'1',b'2',b'3',b'4',b'5',b'6',b'7',b'8']))
        # error col zero => good
        self.assertTrue(lib.goodrow([b'1',b'0',b'3',b'4',b'5',b'6',b'7',b'8']))


if __name__ == '__main__':
    unittest.main()

