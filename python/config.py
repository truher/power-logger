"""configuration"""
# FOR TEENSY, uses UID
loadnames = {
    b"4E4552361001000Bct0": "load1",
    b"4E4552361001000Bct1": "load2",
    b"4E4552361001000Bct2": "load3",
    b"4E4552361001000Bct3": "load4",
    b"4E4552361001000Bct4": "load5",
    b"4E4552361001000Bct5": "load6",
    b"4E4552361001000Bct6": "load7",
    b"4E4552361001000Bct7": "load8",
    b"4E4552361001000Bct8": "load9",
    b"4E4552361001000Bct9": "load10",
    b"4E4552361001000Bct10": "load11",
    b"4E4552361001000Bct11": "load12",
    b"4E4552361001000Bct12": "load13",
    b"4E4552361001000Bct13": "load14",
    b"4E4552361001000Bct14": "load15",
    b"4E4552361001000Bct15": "load16"
}

# FOR A PAIR OF LEONARDOS WITH EMONTX SHIELDS
#loadnames = {b"5737333034370D0E14ct1": 'load1',
#             b"5737333034370D0E14ct2": 'load2',
#             b"5737333034370D0E14ct3": 'load3',
#             b"5737333034370D0E14ct4": 'load4',
#             b"5737333034370A220Dct1": 'load5',
#             b"5737333034370A220Dct2": 'load6',
#             b"5737333034370A220Dct3": 'load7',
#             b"5737333034370A220Dct4": 'load8'}

# FOR A SINGLE MEGA WITH CUSTOM SHIELD
#loadnames = {b"6E756E6B776F000C02ct2": 'load1',
#             b"6E756E6B776F000C02ct3": 'load2',
#             b"6E756E6B776F000C02ct4": 'load3',
#             b"6E756E6B776F000C02ct5": 'load4',
#             b"6E756E6B776F000C02ct6": 'load5',
#             b"6E756E6B776F000C02ct7": 'load6',
#             b"6E756E6B776F000C02ct8": 'load7',
#             b"6E756E6B776F000C02ct9": 'load8',
#             b"6E756E6B776F000C02ct10": 'load9',
#             b"6E756E6B776F000C02ct11": 'load10',
#             b"6E756E6B776F000C02ct12": 'load11',
#             b"6E756E6B776F000C02ct13": 'load12',
#             b"6E756E6B776F000C02ct14": 'load13',
#             b"6E756E6B776F000C02ct15": 'load14'}

# see
# https://docs.google.com/spreadsheets/d/1L5l22Gl8_NVvAKYv-z71Cd4lBbWYdaJ1Pb2_rq0OKFM/edit#
# sample period of about a minute

# Vrms, according to Fluke
ACTUAL_RMS_VOLTS = 117.2
# Arms, according to Extech
ACTUAL_RMS_AMPS = 2.02

# mean Vrms (stdev) from data_sample.csv
# TODO: make these right
sample_rms_volts = [-2398.757,
                    -2398.734,
                    -2398.684,
                    -2398.664,
                    -2398.642,
                    -2398.498,
                    -2398.670,
                    -2398.895,
                     1200.740,
                     1200.560,
                     1200.634,
                     1200.660,
                    -1196.481,
                    -1196.482,
                    -1196.533,
                    -1196.506]
# mean Arms from data_sample.csv
sample_rms_amps = [39.859,
                   38.326,
                   41.334,
                   39.611,
                   49.721,
                   42.410,
                   40.880,
                   40.218,
                   106.423,
                   106.009,
                   108.173,
                   107.205,
                   110.624,
                   109.435,
                   108.456,
                   108.627]

scale_rms_volts = dict(zip(loadnames.values(), sample_rms_volts))
scale_rms_amps = dict(zip(loadnames.values(), sample_rms_amps))
