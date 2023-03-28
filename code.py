import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Mode
from adafruit_ads1x15.analog_in import AnalogIn
import csv

# Data collection setup
RATE = 860
SAMPLES = 8600

# Create the I2C bus with a fast frequency
i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)

# Create the ADC object using the I2C bus
adsPD1 = ADS.ADS1115(i2c, address=0x4a)
adsPD2 = ADS.ADS1115(i2c, address=0x4b)
adsT = ADS.ADS1115(i2c, address=0x49)

# Initialize gain-factor / Leg med disse tal
adsPD1.gain = 4
adsPD2.gain = 2
adsT.gain = 4

# Set up analog input channels
chanPD1 = AnalogIn(adsPD1, ADS.P1)
chanPD2 = AnalogIn(adsPD2, ADS.P1)
chanT = AnalogIn(adsT, ADS.P0)

# ADC Configuration
adsPD1.mode = Mode.CONTINUOUS
adsPD1.data_rate = RATE
adsPD2.mode = Mode.CONTINUOUS
adsPD2.data_rate = RATE
adsT.mode = Mode.CONTINUOUS
adsT.data_rate = RATE

# First ADC channel read in continuous mode configures device and waits 2 conversion cycles
_ = chanPD1.value
_ = chanPD2.value
_ = chanT.value

sample_intervalPD1 = 1.0 / adsPD1.data_rate
sample_intervalPD2 = 1.0 / adsPD2.data_rate
sample_intervalT = 1.0 / adsT.data_rate

repeats = 0
skips = 0

dataPD1, dataPD2, dataT = [], [], []
voltPD1, voltPD2, voltT = [], [], []

for j, channel in enumerate([(chanPD1, dataPD1, voltPD1, sample_intervalPD1),
                              (chanPD2, dataPD2, voltPD2, sample_intervalPD2),
                              (chanT, dataT, voltT, sample_intervalT)]):
    start = time.monotonic()
    time_next_sample = start

    # Read the same channel over and over
    for i in range(SAMPLES):
        # Wait for expected conversion finish time
        while time.monotonic() < time_next_sample:
            pass

        # Read conversion value for ADC channel
        channel[1].append(channel[0].value)
        channel[2].append(channel[0].voltage)

        # Loop timing
        time_last_sample = time_next_sample
        time_next_sample += channel[3]
        if time.monotonic() > (time_next_sample + channel[3]):
            skips += 1
            time_next_sample = time.monotonic() + channel[3]

        # Detect repeated values due to over polling
        if i > 0 and channel[1][-1] == channel[1][-2]:
            repeats += 1

    end = time.monotonic()
    if j == 0:
        time0 = end - start
        print("    Reported        = {:5d}    sps for PD1".format(adsPD1.data_rate))
        print("This took {0} seconds".format(time0))
    if j == 1:
        time1 = end - start
        print("    Reported        = {:5d}    sps for PD2".format(adsPD2.data_rate))
        print("This took {0} seconds".format(time1))
    if j == 2:
        time2 = end - start
        print("    Reported        = {:5d}    sps for T".format(adsT.data_rate))
        print("This took {0} seconds".format(time2))

total_time = time0 + time1 + time2

rate_reported = SAMPLES*3.0 / total_time
rate_actual = (SAMPLES*3.0 - repeats) / total_time

print("SIU")

with open('output.txt', 'w') as file:
    file.write("Took {:5.3f} s to acquire {:d} samples.\n".format(total_time, SAMPLES*3))
    file.write("\n")
    file.write("Configured:\n")
    file.write("    Requested       = {:5d}    sps\n".format(RATE))
    file.write("\n")
    file.write("Actual:\n")
    file.write("    Polling Rate    = {:8.2f} sps\n".format(rate_reported))
    file.write("                      {:9.2%}\n".format(rate_reported / RATE))
    file.write("    Skipped         = {:5d}\n".format(skips))
    file.write("    Repeats         = {:5d}\n".format(repeats))
    file.write("    Conversion Rate = {:8.2f} sps   (estimated)\n".format(rate_actual))
    file.write("\n")
    for i in range(len(voltPD1)):
        file.write(str(voltPD1[i]) + ',' + str(voltPD2[i]) + ',' + str(voltT[i]) + '\n')
