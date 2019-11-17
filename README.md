# edgemicscope
AdaFruit EDGE badge microphone oscilloscope

Created at the Hack-a-day Superconference 2019
Hardware modification needed to run this:

Program to display a microphone waveform on the display of
the AdaFruit EDGE badge
Hardware change requirement:
  - Connect pin 5 (mic clk) to Tx
  - Connect pin 6 (mic data) to D12 (label is '12' on the silk screen)

This requires CircuitPython v5.0.0 or later.
The display update commands in v5 help with the display code.

