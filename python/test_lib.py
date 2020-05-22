"""Test the library."""
from __future__ import annotations
from typing import List
import unittest
import numpy as np
import lib

class TestLib(unittest.TestCase):
    """Contains test cases."""
    def test_sums(self) -> None:
        """are the singletons working right?"""
        s01 = lib.Sums()
        s02 = lib.Sums()
        lib.update_stats([1,2,3], s01)
        self.assertEqual(3, s01.count)
        self.assertEqual(0, s02.count)

        s1 = lib.allsums['load1']
        s2 = lib.allsums['load2']
        lib.update_stats([1,2,3], s1.vsums)
        self.assertEqual(3, s1.vsums.count)
        self.assertEqual(0, s2.vsums.count)
        self.assertAlmostEqual(6, s1.vsums.total)
        self.assertAlmostEqual(0, s2.vsums.total)
        self.assertAlmostEqual(14, s1.vsums.sq_total)
        self.assertAlmostEqual(0, s2.vsums.sq_total)
        d1 = lib.dump_stats(s1.vsums)
        d2 = lib.dump_stats(s2.vsums)
        self.assertEqual(3, d1.count)
        self.assertEqual(0, d2.count)
        self.assertAlmostEqual(2, d1.mean)
        self.assertAlmostEqual(0, d2.mean)
        self.assertAlmostEqual( 2.160246899, d1.rms)
        self.assertAlmostEqual(0, d2.rms)

    def test_update_stats(self) -> None:
        """Tests stats calculations."""
        x = [1,2,3,4,5]
        s = lib.Sums()
        lib.update_stats(x,s)
        self.assertEqual(5, s.count)
        self.assertAlmostEqual(15, s.total)
        self.assertAlmostEqual(55, s.sq_total)
        ss = lib.dump_stats(s)
        self.assertEqual(5, ss.count)
        self.assertAlmostEqual(3, ss.mean)
        self.assertAlmostEqual(3.31662479, ss.rms)

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
        def interp(samples: List[int])->List[int]:
            return samples
        # no data
        self.assertIsNone(lib.bytes_to_array(interp, [], 0, 0, True))
        # data col out of range
        self.assertIsNone(lib.bytes_to_array(interp, [b'asdf'], 5, 4, True))
        self.assertIsNone(lib.bytes_to_array(interp, [b'asdf'], 5, 4, True))
        # if we observe 10,11,12,13,14
        # then we record first = 10, deltas = 0,1,2,3,4
        # add 128, hex, so 80, 81, 81, 81, 81
        # note the first observation needs to be zero TODO fix that
        # note the interpolator is a passthrough, and we trim the first
        data = [b'10', b'8081818181']
        self.assertCountEqual(
            [11, 12, 13, 14], lib.bytes_to_array(interp, data, 1, 0, True))

    def test_interpolator(self) -> None:
        """Tests interpolation."""
        interp = lib.interpolator(5)
        result = interp([1, 2, 3, 4, 5])
        # interpolates the midpoints
        self.assertEqual(9, len(result))
        self.assertCountEqual([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5], result)

    def test_goodrow(self) -> None:
        """Tests invalidity detection."""
        # None => bad
        self.assertFalse(lib.goodrow(None)) #type:ignore
        # empty => bad
        self.assertFalse(lib.goodrow([]))
        # error col not zero => bad
        self.assertFalse(
            lib.goodrow([b'1', b'2', b'3', b'4', b'5', b'6', b'7', b'8']))
        # error col zero => good
        self.assertTrue(
            lib.goodrow([b'1', b'0', b'3', b'4', b'5', b'6', b'7', b'8']))

    def test_decode_and_interpolate(self) -> None:
        """Tests decoding and interpolation together."""
        interp = lib.interpolator(5)
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
        volts_amps = lib.decode_and_interpolate(
            interp,
            b'x 0 5737333034370A220D ct1 10 8081818181 20 8081818181')
        self.assertIsNotNone(volts_amps)
        if volts_amps: # this is for mypy
            self.assertEqual(8, len(volts_amps.volts))
            self.assertEqual(8, len(volts_amps.amps))
            self.assertCountEqual(
                [10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0],
                volts_amps.volts)
            self.assertCountEqual(
                [20.0, 20.5, 21.0, 21.5, 22.0, 22.5, 23.0, 23.5],
                volts_amps.amps)

    def test_average_power_watts(self) -> None:
        """Tests power calculation."""
        # one constant volt * one constant amp = one constant watt
        pwr = lib.average_power_watts([1], [1])
        self.assertAlmostEqual(1, pwr)

        # one volt AC * one amp AC = 0.5W
        # (max amplitude, not RMS)
        pwrp = lib.average_power_watts(
            np.sin(np.linspace(0, np.pi * 4, 2000)), #type:ignore
            np.sin(np.linspace(0, np.pi * 4, 2000))) #type:ignore
        self.assertAlmostEqual(0.5, pwrp, places=3)

    def test_interpolation_and_power(self) -> None:
        """Tests interpolation and power calculation together."""
        interp = lib.interpolator(5)
        # same as above
        volts_amps = lib.decode_and_interpolate(
            interp,
            b'x 0 5737333034370A220D ct1 10 8081818181 20 8081818181')
        self.assertIsNotNone(volts_amps)
        if volts_amps: # this is for mypy
            pwr = lib.average_power_watts(volts_amps.volts, volts_amps.amps)
            self.assertAlmostEqual(267.75, pwr, places=3)
            self.assertEqual(b'load5', volts_amps.load)

    def test_rms(self) -> None:
        x = np.array([-5, -4, -3, -2, -1, 0, 1, 2, 3, 4])
        self.assertAlmostEqual(2.9154759, lib.rms(x))

if __name__ == '__main__':
    unittest.main()
