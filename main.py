from architecture import Architecture

import pygame

class Emulator:

    TIMER = pygame.USEREVENT + 1

    # Delay timer decrement interval (in ms)
    DELAY_INTERVAL = 17

    def __init__(self, rom, scale=5, delay=5, font_file="FONTS.chip8"):
        self.ROM_FILE = rom
        self.FONT_FILE = font_file
        self.SCALE = scale
        self.DELAY = delay

        self.main()

    def main(self):
        CPU = Architecture(self.SCALE)

        CPU.LOAD_ROMFILE(self.FONT_FILE, 0)
        CPU.LOAD_ROMFILE(self.ROM_FILE)

        pygame.time.set_timer(self.TIMER, self.DELAY_INTERVAL)

        running = True

        while running:
            pygame.time.wait(self.DELAY)
            CurrentOperand = CPU.EXECUTE()

            # Check for various events
            for event in pygame.event.get():
                if event.type == self.TIMER:
                    CPU.DECREMENT_TIMERS()

                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    all_keys_down = pygame.key.get_pressed()
                    if all_keys_down[pygame.K_q]:
                        running = False

            if CurrentOperand == 0x00FD:
                running = False

    
if __name__ == '__main__':
    emulator = Emulator(rom='c8games\TETRIS', font_file='c8games\\FONTS.chip8', scale=15)