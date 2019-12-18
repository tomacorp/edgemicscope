# edgemicscope - AdaFruit EDGE badge microphone oscilloscope

This Python program creates a scope app for the AdaFruit EDGE badge.
The graph display shows output from the microphone, accelerometer, light sensor,
and a generated sawtooth wave. Adjust the sweep time and sensitivity
with the badge buttons.

code.py - Copy this file to the EDGE badge, and it runs!

A hardware modification is required to see the microphone output.
The code runs without this modification, and shows the other sensor outputs.
This change can be done with jumper wires in the connector holes:
  - Connect pin 5 (mic clk) to Tx
  - Connect pin 6 (mic data) to D12 (label is '12' on the silk screen)
The connector pins are labelled on the board.

This program requires CircuitPython v5.0.0 Alpha 5 or later.
See https://github.com/adafruit/circuitpython/releases for instructions.
The display update commands in v5.0.0 provide the display update functions.
Follow the instructions below to update the badge if needed.

To run this program:
  - Connect the EDGE badge to the computer.
  - The badge will appear as a USB drive.
  - Copy either program to the file code.py on this USB drive.
  - The file will automatically run!

Updating the EDGE firmware is easy:
  - Eject the USB drive
  - Double click the reset button on the EDGE to mount the firmware drive
  - Copy the new firmware file to the firmware drive
  - That is all!

Button functions:
 - Select: Select the input channel microphone, light sensor, accelerometer, or sawtooth.
 - A, B: Adjust gain up and down
 - Left, Right: Adjust sweep time
 - Up, Down: Adjust offset
 - Start: Restore defaults for channel gain, offset, and sweep time

