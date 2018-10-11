
from pygame import display, HWSURFACE, DOUBLEBUF, Color, draw


class Screen(object):
    
    # Possible screen sizes
    SCREEN_HEIGHT_NORMAL = 32
    SCREEN_HEIGHT_EXTENDED = 64

    SCREEN_WIDTH_NORMAL = 64
    SCREEN_WIDTH_EXTENDED = 128

    COLOR_DEPTH = 8

    PIXEL_OFF = Color(0, 0, 0, 255)
    PIXEL_ON = Color(255, 255, 255, 255)

    def __init__(self, SCALE=1, HEIGHT=SCREEN_HEIGHT_NORMAL, WIDTH=SCREEN_WIDTH_NORMAL):
        
        # Setting the screen class height, width, and scale
        self.HEIGHT = HEIGHT
        self.WIDTH = WIDTH
        self.SCALE = SCALE

        #  Initialize a variable to hold the surface but don't use it
        self.SURFACE = None

        # Initialize the screen
        self.INITIALIZE()

    def INITIALIZE(self):
        
        # Initialize the display from pygame
        display.init()

        # Set the surface
        self.SURFACE = display.set_mode(((self.WIDTH * self.SCALE), (self.HEIGHT * self.SCALE)), HWSURFACE | DOUBLEBUF, self.COLOR_DEPTH)
        
        # Setting the title of the display
        display.set_caption('CHIP-8 Emulator')

        # Clear the display, run update on it
        self.CLEAR()
        self.UPDATE()
        self.CLEAR()    

    def DRAW(self, x, y, state):
        
        # Setting pixel coordinates
        x_origin = x * self.SCALE
        y_origin = y * self.SCALE

        # Whether to turn pixel on or off
        if state == 0:
            draw.rect(self.SURFACE, self.PIXEL_OFF, (x_origin, y_origin, self.SCALE, self.SCALE))
        elif state == 1:
            draw.rect(self.SURFACE, self.PIXEL_ON, (x_origin, y_origin, self.SCALE, self.SCALE))

    def GET_STATE(self, x, y):
        
        # Checking if pixel is on or off
        # Getting scaled coordinates
        x_scaled = x * self.SCALE
        y_scaled = y * self.SCALE

        # Checking state
        STATE = self.SURFACE.get_at((x_scaled, y_scaled))
        if STATE == self.PIXEL_OFF:
            return 0
        else:
            return 1

    def CLEAR(self):
        """
        Sets the entire screen to black (PIXEL_OFF)
        """
        self.SURFACE.fill(self.PIXEL_OFF)

    def UPDATE(self):
        display.flip()

    def GET_WIDTH(self):
        return self.WIDTH

    def GET_HEIGHT(self):
        return self.HEIGHT

    @staticmethod
    def DECONSTRUCTOR():
        """
        Destroys the current screen object.
        """
        display.quit()

    def SET_EXT(self):
        """
        Sets the screen mode to extended.
        """
        self.DECONSTRUCTOR()
        self.HEIGHT = self.SCREEN_HEIGHT_EXTENDED
        self.WIDTH = self.SCREEN_WIDTH_EXTENDED
        self.INITIALIZE()

    def SET_NORM(self):
        """
        Sets the screen mode to normal.
        """
        self.DECONSTRUCTOR()
        self.HEIGHT = self.SCREEN_HEIGHT_NORMAL
        self.WIDTH = self.SCREEN_WIDTH_NORMAL
        self.INITIALIZE()

    def SCROLL_DOWN(self, num_lines):

        # Scrolling lines down by grabbing previous row and copying it
        range_flip = self.HEIGHT - num_lines
        for y in reversed(range(range_flip)):
            for x in range(self.WIDTH):
                STATE = self.GET_STATE(x, y)
                self.DRAW(x, y + num_lines, STATE)

        # Blank out the lines above the ones we scrolled
        for y in range(num_lines):
            for x in range(self.WIDTH):
                self.DRAW(x, y, 0)

        self.UPDATE()

    def SCROLL_LEFT(self):

        #  Scroll lines left by 4 pixels (hard coded)
        for y in range(self.HEIGHT):
            for x in range(4, self.WIDTH):
                STATE = self.GET_STATE(x, y)
                self.DRAW(x - 4, y, STATE)

        # Blank out the lines to the right of the ones we just scrolled
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH - 4, self.WIDTH):
                self.DRAW(x, y, 0)

        self.UPDATE()

    def SCROLL_RIGHT(self):

        # Scroll lines right by 4 pixels (hard coded)
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH - 4, -1, -1):
                STATE = self.GET_STATE(x, y)
                self.DRAW(x + 4, y, STATE)

        # Blank out the lines to the left of the ones we just scrolled
        for y in range(self.HEIGHT):
            for x in range(4):
                self.DRAW(x, y, 0)

        self.UPDATE()