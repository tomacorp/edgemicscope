# edgemicscope - AdaFruit EDGE badge microphone oscilloscope

Program to display a microphone waveform on the display of
the AdaFruit EDGE badge.
Created at the Hack-a-day Superconference 2019.

A hardware modification is required to see the microphone output.
This change can be done with jumper wires in the connector holes:
  - Connect pin 5 (mic clk) to Tx
  - Connect pin 6 (mic data) to D12 (label is '12' on the silk screen)
The connector pins are labelled on the board.

This program requires CircuitPython v5.0.0 Alpha 5 or later.
See https://github.com/adafruit/circuitpython/releases for instructions.
The display update commands in v5.0.0 provide the display update functions.
Follow the instructions to update the badge.

To run this program:
  - Connect the EDGE badge to the computer.
  - The badge will appear as a USB drive.
  - Copy the program to the file code.py on this USB drive.
  - The file will automatically run!

