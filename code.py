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
# turn off automatic display refresh. 
# Explicit refresh functions update the display.
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

# This sets trace to near bottom of screen when gain is low
# vertical_offset = 120
adc_midscale = 32768
start_sample = 3
max_samples = 4000

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

def draw_trace(color_idx, channel):
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
          
        TODO: 
    """
    x = x_left
    horizontal_counter = channel.num_samples_per_px
    sample_index = start_sample
    while (x < x_right) and (sample_index < channel.num_samples):
        y = channel.vertical_offset - ((samples1[sample_index] - adc_midscale) >> channel.vertical_gain)
        if y > y_bottom:
            y = y_bottom
        elif y < y_top:
            y = y_top
        bitmap[x, y] = color_idx
        if horizontal_counter == 0:
            x += 1
            horizontal_counter = channel.num_samples_per_px
        else:
            horizontal_counter -= 1
        sample_index += 1
        
board.DISPLAY.refresh(minimum_frames_per_second=0)

# TODO:
# Need to make an object and save the state for different
# sensors, so that switching between them doesn't lose
# their settings.

# There needs to be a way for controls to respond more
# quickly when sample times are long.
# There needs to be a way to do screen updates during
# long sample times.
#
# Add G sensor
#
# First state initialization

vertical_input = 0

class micChannel(object):
    def __init__(self):
        
        self.vertical_offset = 64
        self.num_samples_per_px = 2
        self.num_samples = 1000
        self.vertical_gain = 5
        self.vertical_input = 0
        
        self.max_gain_limit = 12
        self.min_gain_limit = 0
        self.gain_increment = 1
        
        self.max_vertical_offset_limit = 1000
        self.min_vertical_offset_limit = -1000
        self.vertical_offset_increment = 4
        
        self.max_samples_per_px = 39
        self.min_samples_per_px = 1
        self.samples_per_px_increment = 1
        
        self.min_num_samples = 100
        self.max_num_samples = 8000
        
    def preset(self):
        global vertical_input
        vertical_input = 0
        self.vertical_offset = 64
        self.num_samples_per_px = 2
        self.vertical_gain = 5
        self.vertical_input = 0
        self.calc_num_samples()
        
    def increase_gain(self):
        if self.vertical_gain < self.max_gain_limit:
            self.vertical_gain += self.gain_increment
            
    def decrease_gain(self):
        if self.vertical_gain > self.min_gain_limit:
            self.vertical_gain -= self.gain_increment
            
    def increase_offset(self):
        if (self.vertical_offset <= self.max_vertical_offset_limit +
                                    self.vertical_offset_increment):
            self.vertical_offset += self.vertical_offset_increment
            
    def decrease_offset(self):
        if (self.vertical_offset >= self.min_vertical_offset_limit -
                                    self.vertical_offset_increment):
            self.vertical_offset -= self.vertical_offset_increment
            
    def increase_samples(self):
        if self.num_samples_per_px > self.min_samples_per_px:
            self.num_samples_per_px -= self.samples_per_px_increment
            self.calc_num_samples()

    def decrease_samples(self):
        if self.num_samples_per_px < self.max_samples_per_px:
            self.num_samples_per_px += self.samples_per_px_increment
            self.calc_num_samples()
            
    def calc_num_samples(self):
        nsamp = (1 + self.num_samples_per_px) * (x_right - x_left + start_sample + 1)
        if nsamp <= self.max_num_samples:
            self.num_samples = nsamp
        elif nsamp >= self.min_num_samples:
            self.num_samples = nsamp
        else:
            self.num_samples = self.max_num_samples

def check_buttons(pybadger, channel):
    global vertical_input
    if pybadger.button.a:
        ch1.increase_gain()
    if pybadger.button.b:
        ch1.decrease_gain()
    if pybadger.button.down:
        ch1.increase_offset()
    if pybadger.button.up:
        ch1.decrease_offset()
    if pybadger.button.left:
        ch1.increase_samples()        
    if pybadger.button.right:
        ch1.decrease_samples()
    if pybadger.button.select:
        vertical_input = 1 - vertical_input
        while pybadger.button.select:
            time.sleep(0.05)
    if pybadger.button.start:
        ch1.preset()    

ch1 = micChannel()

pale_green = [0,1,0]
pale_blue = [0,0,1]
black = [0,0,0]
sweep_led = 0
refresh_led = 4

board.DISPLAY.refresh(minimum_frames_per_second=0)

while(True):

    # Take the samples
    pybadger.pixels[sweep_led] = pale_green
    if vertical_input == 0: 
        mic.record(samples1, ch1.num_samples)
    else:
        for a in range(ch1.num_samples):
            samples1[a] = int(pybadger.light * 1)    
    pybadger.pixels[sweep_led] = black
    
    # Check the buttons
    check_buttons(pybadger, ch1)
            
    # Draw the waveform by scaling the recorded values to
    # pixels on the display.
    draw_trace(1, ch1)
    pybadger.pixels[refresh_led] = pale_blue    
    board.DISPLAY.refresh(minimum_frames_per_second=0)
    # The second retrace is still needed!
    board.DISPLAY.refresh(minimum_frames_per_second=0)
    pybadger.pixels[refresh_led] = black

    # Erase the waveform by redrawing the pixels with black.
    draw_trace(0, ch1)

    if run_slow:
        time.sleep(0.1)
