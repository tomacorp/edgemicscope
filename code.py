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

https://www.adafruitdaily.com/2019/11/19/a-supercon-was-had-arm-aiot-dev-summit-is-almost-here-and-more-python-adafruit-circuitpython-pythonhardware-circuitpython-micropython-thepsf-adafruit/

"""

from adafruit_debouncer import Debouncer
import array
import math
import time
import audiobusio
import displayio
import board
import analogio

from collections import namedtuple
from micropython import const
import digitalio
import audioio
from gamepadshift import GamePadShift
import neopixel
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label
import terminalio
import adafruit_lis3dh

Buttons = namedtuple("Buttons", "b a start select right down up left")

# pylint: disable=too-many-instance-attributes
class PyBadger:
    """PyBadger class."""
    # Button Constants
    BUTTON_LEFT = const(128)
    BUTTON_UP = const(64)
    BUTTON_DOWN = const(32)
    BUTTON_RIGHT = const(16)
    BUTTON_SELECT = const(8)
    BUTTON_START = const(4)
    BUTTON_A = const(2)
    BUTTON_B = const(1)

    def __init__(self, i2c=None):
        # Accelerometer
        if i2c is None:
            try:
                i2c = board.I2C()
            except RuntimeError:
                self._accelerometer = None

        if i2c is not None:
            int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
            try:
                self._accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19, int1=int1)
            except ValueError:
                self._accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)

        # Buttons
        self._buttons = GamePadShift(digitalio.DigitalInOut(board.BUTTON_CLOCK),
                                     digitalio.DigitalInOut(board.BUTTON_OUT),
                                     digitalio.DigitalInOut(board.BUTTON_LATCH))

        # Display
        self.display = board.DISPLAY

        # Light sensor
        self._light_sensor = analogio.AnalogIn(board.A7)

        # NeoPixels
        # Count is hardcoded - should be based on board ID, currently no board info for PyBadge LC
        neopixel_count = 5
        self._neopixels = neopixel.NeoPixel(board.NEOPIXEL, neopixel_count,
                                            pixel_order=neopixel.GRB)

    @property
    def pixels(self):
        """Sequence like object representing the NeoPixels on the board."""
        return self._neopixels

    @property
    def button(self):
        button_values = self._buttons.get_pressed()
        return Buttons(*[button_values & button for button in
                         (PyBadger.BUTTON_B, PyBadger.BUTTON_A, PyBadger.BUTTON_START,
                          PyBadger.BUTTON_SELECT, PyBadger.BUTTON_RIGHT,
                          PyBadger.BUTTON_DOWN, PyBadger.BUTTON_UP, PyBadger.BUTTON_LEFT)])

    @property
    def light(self):
        """Light sensor data."""
        return self._light_sensor.value

    @property
    def acceleration(self):
        """Accelerometer data."""
        return self._accelerometer.acceleration if self._accelerometer is not None else None

    @property
    def brightness(self):
        """Display brightness."""
        return self.display.brightness

    @brightness.setter
    def brightness(self, value):
        self.display.brightness = value

pybadger = PyBadger()

# Record up to 0.5 seconds of audio
samples1 = array.array('H', [0] * 8000)

display = board.DISPLAY

# To synchronize the display update to the waveform update,
# turn off automatic display refresh.
# Explicit refresh functions update the display.
# The display refresh feature requires CircuitPython v5.0.0 or later.

board.DISPLAY.auto_refresh = False
 
# Create a bitmap with colors
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

# Define the bounds of the graph
x_left = 10
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
          
       Channel settings:   
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
    horizontal_counter = channel.num_samples_per_px
    sample_index = channel.start_sample
    while (x < x_right) and (sample_index < channel.num_samples):
        y = channel.vertical_offset - ((channel.samples[sample_index] - 
                channel.adc_midscale) >> channel.vertical_gain)
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
# Would like to have a button interrupt, especially for start/preset()
# Debounce button method for all buttons
#
# Add accelerometer channel
#

class sensorChannel(object):
    def __init__(self, pybadger):
        self.pybadger = pybadger
        
        self.vertical_offset = 64
        self.num_samples_per_px = 2
        self.num_samples = 1000
        self.vertical_gain = 5
        self.vertical_input = 0
        self.start_sample = 3
        self.adc_midscale = 32768
        
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
        self.vertical_offset = 64
        self.num_samples_per_px = 2
        self.vertical_gain = 5
        self.vertical_input = 0
        self.calc_num_samples()
     
    @property
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
        nsamp = (1 + self.num_samples_per_px) * (x_right - x_left + 1) \
                + self.start_sample
        if nsamp <= self.max_num_samples:
            self.num_samples = nsamp
        elif nsamp >= self.min_num_samples:
            self.num_samples = nsamp
        else:
            self.num_samples = self.max_num_samples

    def buttons(self):
        
        if self.pybadger.button.a:
            self.increase_gain
        if self.pybadger.button.b:
            self.decrease_gain()
        if self.pybadger.button.down:
            self.increase_offset()
        if self.pybadger.button.up:
            self.decrease_offset()
        if self.pybadger.button.left:
            self.increase_samples()        
        if self.pybadger.button.right:
            self.decrease_samples()

        if self.pybadger.button.start:
            self.preset()  
            
class micChannel(sensorChannel):
    """ Class to use the light sensor as a data channel. """
    
    def __init__(self, board, pybadger, samples):
        super().__init__(pybadger)
        self.samples = samples
        self.board = board
        self.mic = audiobusio.PDMIn(
                board.TX,
                board.D12,
                sample_rate=16000,
                bit_depth=16)
        
    def take_sweep(self):
        """ Take a sweep of sound samples."""
        
        self.mic.record(self.samples, self.num_samples)
        
class lightChannel(sensorChannel):
    """ Class to use the light sensor as a data channel. """
        
    def __init__(self, board, pybadger, samples):
        super().__init__(pybadger)
        self.samples = samples
        self.board = board
        self.pybadger = pybadger
        
    def preset(self):
        super().preset()
        self.vertical_gain = 8
        self.vertical_offset = 0
        # self._light_sensor = analogio.AnalogIn(board.A7)
        
    def take_sweep(self):
        """ Take a sweep of light samples."""
           
        for a in range(self.num_samples):
            self.samples[a] = int(self.pybadger.light * 1)
            # self.samples[a] = int(self._light_sensor.value)
                
class sawtoothChannel(sensorChannel):
    """ Class to use a generated sawtooth waveform as a data channel. """
        
    def __init__(self, board, pybadger, samples):
        super().__init__(pybadger)
        self.samples = samples
        self.board = board
        self.pybadger = pybadger
        self.vert_peak = 1000
        self.vert_start = 32768 - self.vert_peak
        self.vert_stop = 32768 + self.vert_peak
        self.vert_incr = 25
        self.vert = self.vert_start
        
    def preset(self):
        
        super().preset()
        self.vertical_gain = 5
        self.vertical_offset = 68
        
    def take_sweep(self):
        """ Generate a sawtooth waveform with math, no measurement."""
        
        for idx in range(self.num_samples):
            self.samples[idx] = self.vert
            if self.vert + self.vert_incr > self.vert_stop:
                self.vert = self.vert_start
            else:
                self.vert += self.vert_incr  
        
mic_channel = micChannel(board, pybadger, samples1)
mic_channel.preset()

light_channel = lightChannel(board, pybadger, samples1)
light_channel.preset()

sawtooth_channel = sawtoothChannel(board, pybadger, samples1)
sawtooth_channel.preset()

pale_green = [0,1,0]
pale_blue = [0,0,1]
black = [0,0,0]
sweep_led = 0
refresh_led = 4

board.DISPLAY.refresh(minimum_frames_per_second=0)

channel = light_channel
vertical_input = 1

run_slow = False

def debounce(btn):
    pressed = False
    if pybadger.button[btn]:
        pressed = True
        pybadger.pixels[2] = pale_green
        while pybadger.button[btn]:
            pybadger.pixels[2] = pale_blue
            time.sleep(0.05)
    else:
        pybadger.pixels[2] = black  
    return pressed

while(True):
    
    # Check the buttons for the channel
    channel.buttons()
    
    if debounce(3):
        vertical_input += 1
        if vertical_input > 2:
            vertical_input = 0  
        
        if vertical_input == 0:
            channel = mic_channel
        elif vertical_input == 1:
            channel = light_channel
        else:
            channel = sawtooth_channel
        
    # Turn the sweep LED on while taking samples
    pybadger.pixels[sweep_led] = pale_green
    channel.take_sweep()
    pybadger.pixels[sweep_led] = black
            
    # Draw the waveform to pixels on the display.
    # During the display update, light the refresh LED.
    pybadger.pixels[refresh_led] = pale_blue
    draw_trace(1, channel)
    
    # Refresh the display. Repeat the call until it completes.
    while not board.DISPLAY.refresh(minimum_frames_per_second=0):
        pass
        
    # Erase the waveform by redrawing the pixels with black.
    draw_trace(0, channel)
    pybadger.pixels[refresh_led] = black
