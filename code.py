#
# Program to display a microphone waveform on the display of
# the AdaFruit EDGE badge
# Hardware change requirement:
#   Connect pin 5 (mic clk) to Tx
#   Connect pin 6 (mic data) to D12 (label is '12' on the silk screen)
# This requires CircuitPython v5.0.0 or later
#

from adafruit_pybadger import PyBadger
import array
import math
import time
import audiobusio
import displayio
import board

pybadger = PyBadger()
pybadger.auto_dim_display(delay=30)

first_display = True
run_slow = False

mic = audiobusio.PDMIn(
    board.TX,
    board.D12,
    sample_rate=16000,
    bit_depth=16
    )

samples1 = array.array('H', [0] * 150)

display = board.DISPLAY

# To synchronize the display update to the waveform update,
# turn off automatic display refresh. Explicit refresh
# functions update the display.
# The display refresh feature requires CircuitPython v5.0.0 or later.

board.DISPLAY.auto_refresh = False
 
# Create a bitmap with two colors
ncolors = 3
bitmap = displayio.Bitmap(display.width, display.height, ncolors)
 
# Create a color palette
palette = displayio.Palette(ncolors)
palette[0] = 0x000000
palette[1] = 0x00ff00
palette[2] = 0xaaaaaa
 
# Create a TileGrid using the Bitmap and Palette
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
 
# Create a Group
group = displayio.Group()
 
# Add the TileGrid to the Group
group.append(tile_grid)
 
# Add the Group to the Display
display.show(group)
 
# The display width is 160 and the height is 128
#   Positive y is down
#   Positive x is right
 
# Scale from -2000 to 2000
# Mid display is 64
# y = 64 + 64/2000*ADC value

display_offset = 64
midscale = 32768
n_sample = 140
start_sample = 3
stop_sample = n_sample + start_sample

# Define the bounds of the graph
x_left = 10 - start_sample
x_right = 140
y_bottom = 120
y_top = 20

# Draw a frame around the graph
for px in range(x_left-1, x_right+1):
    bitmap[px, y_top-1] = 2
    bitmap[px, y_bottom+1] = 2
for py in range(y_top-1, y_bottom+1):
    bitmap[x_left-1, py] = 2
    bitmap[x_right+1, py] = 2

while(True):

    mic.record(samples1, len(samples1))
    board.DISPLAY.refresh(minimum_frames_per_second=0)

    # Draw the waveform by scaling the recorded values to
    # pixels on the display.
    x = x_left
    for sample_index in range(start_sample, stop_sample):
        y = display_offset - ((samples1[sample_index] - midscale) >> 6)
        if y > y_bottom:
            y = y_bottom
        elif y < y_top:
            y = y_top
        bitmap[x, y] = 1
        x += 1
        if x > x_right:
            break

    board.DISPLAY.refresh(minimum_frames_per_second=0)

    # Erase the pixels
    x = x_left
    for sample_index in range(start_sample, stop_sample):
        y = display_offset - ((samples1[sample_index] - midscale) >> 6)
        if y > y_bottom:
            y = y_bottom
        elif y < y_top:
            y = y_top
        bitmap[x, y] = 0
        x += 1
        if x > x_right:
            break

    if run_slow:
        time.sleep(0.1)

