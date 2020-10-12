"""Test the library."""
from __future__ import annotations
import base64
import unittest
import numpy as np
import lib

class TestLib(unittest.TestCase):
    """Contains test cases."""
    def test_sums(self) -> None:
        """are the singletons working right?"""
        s01 = lib.Sums()
        s02 = lib.Sums()
        lib.update_stats(np.array([1, 2, 3]).astype(np.float64), s01)
        self.assertEqual(3, s01.count)
        self.assertEqual(0, s02.count)

        sum_1 = lib.allsums['load1']
        sum_2 = lib.allsums['load2']
        lib.update_stats(np.array([1, 2, 3]).astype(np.float64), sum_1.vsums)
        self.assertEqual(3, sum_1.vsums.count)
        self.assertEqual(0, sum_2.vsums.count)
        self.assertAlmostEqual(6, sum_1.vsums.total)
        self.assertAlmostEqual(0, sum_2.vsums.total)
        self.assertAlmostEqual(14, sum_1.vsums.sq_total)
        self.assertAlmostEqual(0, sum_2.vsums.sq_total)
        dump_1 = lib.dump_stats(sum_1.vsums)
        dump_2 = lib.dump_stats(sum_2.vsums)
        self.assertEqual(3, dump_1.count)
        self.assertEqual(0, dump_2.count)
        self.assertAlmostEqual(2, dump_1.mean)
        self.assertAlmostEqual(0, dump_2.mean)
        self.assertAlmostEqual(2.160246899, dump_1.rms)
        self.assertAlmostEqual(0, dump_2.rms)

    def test_update_stats(self) -> None:
        """Tests stats calculations."""
        x_in: np.ndarray[np.float64] = np.array([1, 2, 3, 4, 5]).astype(np.float64) # pylint: disable=E1136
        sums = lib.Sums()
        lib.update_stats(x_in, sums)
        self.assertEqual(5, sums.count)
        self.assertAlmostEqual(15, sums.total)
        self.assertAlmostEqual(55, sums.sq_total)
        dump = lib.dump_stats(sums)
        self.assertEqual(5, dump.count)
        self.assertAlmostEqual(3, dump.mean)
        self.assertAlmostEqual(3.31662479, dump.rms)

    def test_read_raw_no_header(self) -> None:
        """Tests file reading."""
        raw_data = lib.read_raw_no_header('test_kwh.csv')
        self.assertEqual(24, len(raw_data))
        self.assertCountEqual(['load', 'measure', 'vrms', 'arms'],
                              list(raw_data.columns))

    def test_make_multi_hourly(self) -> None:
        """Tests aggregation."""
        load_data = lib.read_raw_no_header('test_kwh.csv')
        hourly = lib.make_multi_hourly(load_data)
        self.assertEqual(16, len(hourly), 'one per load plus total')

    def test_make_hourly(self) -> None:
        """Tests aggregation for one load."""
        load_data = lib.read_raw_no_header('test_kwh.csv')
        hourly = lib.make_hourly(
            load_data[load_data['load'] == 'load1'][['measure']])
        self.assertEqual(1, len(hourly), 'all data is in 14:00')
        self.assertAlmostEqual(0.0001667, hourly.iloc[0].at['measure'],
                               places=7)

    def test_bytes_to_array(self) -> None:
        """Tests decoding."""
        # no data
        self.assertIsNone(lib.bytes_to_array([], 0))
        # data col out of range
        self.assertIsNone(lib.bytes_to_array([b'asdf'], 10))
        # if we observe 10,11,12,13,14
        encoded = base64.b85encode(bytearray(np.array([10, 11, 12, 13, 14]).astype(np.int16)))
        self.assertEqual(b'3IGcL3;+!P4gd', encoded)
        data = [encoded]
        result = lib.bytes_to_array(data, 0)
        self.assertIsNotNone(result)
        if result is not None:
            self.assertCountEqual([10, 11, 12, 13, 14], result.tolist())

    def test_goodrow(self) -> None:
        """Tests invalidity detection."""
        # None => bad
        self.assertFalse(lib.goodrow(None)) #type:ignore
        # empty => bad
        self.assertFalse(lib.goodrow([]))
        # wrong field count => bad
        self.assertFalse(
            lib.goodrow([b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8']))
        # right field count => good
        self.assertTrue(
            lib.goodrow([b'date', b'uid', b'ct', b'freq', b'len', b'buff1', b'buff2']))

    def test_decode(self) -> None:
        """Tests decoding and interpolation together."""
        # interpolation is gone, so this is all there is
        # volts: 10 11 12 13 14
        # amps:  20 21 22 23 24
        volts_amps = lib.decode(
            {b'barct1': 'foo'},
            b'0 bar ct1 10 5 3IGcL3;+!P4gd 6aW<f762Cj7yt')
        self.assertIsNotNone(volts_amps)
        if volts_amps: # this is for mypy
            self.assertEqual(5, len(volts_amps.volts))
            self.assertEqual(5, len(volts_amps.amps))
            self.assertCountEqual(
                [10.0, 11.0, 12.0, 13.0, 14.0],
                volts_amps.volts)
            self.assertCountEqual(
                [20.0, 21.0, 22.0, 23.0, 24.0],
                volts_amps.amps)

    def test_average_power_watts(self) -> None:
        """Tests power calculation."""
        # one constant volt * one constant amp = one constant watt
        pwr = lib.average_power_watts(np.array([1], dtype=np.float64),
                                      np.array([1], dtype=np.float64))
        self.assertAlmostEqual(1, pwr)

        # one volt AC * one amp AC = 0.5W
        # (max amplitude, not RMS)
        pwrp = lib.average_power_watts(
            np.sin(np.linspace(0, np.pi * 4, 2000)), #type:ignore
            np.sin(np.linspace(0, np.pi * 4, 2000))) #type:ignore
        self.assertAlmostEqual(0.5, pwrp, places=3)

    def test_interpolation_and_power(self) -> None:
        """Tests interpolation and power calculation together."""
        # same as above
        volts_amps = lib.decode(
            {b'barct1': 'foo'},
            b'0 bar ct1 10 5 3IGcL3;+!P4gd 6aW<f762Cj7yt')
        self.assertIsNotNone(volts_amps)
        if volts_amps: # this is for mypy
            pwr = lib.average_power_watts(volts_amps.volts, volts_amps.amps)
            self.assertAlmostEqual(266.0, pwr, places=3)
            self.assertEqual('foo', volts_amps.load)

    def test_rms(self) -> None:
        """test rms"""
        x_in = np.array([-5, -4, -3, -2, -1, 0, 1, 2, 3, 4])
        self.assertAlmostEqual(2.9154759, lib.rms(x_in)) #type:ignore

    def test_load(self) -> None:
        """test load"""
        x_in = lib.load({b'bc': 'e'}, [b"a", b"b", b"c", b"d"])
        self.assertEqual("e", x_in)

if __name__ == '__main__':
    unittest.main()
