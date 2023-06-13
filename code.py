# s203970
# Last updated 25/05/2023

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import numpy as np
import RPi.GPIO as GPIO
import math

# Data collection setup
RATE = 64
DURATION = 200 # Chose a integration time
CALIBRATION_DURATION = 10 # Chose a thresshold time
THRESHOLD = 0.001 # Chose a thresshold

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)

i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADC objects using the I2C bus
adsPD1 = ADS.ADS1115(i2c, address=0x4a)
adsPD2 = ADS.ADS1115(i2c, address=0x4b)
adsT = ADS.ADS1115(i2c, address=0x49)

# Initialize gain-factor
adsPD1.gain = 1
adsPD2.gain = 1
adsT.gain = 4

# Set up channels
chanPD1 = AnalogIn(adsPD1, ADS.P0, ADS.P1)
chanPD2 = AnalogIn(adsPD2, ADS.P0, ADS.P1)
chanT = AnalogIn(adsT, ADS.P0, ADS.P1)

# ADC Configuration
adsPD1.mode = ADS.Mode.SINGLE
adsPD1.data_rate = RATE
adsPD2.mode = ADS.Mode.SINGLE
adsPD2.data_rate = RATE
adsT.mode = ADS.Mode.SINGLE
adsT.data_rate = RATE

sample_interval = 1.0 / RATE
total_samples = int(DURATION * RATE)

voltPD1_on = []
voltPD1_off = []

voltPD2_on= []
voltPD2_off= []

voltT = []

# Temp correectionn formula
def tempCorrPD1(x):
    return 1.4914 * math.exp(-0.016 * x)

calibration_stable = False
while not calibration_stable:
    calibration_voltPD1 = []
    calibration_voltPD2 = []

    led_interval = 32
    led_state = False

    for i in range(int(CALIBRATION_DURATION * RATE)):
        if (i % led_interval) == 0:
            led_state = not led_state
            GPIO.output(18, GPIO.HIGH if led_state else GPIO.LOW)
            time.sleep(sample_interval)

        if led_state:
            if (i % led_interval) == 1:                time.sleep(sample_interval)
            elif (i % led_interval) <= 15:
                calibration_voltPD1.append(chanPD1.voltage)
            elif (i % led_interval) <= 30:
                calibration_voltPD2.append(chanPD2.voltage)

    calibration_mean_on = np.mean(calibration_voltPD1)
    calibration_mean_off = np.mean(calibration_voltPD2)
    calibration_result = calibration_mean_on - calibration_mean_off


    calibration_stable = np.std(calibration_result) <= THRESHOLD

    # Check stability # If not repeat, if yes then move on
    if abs(calibration_result) <= THRESHOLD:
        calibration_stable = True

for i in range(total_samples):
    if (i % led_interval) == 0:
        led_state = not led_state
        GPIO.output(18, GPIO.HIGH if led_state else GPIO.LOW)
        time.sleep(sample_interval)

    if led_state: # LED on
        if (i % led_interval) == 1:
            time.sleep(sample_interval)
        elif (i % led_interval) <= 15:
            voltPD1_on.append(chanPD1.voltage - calibration_mean_on)
        elif (i % led_interval) <= 30:
            voltPD2_on.append(chanPD2.voltage - calibration_mean_off)

        if (i % led_interval) == 30:
            voltT.append(chanT.voltage)

    else: # LED off
        if (i % led_interval) >= 1 and (i % led_interval) <= 15:
            voltPD1_off.append(chanPD1.voltage - calibration_mean_off)
        elif (i % led_interval) >= 16 and (i % led_interval) <= 30:
            voltPD2_off.append(chanPD2.voltage - calibration_mean_off)

        if (i % led_interval) == 30:
            voltT.append(chanT.voltage)

# Substract dark current
voltPD1_diff=np.mean(voltPD1_on)-np.mean(voltPD1_off)
voltPD2_diff=np.mean(voltPD2_on)-np.mean(voltPD2_off)

# Correction factor
Temp_corr_factor=tempCorrPD1(voltT)

# Correct for temperature changes for PD1
voltPD1_temp=voltPD2_diff*Temp_corr_factor

# Correct for temperature changes 
# Since they have different sizes I couldn't find a way to save them in one
np.savetxt('pd1_pd2_3000_real.xlsx', np.array([voltPD1_on, voltPD1_off,voltPD2_on, voltPD2_off]).T, delimiter='\t', fmt="%s")
np.savetxt('temp_3000_real.xlsx', np.array([voltT]).T, delimiter='\t', fmt="%s")

GPIO.output(18, GPIO.LOW)  # Turn off LED
GPIO.cleanup()
