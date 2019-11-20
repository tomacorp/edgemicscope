# Tom Anderson
# Tue Nov 19 20:25:05 PST 2019

"""
Program to display a microphone waveform on the display of
the AdaFruit EDGE badge.

 Hardware change requirement:
   Connect pin 5 (mic clk) to Tx
   Connect pin 6 (mic data) to D12 (label is '12' on the silk screen)
 This requires CircuitPython v5.0.0 beta or later

User interface buttons:
B:     more gain
A:     less gain  
Up:    push trace up
Down:  push trace down
Left:  faster sweep, fewer points
Right: slower sweep, more points

"""

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

# Record up to 0.5 seconds of audio
samples1 = array.array('H', [0] * 8000)

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

vertical_offset = 64
# This sets trace to near bottom of screen when gain is low
# vertical_offset = 120
adc_midscale = 32768
start_sample = 3

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

num_samples_per_px = 2
num_samples = (1 + num_samples_per_px) * (x_right - x_left + start_sample + 1)
vertical_gain = 5

def draw_trace(color_idx):
    """Draw a trace on the screen"""

    """Globals:
        Screen:
          - x_left
          - x_right
          - y_bottom
          - y_top
        Display:
          - num_samples_per_px
          - adc_midscale
          - vertical_offset
          - vertical_gain
        Sampling:
          - start_sample
          - num_samples
    """
    x = x_left
    horizontal_counter = num_samples_per_px
    sample_index = start_sample
    while (x < x_right) and (sample_index < num_samples):
        y = vertical_offset - ((samples1[sample_index] - adc_midscale) >> vertical_gain)
        if y > y_bottom:
            y = y_bottom
        elif y < y_top:
            y = y_top
        bitmap[x, y] = color_idx
        if horizontal_counter == 0:
            x += 1
            horizontal_counter = num_samples_per_px
        else:
            horizontal_counter -= 1
        sample_index += 1

while(True):

    # Take the samples
    mic.record(samples1, num_samples)
    
    # Check the buttons
    if pybadger.button.a:
        if vertical_gain < 12:
            vertical_gain += 1
    if pybadger.button.b:
        if vertical_gain > 0:
            vertical_gain -= 1
    if pybadger.button.down:
        if vertical_offset < 1000:
            vertical_offset += 4
    if pybadger.button.up:
        if vertical_offset > -1000:
            vertical_offset -= 4
    if pybadger.button.left:
        if num_samples_per_px > 1:
            num_samples_per_px -= 1
            num_samples = (1 + num_samples_per_px) * (x_right - x_left + start_sample + 1)
    if pybadger.button.right:
        if num_samples_per_px < 40:
            num_samples_per_px += 1
            num_samples = (1 + num_samples_per_px) * (x_right - x_left + start_sample + 1)
            
    # Draw the waveform by scaling the recorded values to
    # pixels on the display.
    draw_trace(1)

    board.DISPLAY.refresh(minimum_frames_per_second=0)
    # Don't know why this second refresh is required.
    # Looks like a bug!
    board.DISPLAY.refresh(minimum_frames_per_second=0)

    # Erase the waveform by redrawing the pixels with black.
    draw_trace(0)

    if run_slow:
        time.sleep(0.1)
