import io, lib, unittest
import numpy as np
from typing import IO,List

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
        def v(va:lib.VA) -> None:
            pass
        #sink = io.StringIO()
        sink = io.BytesIO()
        i = lib.interpolator(5)
        f = lib.transcribe(sink, i, v)
        source:IO[bytes] = io.BytesIO(b'0 5701333034370A220D ct1 10 8081818181 20 8081818181')
        f(source)
        content:bytes = sink.getvalue()
        self.assertEqual(b"load5\t267.75\n", content[-13:])

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
        self.assertCountEqual(['load','measure'], list(raw_data.columns))

    def test_make_multi_hourly(self) -> None:
        load_data = lib.read_raw_no_header('test_data_multi.csv')
        hourly = lib.make_multi_hourly(load_data)
        self.assertEqual(16, len(hourly),'one per load plus total')

    def test_make_hourly(self) -> None:
        load_data = lib.read_raw_no_header('test_data_multi.csv')
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

    def test_decode_and_interpolate(self) -> None:
        i = lib.interpolator(5)
        # volts: 10 11 12 13 14
        # amps:  20 21 22 23 24
        # interpolation (volts is first):
        # volts: 10.0      11.0      12.0      13.0      14.0
        # amps:       20.0      21.0      22.0      23.0      24.0
        # interpolated:
        # volts: 10.0 10.5 11.0 11.5 12.0 12.5 13.0 13.5 14.0
        # amps:       20.0 20.5 21.0 21.5 22.0 22.5 23.0 23.5 24.0
        # trimmed:
        # volts:      10.5 11.0 11.5 12.0 12.5 13.0 13.5 14.0
        # amps:       20.0 20.5 21.0 21.5 22.0 22.5 23.0 23.5
        # 
        va = lib.decode_and_interpolate(i, b'x 0 5701333034370A220D ct1 10 8081818181 20 8081818181')
        self.assertIsNotNone(va)
        if va: # this is for mypy
            self.assertEqual(8, len(va.volts))
            self.assertEqual(8, len(va.amps))
            self.assertCountEqual([10.5,11.0,11.5,12.0,12.5,13.0,13.5,14.0], va.volts)
            self.assertCountEqual([20.0,20.5,21.0,21.5,22.0,22.5,23.0,23.5], va.amps)

    def test_average_power_watts(self) -> None:
        # one constant volt * one constant amp = one constant watt
        pwr = lib.average_power_watts([1], [1])
        self.assertEqual(1, pwr)

        # one volt AC * one amp AC = 0.5W
        # (max amplitude, not RMS)
        pwrp = lib.average_power_watts(np.sin(np.linspace(0,999,1000)), #type:ignore
                                       np.sin(np.linspace(0,999,1000))) #type:ignore
        self.assertAlmostEqual(0.5, pwrp, places=3)

    def test_interpolation_and_power(self) -> None:
        i = lib.interpolator(5)
        # same as above
        va = lib.decode_and_interpolate(i, b'x 0 5701333034370A220D ct1 10 8081818181 20 8081818181')
        self.assertIsNotNone(va)
        if va: # this is for mypy
            pwr = lib.average_power_watts(va.volts, va.amps)
            self.assertAlmostEqual(267.75, pwr, places=3)
            self.assertEqual(b'load5', va.load)

    def test_readline(self) -> None:
        class FakeSerial:
            def __init__(self):
                self.bytes = b'asdf\nqwerty\n'
                self.in_waiting = len(self.bytes)
            def read(self, i):
                x = self.bytes[:i]
                self.bytes = self.bytes[i:]
                return x
        f = FakeSerial()
        rl = lib.ReadLine(f)
        line = rl.readline()
        self.assertEqual(b'asdf\n',line)
        line = rl.readline()
        self.assertEqual(b'qwerty\n',line)

if __name__ == '__main__':
    unittest.main()
