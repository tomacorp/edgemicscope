# Tom Anderson
# Tue Nov 19 20:25:05 PST 2019
# Sat Dec 21 18:57:39 PST 2019

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

For a photos and a description see:
https://www.adafruitdaily.com/2019/11/19/
a-supercon-was-had-arm-aiot-dev-summit-is-almost-here-and-more-python-
adafruit-circuitpython-pythonhardware-circuitpython-micropython-thepsf-adafruit/

"""

from adafruit_debouncer import Debouncer
import array
import math
import time
import audiobusio
import displayio
import board
import analogio

from micropython import const
import digitalio
import audioio
from gamepadshift import GamePadShift
import neopixel
from adafruit_display_shapes.rect import Rect
from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font
import terminalio
import adafruit_lis3dh

""" Model View Controller Architecture 
    The Model and View are in classes.
    The Controller is the initialization and run loop.


    Hardware model classes:
        sensorChannel has the shared code for:
          - Processing a signal
          - Assigning actions to the buttons.
          
        Each sensor inherits the sensorChannel class. 
        The sensor-specific classes:
          - Interfaces to the hardware
          - Scales the output data
          - Has a take_sweep() function to take a trace full of data.

"""
        
class sensorChannel(object):
    def __init__(self, button):
        
        self.button = button
        
        self.vertical_offset = 64
        self.num_samples_per_px = 2
        self.num_samples = 1000
        self.vertical_gain = 5
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
        nsamp = (1 + self.num_samples_per_px) * (x_right - x_left + 1) \
                + self.start_sample
        if nsamp <= self.max_num_samples:
            self.num_samples = nsamp
        elif nsamp >= self.min_num_samples:
            self.num_samples = nsamp
        else:
            self.num_samples = self.max_num_samples

    def buttons(self):
        self.button.scan()
        if self.button.a:
            self.increase_gain()
        if self.button.b:
            self.decrease_gain()
        if self.button.down:
            self.increase_offset()
        if self.button.up:
            self.decrease_offset()
        if self.button.left:
            self.increase_samples()        
        if self.button.right:
            self.decrease_samples()
        if self.button.start:
            self.preset()
            
class micChannel(sensorChannel):
    """ Class to use the light sensor as a data channel. """
    
    def __init__(self, board, button, samples):
        super().__init__(button)
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
        
    def __init__(self, board, button, samples):
        super().__init__(button)
        self.samples = samples
        self.board = board
        self.light_sensor = analogio.AnalogIn(board.A7)
        
    def preset(self):
        super().preset()
        self.vertical_gain = 8
        self.vertical_offset = 0
        
    def take_sweep(self):
        """ Take a sweep of light samples."""
           
        for a in range(self.num_samples):
            self.samples[a] = self.light_sensor.value
                
class sawtoothChannel(sensorChannel):
    """ Class to use a generated sawtooth waveform as a data channel. """
        
    def __init__(self, board, button, samples):
        super().__init__(button)
        self.samples = samples
        self.board = board
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

class accelerometerChannel(sensorChannel):
    """ Class to use the accelerometer as a data channel. """
    
    def __init__(self, board, button, samples):
        super().__init__(button)
        self.samples = samples
        self.board = board

        try:
            i2c = board.I2C()
        except RuntimeError:
            self.accelerometer = None

        if i2c is not None:
            int1 = digitalio.DigitalInOut(board.ACCELEROMETER_INTERRUPT)
            try:
                self.accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19, int1=int1)
            except ValueError:
                self.accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, int1=int1)       
        
    def preset(self):
        super().preset()
        
    def take_sweep(self):
        """ Take a sweep of accelerometer measurements."""
        
        """ Question: what is best lightweight algorithm to make 
        a swept graph of acceleration interesting? 
        Right now it is using the sum of the accelerations in x, y, and z."""
        
        # Scale the readings to look like ADC readings.

        for a in range(0, self.num_samples, 2):
            accel_reading = self.accelerometer.acceleration
            accel = int(round(accel_reading.x + accel_reading.y + accel_reading.z) * 25.0) + 32768
            self.samples[a] = accel
            
        # The accelerometer is slow. Interpolate between readings to make it sweep faster.
        for a in range(1, self.num_samples, 2):
            self.samples[a] = (self.samples[a-1] + self.samples[a+1]) >> 1

class Button:
    """Class to read Buttons on AdaFruit EDGE Badge."""
    
    """
    TODO:
    Need to debounce all the buttons in here, and also detect chords.
    Chords can be captured as maximum value during press.
    Instead of sleeping, should set a flag meaning 'button(s) are down'
    And then another flag when they are all stable and up.
    Use timestamps instead of delays so maybe things can continue
    to happen. This requires some sort of threading or interrupts? 
    Or maybe it spins inside here?
    
    Would like to have a button interrupt, especially for start/preset()
    Need a debounce button method for all buttons

    """
    
    # Button Constants
    BUTTON_LEFT = const(128)
    BUTTON_UP = const(64)
    BUTTON_DOWN = const(32)
    BUTTON_RIGHT = const(16)
    BUTTON_SELECT = const(8)
    BUTTON_START = const(4)
    BUTTON_A = const(2)
    BUTTON_B = const(1)

    def __init__(self, lights=None, i2c=None):
        # Buttons
        self._buttons = GamePadShift(digitalio.DigitalInOut(board.BUTTON_CLOCK),
                                     digitalio.DigitalInOut(board.BUTTON_OUT),
                                     digitalio.DigitalInOut(board.BUTTON_LATCH))
        self.button_values = self._buttons.get_pressed()
        self.lights = lights
        
    def scan(self):
        self.button_values = self._buttons.get_pressed()        

    @property
    def left(self):
        return self.button_values & BUTTON_LEFT
        
    @property
    def up(self):
        return self.button_values & BUTTON_UP
        
    @property
    def down(self):
        return self.button_values & BUTTON_DOWN
        
    @property
    def right(self):
        return self.button_values & BUTTON_RIGHT
        
    @property
    def select(self):
        return self.button_values & BUTTON_SELECT
        
    @property
    def start(self):
        return self.button_values & BUTTON_START
        
    @property
    def a(self):
        return self.button_values & BUTTON_A
        
    @property
    def b(self):
        return self.button_values & BUTTON_B
    
    def set_light_color(self, color_attr):
        if self.lights is not None:
            lights.pixels[2] = getattr(self.lights, color_attr)
            
    def debounce_select(self):
        pressed = False
        if self.select:
            pressed = True
            lights.pixels[2] = lights.pale_green
            while self.select:
                self.set_light_color('pale_blue')
                time.sleep(0.05)
                self.scan()
        else:
            lights.pixels[2] = lights.black  
        return pressed


""" View """

class DisplayView(object):
    global x_left
    global x_right
    global y_bottom
    global y_top
    
    def __init__(self, display):
        # To synchronize the display update to the waveform update,
        # turn off automatic display refresh.
        # Explicit refresh functions update the display.
        # The display refresh feature requires CircuitPython v5.0.0 or later.
        
        self.display = display
        display.auto_refresh = False
         
        # Create a bitmap with colors
        ncolors = 3
        self.bitmap = displayio.Bitmap(self.display.width, self.display.height, ncolors)
         
        # Create a color palette
        palette = displayio.Palette(ncolors)
        palette[0] = 0x000000
        palette[1] = 0x00ff00
        palette[2] = 0xaaaaaa
         
        # Create a TileGrid using the Bitmap and Palette
        tile_grid = displayio.TileGrid(self.bitmap, pixel_shader=palette)
         
        # Create a Group
        group = displayio.Group()
         
        # Add the TileGrid to the Group
        group.append(tile_grid)
         
        # Add the Group to the Display
        self.display.show(group)
         
        # The display width is 160 and the height is 128
        #   Positive y is down
        #   Positive x is right
        
        # Define the bounds of the graph
        x_left = 10
        x_right = 140
        y_bottom = 114
        y_top = 14
        
        # Define the bounds of the annotation
        y_annot_top = 5
        y_annot_bottom = 123
        
        # Draw a frame around the graph
        for px in range(x_left-1, x_right+1):
            self.bitmap[px, y_top-1] = 2
            self.bitmap[px, y_bottom+1] = 2
        for py in range(y_top-1, y_bottom+1):
            self.bitmap[x_left-1, py] = 2
            self.bitmap[x_right+1, py] = 2
        
        # Draw labels to annotate the display
        self.st_label = Label(terminalio.FONT, text='*', max_glyphs=30)
        self.st_label.x = x_left
        self.st_label.y = y_annot_top
        self.st_label.color = palette[1]
        group.append(self.st_label)
        
        self.dt_label = Label(terminalio.FONT, text='LIGHT', max_glyphs=30)
        self.dt_label.x = x_right - self.dt_label.bounding_box[2]
        self.dt_label.y = y_annot_top
        self.dt_label.color = palette[1]
        group.append(self.dt_label)
        
        self.status_label = Label(terminalio.FONT, text='EDGEMICSCOPE', max_glyphs=30)
        self.status_label.x = x_left
        self.status_label.y = y_annot_bottom
        self.status_label.color = palette[1]
        group.append(self.status_label)        

    def draw_trace(self, color_idx, channel):
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
            self.bitmap[x, y] = color_idx
            if horizontal_counter == 0:
                x += 1
                horizontal_counter = channel.num_samples_per_px
            else:
                horizontal_counter -= 1
            sample_index += 1



class LedView(object):
    """Class to operate the NeoPixels"""
    
    import neopixel
    
    PIXEL_SWEEP = const(0)
    PIXEL_SELECT = const(2)
    PIXEL_REFRESH = const(4)

    
    def __init__(self, leds):
        """ Neopixel initialization """
        
        neopixel_count = 5
        self.pixels = neopixel.NeoPixel(leds, neopixel_count,
                                            pixel_order=neopixel.GRB)
        self.pale_green = [0,1,0]
        self.pale_blue = [0,0,1]
        self.black = [0,0,0]
        self.sweep_led = 0
        self.refresh_led = 4
        
    def set_light_color(self, pixel_idx, color_attr):
        """ Set one neopixel to a predefined color. """
        if self.pixels is not None:
            color = getattr(self, color_attr)
            if color is not None:  
                 self.pixels[pixel_idx] = color

""" Controller """

x_left = 10
x_right = 140
y_bottom = 114
y_top = 14

screen = DisplayView(board.DISPLAY)
lights = LedView(board.NEOPIXEL)

# Allocate memory to store up to 0.5 seconds of audio
samples1 = array.array('H', [0] * 8000)

button = Button(lights)
    
mic_channel = micChannel(board, button, samples1)
mic_channel.preset()

light_channel = lightChannel(board, button, samples1)
light_channel.preset()

sawtooth_channel = sawtoothChannel(board, button, samples1)
sawtooth_channel.preset()

accelerometer_channel = accelerometerChannel(board, button, samples1)
accelerometer_channel.preset()

screen.display.refresh(minimum_frames_per_second=0)

channel = light_channel
vertical_input = 1

while(True):
    
    # Check the buttons for the channel
    channel.buttons()
    if channel.button.debounce_select():
        vertical_input += 1
        if vertical_input > 3:
            vertical_input = 0  
        
        if vertical_input == 0:
            channel = mic_channel
            screen.dt_label.text = 'MIC'
            screen.dt_label.x = x_right - screen.dt_label.bounding_box[2]
            screen.st_label.text = 'ST: *ms'
        elif vertical_input == 1:
            channel = light_channel
            screen.dt_label.text = 'LIGHT'
            screen.dt_label.x = x_right - screen.dt_label.bounding_box[2]
        elif vertical_input == 2:
            channel = sawtooth_channel
            screen.dt_label.text = 'SAWTOOTH'
            screen.dt_label.x = x_right - screen.dt_label.bounding_box[2]
        else:
            channel = accelerometer_channel
            screen.dt_label.text = 'ACCEL'
            screen.dt_label.x = x_right - screen.dt_label.bounding_box[2]
        
    # Turn the sweep LED on while taking samples
    lights.set_light_color(LedView.PIXEL_SWEEP, 'pale_green')
    start_time = time.monotonic_ns()
    
    channel.take_sweep()
    
    sweep_time = (time.monotonic_ns() - start_time)/1000000.0
    screen.st_label.text = 'ST: ' + str(round(sweep_time)) + 'ms'
    lights.set_light_color(LedView.PIXEL_SWEEP, 'black')

    # During the display update, light the refresh LED.
    lights.set_light_color(LedView.PIXEL_REFRESH, 'pale_blue')
    
    # Draw the waveform to pixels on the display.
    screen.draw_trace(1, channel)
    
    # Refresh the display. Repeat the call until it completes.
    while not screen.display.refresh(minimum_frames_per_second=0):
        pass
        
    # Erase the waveform by redrawing the pixels with black.
    screen.draw_trace(0, channel)
    lights.set_light_color(LedView.PIXEL_REFRESH, 'black')
    
    