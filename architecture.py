from exceptions import UnknownOpCodeException
from keyboard import KEY_MAPPINGS
from screen import Screen

import pygame
from pygame import key
from random import randint

class Architecture:
    # Constants:
    MAX_MEMORY = 4096
    PROGRAM_COUNTER_START = 0x200
    STACK_POINTER_START = 0x52
    NORMAL = 'normal'
    EXTENDED = 'extended'

    def __init__(self, scale):

        # The CHIP-8 had 4k (4096 bytes) of memory
        self.memory = bytearray(self.MAX_MEMORY)

        # The CHIP-8 had a series of registers as follows:
        # 
        #   1 x 16-bit index register        (I)
        #   1 x 16-bit program counter       (PC)
        #   1 x 16-bit stack pointer         (SP)
        #   1 x 8-bit delay timer            (DT)
        #   1 x 8-bit sound timer            (ST)
        # 
        #   16 x 8-bit general registers     (V0 - VF)

        self.GeneralRegisters = {
            0x0: 0,
            0x1: 0,
            0x2: 0,
            0x3: 0,
            0x4: 0,
            0x5: 0,
            0x6: 0,
            0x7: 0,
            0x8: 0,
            0x9: 0,
            0xA: 0,
            0xB: 0,
            0xC: 0,
            0xD: 0,
            0xE: 0,
            0xF: 0,
        }

        self.CpuRegisters = {
            'I' : 0,
            'SP': 0,
            'PC': 0,
            'RPL': bytearray(16)
        }

        self.Timers = {
            'DT': 0,
            'ST': 0,
        }

        # The Operations function by looking at the most significant byte
        # (The first character after 0x), then the next 3 bytes are used to define
        # The parameters of the operation (so 0x1333 = JMP 333)
        self.OperationLookupTable = {
            0x0: self.SYS,                       # 0NNN - SYS  NNN             (CLEAR, RETURN)
            0x1: self.JMP_ADDR,                    # 1NNN - JUMP NNN           (JUMP TO ADDRESS)
            0x2: self.JMP_SBR,                     # 2NNN - CALL NNN           (JUMP TO SUBROUTINE)
            0x3: self.SKIP_REG_E_VAL,              # 3SNN - SKNE VS, NN        (SKIP IF VS == NN)
            0x4: self.SKIP_REG_NE_VAL,             # 4SNN - SKNE VS, NN        (SKIP IF VS != NN)
            0x5: self.SKIP_REG_E_REG,              # 5ST0 - SKE  VS, VT        (SKIP IF VS == VT)
            0x6: self.LD_VAL_REG,                  # 6SNN - LOAD VS, NN        (LOAD NN INTO VS)
            0x7: self.ADD_VAL_REG,                 # 7SNN - ADD  VS, NN        (ADD NN TO VS)
            0x8: self.ELI,                         # SUBFUNCTION DEFINED BELOW (Execute Logical Instruction)
            0x9: self.SKIP_REG_NE_REG,             # 9ST0 - SKNE VS, VT        (SKIP IF VS != VT)
            0xA: self.LD_I_VAL,                    # ANNN - LOAD I, NNN        (LOAD NNN INTO I)
            0xB: self.JMP_I_VAL,                   # BNNN - JUMP [I] + NNN     (JUMP TO [I] + NNN)
            0xC: self.RND_REG,                     # CTNN - RAND VT, NN        (LOAD RANDOM NUMBER INTO VT AFTER AND WITH NN)
            0xD: self.DRAW,                        # DSTN - DRAW VS, VT, N     (DRAW INTO VS, VT VALUE N USING SPRITE IN I)
            0xE: self.KBRD,                        # SUBFUNCTION DEFINED BELOW (Keyboard Routine)
            0xF: self.MSC,                         # SUBFUNCTION DEFINED BELOW (Miscellaneous Routine)
        }

        #  As defined above, self.ELI get called when 0x8NNN is loaded into the CPU
        #  The last byte is used to define the logical instruction
        self.ELILookup = {
            0x0: self.LD_REG_REG,                  # 8ST0 - LOAD VS, VT   (LOAD VT INTO VS)
            0x1: self.OR,                          # 8ST1 - OR   VS, VT   (LOGICAL 'OR' OF VS AND VT)
            0x2: self.AND,                         # 8ST2 - AND  VS, VT   (LOGICAL 'AND' OF VS AND VT)
            0x3: self.XOR,                         # 8ST3 - XOR  VS, VT   (LOGICAL 'XOR' OF VS AND VT)
            0x4: self.ADD_REG_REG,                 # 8ST4 - ADD  VS, VT   (ADD VT TO VS)
            0x5: self.SUB_REG_REG,                 # 8ST5 - SUB  VS, VT   (VS = VS - VT)
            0x6: self.R_SHFT_REG,                  # 8SN6 - SHR  VS       (RIGHT SHIFT VS)
            0x7: self.SUBN_REG_REG,                # 8ST7 - SUBN VT, VT   (VS = VT - VS)
            0xE: self.L_SHFT_REG,                  # 8SNE - SHL  VS       ( LEFT SHIFT VS)
        }

        #  As defined above, self.MSC get called when 0xFNNN is loaded into the CPU
        #  The last two bytes are used to define the logical instruction
        self.MSCLookup = {
            0x07: self.LD_DT_REG,                   # FT07 - LOAD VT, DT    (LOAD DT INTO VT)
            0x0A: self.WAIT_KEYPRESS,               # FT0A - KEYD VT        (WAIT FOR KEYPRESS, LOAD INTO VT)
            0x15: self.LD_REG_DT,                   # FS15 - LOAD DT, VS    (LOAD VS INTO DT)
            0x18: self.LD_REG_ST,                   # Fs18 - LOAD ST, VS    (LOAD VS INTO ST)
            0x1E: self.ADD_REG_I,                   # FS1E - ADD  I, VS     (ADD VS TO I)
            0x29: self.LD_I_REG,                    # FS29 - LOAD I, VS     (LOAD SPRITE IN VS ITNO I)
            0x30: self.LD_EXT_I_REG,                # FS30 - LOAD I, VS     (LOAD EXTENDED SPRITE IN VS INTO I)
            0x33: self.STR_BCD_MEM,                 # FS33 - BCD            (STORE BINARY CODED DECIMAL IN VS INTO MEMORY)
            0x55: self.STR_REG_MEM,                 # FS55 - STOR [I], VS   (STORE V0 to VX INTO MEMORY[I])
            0x65: self.LD_REG_MEM,                  # FS65 - LOAD VS, [I]   (LOAD V0 to VX FROM MEMORY[I])
            0x75: self.STR_REG_RPL,                 # FS75 - SRPL VS        (STORE V0 - VS INTO RPL)
            0x85: self.LD_REG_RPL,                  # FS85 - LRPL VS        (LOAD V0 - VS FROM RPL)
        }

        # Settings the current operand 
        self.CurrentOperand = 0

        # Create and initialize screen class
        self.screen = Screen(SCALE=scale)

        # Setting default operating mode
        self.MODE = self.NORMAL

        # Reset memory function
        self.RESET()

    def LOAD_ROMFILE(self, filename, offset=PROGRAM_COUNTER_START):
        """
        Load the ROM indicated by the filename into memory.
        """
        ROM = open(filename, 'rb').read()
        for index, value in enumerate(ROM):
            self.memory[offset + index] = value

    def EXECUTE(self, OPERAND=None):
        """
        Execute the current instruction from the OPERAND parameter
        or the value at self.memory([PC])
        """

        if OPERAND:
            self.CurrentOperand = OPERAND
        else:
            # Getting the byte at index [PC]
            # Shifting it 8 bits to the left to make it most significant
            # Adding the next byte to it for subinstructions
            # Increment the Program Counter [PC] by 2
            self.CurrentOperand = int(self.memory[self.CpuRegisters['PC']]) 
            self.CurrentOperand = self.CurrentOperand << 8                  
            self.CurrentOperand += int(self.memory[self.CpuRegisters['PC'] + 1])
            self.CpuRegisters['PC'] += 2

        # The operation index being formatted for the lookup table
        OPERATION = (self.CurrentOperand & 0xF000) >> 12
        
        # Run the correct operation
        self.OperationLookupTable[OPERATION]()

        # Return the operation we just ran
        return self.CurrentOperand

    def ELI(self):
        """
        Defining the ELI Operation from the Lookup Table
        """

        # Formatting operation for lookup table
        OPERATION = self.CurrentOperand & 0x000F

        try:
            self.ELILookup[OPERATION]()
        except KeyError:
            # If operation not found, throw exception
            raise UnknownOpCodeException(self.CurrentOperand)

    def KBRD(self):
        """
        Runs the correct keyboard routine based on CurrentOperand

        OPERANDS:
            ES9E - SKPR VS (IF KEY IN VS IS PRESSED, SKIP LINE)
            ESA1 - SKUP VS (IF KEY IN VS NOT PRESSED, SKIP LINE)
        """

        # Formatting operation for lookup table (get first 2 bytes)
        OPERATION = self.CurrentOperand & 0x00FF 
        
        # Getting Key Register from CurrentOperand (get second byte)
        KEY_REGISTER = (self.CurrentOperand & 0x0F00) >> 8

        KEY_TO_CHECK = self.GeneralRegisters[KEY_REGISTER]

        # Get array of all pressed keys
        ALL_PRESSED_KEYS = key.get_pressed()
        

        # Skip if the key specified in the source register is pressed
        if OPERATION == 0x9E:
            if ALL_PRESSED_KEYS[int(KEY_MAPPINGS[KEY_TO_CHECK])] == 1:
                self.CpuRegisters['PC'] += 2

        # Skip if the key specified in the source register is not pressed
        if OPERATION == 0xA1:
            if ALL_PRESSED_KEYS[int(KEY_MAPPINGS[KEY_TO_CHECK])] == 0:
                self.CpuRegisters['PC'] += 2

    def MSC(self):
        """
        Will execute the subroutines defined in self.MSCLookup
        """

        # Formatting operation for lookup table
        OPERATION = self.CurrentOperand & 0x00FF

        try:
            self.MSCLookup[OPERATION]()
        except KeyError:
            # If operation not found, throw exception
            raise UnknownOpCodeException(self.CurrentOperand)

    def SYS(self):
        """
        These are System OP Codes, no point in having a lookup table for these since they only operate on the screen

        Opcodes starting with a 0 are one of the following instructions:
            0NNN - Jump to machine code function (ignored)
            00CN - Scroll n pixels down
            00E0 - Clear the display
            00EE - Return from subroutine
            00FB - Scroll 4 pixels right
            00FC - Scroll 4 pixels left
            00FD - Exit
            00FE - Disable extended mode
            00FF - Enable extended mode
        """

        # Formatting operation and sub_operation for conditional statements
        OPERATION = self.CurrentOperand & 0x00FF
        SUB_OPERATION = OPERATION & 0x00F0

        if SUB_OPERATION == 0x00C0:
            SCROLL_PIXELS = self.CurrentOperand & 0x000F
            self.screen.SCROLL_DOWN(SCROLL_PIXELS)

        if OPERATION == 0x00E0:
            self.screen.CLEAR()

        if OPERATION == 0x00EE:
            self.RETURN()

        if OPERATION == 0x00FB:
            self.screen.SCROLL_RIGHT()

        if OPERATION == 0x00FC:
            self.screen.SCROLL_LEFT()

        if OPERATION == 0x00FD:
            pass

        if OPERATION == 0x00FE:
            self.DISABLE_EXT()

        if OPERATION == 0x00FF:
            self.ENABLE_EXT()

    def RETURN(self):
        """
        Called by 00EE instruction

        Return from subroutine. Pop the current value in the stack pointer
        off of the stack, and set the program counter to the value popped.
        """
        self.CpuRegisters['SP'] -= 1
        self.CpuRegisters['PC'] = self.memory[self.CpuRegisters['SP']] << 8
        self.CpuRegisters['SP'] -= 1
        self.CpuRegisters['PC'] += self.memory[self.CpuRegisters['SP']]

    def JMP_ADDR(self):
        """
        Jump instruction to address

        0x1NNN = JUMP TO NNN
        """

        self.CpuRegisters['PC'] = self.CurrentOperand & 0x0FFF

    def JMP_SBR(self):
        """
        Jump instruction to subroutine. Save the current program counter on the stack,
        then take the CurrentOperand and pull out the last 3 bytes for the 

        0x2NNN - CALL NNN Subroutine
        """

        self.memory[self.CpuRegisters['SP']] = self.CpuRegisters['PC'] & 0x00FF
        self.CpuRegisters['SP'] += 1
        self.memory[self.CpuRegisters['SP']] = (self.CpuRegisters['PC'] & 0xFF00) >> 8
        self.CpuRegisters['SP'] += 1
        self.CpuRegisters['PC'] = self.CurrentOperand & 0x0FFF

    def SKIP_REG_E_VAL(self):
        """
        Triggered by 0x3SNN = SKIP IF REGISTER VS == NN
        """

        # Pull value for register out
        register = (self.CurrentOperand & 0x0F00) >> 8

        if self.GeneralRegisters[register] == self.CurrentOperand & 0x00FF:
            self.CpuRegisters['PC'] += 2

    def SKIP_REG_NE_VAL(self):
        """
        Triggered by 0x4SNN = SKIP IF REGISTER VS != NN
        """

        # Pull value for register out
        register = (self.CurrentOperand & 0x0F00) >> 8

        if self.GeneralRegisters[register] != self.CurrentOperand & 0x00FF:
            self.CpuRegisters['PC'] += 2

    def SKIP_REG_E_REG(self):
        """
        Triggered by 0x5ST0 = SKIP IF REGISTER VS == VT
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        if self.GeneralRegisters[register1] == self.GeneralRegisters[regsiter2]:
            self.CpuRegisters['PC'] += 2

    def SKIP_REG_NE_REG(self):
        """
        Triggered by 0x9ST0 = SKIP IF REGISTER VS != VT
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        if self.GeneralRegisters[register1] != self.GeneralRegisters[register2]:
            self.CpuRegisters['PC'] += 2

    def LD_VAL_REG(self):
        """
        Triggered by 0x6SNN = LOAD NN into VS
        """

        value = self.CurrentOperand & 0x00FF
        register = (self.CurrentOperand & 0x0F00) >> 8

        self.GeneralRegisters[register] = value

    def ADD_VAL_REG(self):
        """
        Triggered by 0x7SNN = VS = [VS] + NN
        We need to be careful of overflow as well
        """

        value = self.CurrentOperand & 0x00FF
        register = (self.CurrentOperand & 0x0F00) >> 8
        added_value = self.GeneralRegisters[register] + value
        self.GeneralRegisters[register] = added_value if added_value < 256 else added_value - 256

    def LD_REG_REG(self):
        """
        PART OF ELI: Triggered by 0x8ST0 = VS = [VT]
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4
        self.GeneralRegisters[register1] = self.GeneralRegisters[register2]

    def ADD_REG_REG(self):
        """
        PART OF ELI: Triggered by 0x8ST4 = VS = VS + [VT]
        If carry is generated, we need to set the carry flag in VF (hardcoded)
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        added_value = self.GeneralRegisters[register1] + self.GeneralRegisters[register2]

        if added_value > 255:
            self.GeneralRegisters[register1] = added_value - 256
            self.GeneralRegisters[0xF] = 1
        else:
            self.GeneralRegisters[register1] = added_value
            self.GeneralRegisters[0xF] = 0

    def SUB_REG_REG(self):
        """
        PART OF ELI: Triggered by 0x8ST5 = VS = [VS] - [VT]

        Need to set the carry flag in VF (hardcoded) if a borrow is not generated
        """
        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        if self.GeneralRegisters[register1] > self.GeneralRegisters[register2]:
            self.GeneralRegisters[register1] -= self.GeneralRegisters[register2]
            self.GeneralRegisters[0xF] = 1
        else:
            self.GeneralRegisters[register1] = 256 + self.GeneralRegisters[register1] - self.GeneralRegisters[register2]
            self.GeneralRegisters[0xF] = 0

    def SUBN_REG_REG(self):
        """
        PART OF ELI: Triggered by 0x8ST7 = VS = [VT] - [VS]

        Need to set the carry flag in VF (hardcoded) if a borrow is not generated
        """
        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        if self.GeneralRegisters[register1] < self.GeneralRegisters[register2]:
            self.GeneralRegisters[register1] = self.GeneralRegisters[register2] - self.GeneralRegisters[register1]
            self.GeneralRegisters[0xF] = 1
        else:
            self.GeneralRegisters[register1] = 256 + self.GeneralRegisters[register2] - self.GeneralRegisters[register1]
            self.GeneralRegisters[0xF] = 0

    def OR(self):
        """
        PART OF ELI: Triggered by 0x8ST1 = VS = VS | VT
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        self.GeneralRegisters[register1] |= self.GeneralRegisters[register2]

    def AND(self):
        """
        PART OF ELI: Triggered by 0x8ST2 = VS = VS & VT
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        self.GeneralRegisters[register1] &= self.GeneralRegisters[register2]

    def XOR(self):
        """
        PART OF ELI: Triggered by 0x8ST3 = VS = VS ^ VT
        """

        register1 = (self.CurrentOperand & 0x0F00) >> 8
        register2 = (self.CurrentOperand & 0x00F0) >> 4

        self.GeneralRegisters[register1] ^= self.GeneralRegisters[register2]

    def R_SHFT_REG(self):
        """
        PART OF ELI: Triggered by 0x8S06 = VS = VS >> 1 and VF = VS[0] & 0x1 (bit 0 not byte 0)
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.GeneralRegisters[0xF] = self.GeneralRegisters[register] & 0x1
        self.GeneralRegisters[register] = self.GeneralRegisters[register] >> 1

    def L_SHFT_REG(self):
        """
        PART OF ELI: Triggered by 0x8S0E = VS = VS << 1 and VF = VS[7] & 0x80 (bit 7 not byte 7)
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.GeneralRegisters[0xF] = (self.GeneralRegisters[register] & 0x80) >> 8
        self.GeneralRegisters[register] = self.GeneralRegisters[register] << 1

    def LD_I_VAL(self):
        """
        Triggered by 0xANNN = LOAD NNN into I
        """

        self.CpuRegisters['I'] = self.CurrentOperand & 0x0FFF

    def JMP_I_VAL(self):
        """
        Triggered by 0xBNNN = JUMP to [I] + NNN
        """

        self.CpuRegisters['PC'] = self.CpuRegisters['I'] + (self.CurrentOperand & 0x0FFF)
    
    def RND_REG(self):
        """
        Triggered by 0xCSNN = Generate a random number, AND it with NN and save in VS
        Random number must be between 0 and 255
        """

        value = self.CurrentOperand & 0x00FF
        register = (self.CurrentOperand & 0x0F00) >> 8

        self.GeneralRegisters[register] = value & randint(0, 255)

    def LD_DT_REG(self):
        """
        PART OF MSC - Triggered by 0xFS07 = LOAD DT INTO VT
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.GeneralRegisters[register] = self.Timers['DT']

    def WAIT_KEYPRESS(self):
        """
        PART OF MSC - Triggerd by 0xFS0A = WAIT FOR KEYPRESS, STORE KEYPRESS INTO VS
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        key_pressed = False
        while not key_pressed:
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                all_keys_down = key.get_pressed()
                if all_keys_down[pygame.K_q]:
                    self.CurrentOperand = 0x00FD
                    key_pressed = True
                    break
                for keyval, lookup_key in KEY_MAPPINGS.items():
                    if all_keys_down[lookup_key]:
                        self.GeneralRegisters[register] = keyval
                        key_pressed = True
                        break
    
    def LD_REG_DT(self):
        """
        PART OF MSC - Triggered by 0xFS15 = LOAD VS INTO DT
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.Timers['DT'] = self.GeneralRegisters[register]

    def LD_REG_ST(self):
        """
        PART OF MSC - Triggered by 0xFS18 = LOAD VS INTO ST
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.Timers['ST'] = self.GeneralRegisters[register]

    def LD_I_REG(self):
        """
        PART OF MSC - Triggered by 0xFS29 = LOAD VS INTO I
        We multiply by 5 to shift the register value into a SPRITE CODE
        All Sprite codes are 5 bytes long, so the location of the sprite is index*5
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.CpuRegisters['I'] = self.GeneralRegisters[register] * 5

    def LD_EXT_I_REG(self):
        """
        PART OF MSC - Triggered by 0xFS30 = LOAD VS INTO I
        We multiply by 10 to shift the register value into a SPRITE CODE
        All Sprite codes are 10 bytes long, so the location of the sprite is index*10
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.CpuRegisters['I'] = self.GeneralRegisters[register] * 10

    def ADD_REG_I(self):
        """
        PART OF MSC - Triggered by 0xFT1E = I = [VT] + [I]
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        self.CpuRegisters['I'] += self.GeneralRegisters[register]

    def STR_BCD_MEM(self):
        """
        PART OF MSC - Triggered by 0xFT33 = TAKE Value in VT and place as follow into memory:
        
            N*10^2 = self.memory[i]
            N*10^1 = self.memory[i+1]
            N*10^0 = self.memory[i+2]

        """

        register = (self.CurrentOperand & 0x0F00) >> 8
        binary_value = '{:03d}'.format(self.GeneralRegisters[register])

        self.memory[self.CpuRegisters['I']] = int(binary_value[0])
        self.memory[self.CpuRegisters['I'] + 1] = int(binary_value[1])
        self.memory[self.CpuRegisters['I'] + 2] = int(binary_value[2])

    def STR_REG_MEM(self):
        """
        PART OF MSC - Triggered by 0xFT55 = STORE V0-VT INTO MEMORY AT [I] 
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        for i in range(register + 1):
            self.memory[self.CpuRegisters['I'] + i] = self.GeneralRegisters[i]

    def LD_REG_MEM(self):
        """
        PART OF MSC - Triggered by 0xFST65 = LOAD V0-VT FROM MEMORY AT [I]
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        for i in range(register + 1):
            self.GeneralRegisters[i] = self.memory[self.CpuRegisters['I'] + i]

    def STR_REG_RPL(self):
        """
        PART OF MSC - Triggered by 0xFT75 = STORE V0 - VT INTO RPL
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        for i in range(register + 1):
            self.CpuRegisters['RPL'][i] = self.GeneralRegisters[i]

    def LD_REG_RPL(self):
        """
        PART OF MSC - Triggered by 0xFT85 = LOAD V0 - VT FROM RPL
        """

        register = (self.CurrentOperand & 0x0F00) >> 8

        for i in range(register + 1):
            self.GeneralRegisters[i] = self.CpuRegisters['RPL'][i]

    def DRAW(self):
        """
        The draw method for actually drawing output to the screen
        Triggered by DSTN - DRAW VS, VT, N

        Works by checking what sprite is saved in the index register ([I])
        at the x and y coordinates, where x = [VS], = [VT].

        The drawing works by XORing the individual pixels and wrapping if we go off page
        The N value is used to define the height of the sprite and the width is 
        hardcoded to be 8-bits

        Since the index register points to memory, say the memory looks like this:

        self.memory[0]:     0 1 1 1 1 1 0 0
        self.memory[1]:     0 1 0 0 0 0 0 0
        self.memory[2]:     0 1 0 0 0 0 0 0
        self.memory[3]:     0 1 1 1 1 1 0 0
        self.memory[4]:     0 1 0 0 0 0 0 0
        self.memory[5]:     0 1 0 0 0 0 0 0
        self.memory[6]:     0 1 1 1 1 1 0 0

        where the 1's form the shape of an E, then having the index point to self.memory[0
        and N as 7 would tell the emulator to draw the E by iterating from 0-6 in the memory
        """

        register_x = (self.CurrentOperand & 0x0F00) >> 8
        register_y = (self.CurrentOperand & 0x00F0) >> 4

        x = self.GeneralRegisters[register_x]
        y = self.GeneralRegisters[register_y]

        height = self.CurrentOperand & 0x000F

        self.GeneralRegisters[0xF] = 0

        if self.MODE == self.EXTENDED and height == 0:
            self.DRAW_EXT(x, y, 16)
        else:
            self.DRAW_NORM(x, y, height)

    def DRAW_NORM(self, x, y, height):
        """
        Called by draw function in normal mode
        """

        for y_layer in range(height):

            pixel_array = bin(self.memory[self.CpuRegisters['I'] + y_layer])
            pixel_array = pixel_array[2:].zfill(8)

            y_coordinate = (y + y_layer) % self.screen.HEIGHT

            for x_layer in range(8):

                x_coordinate = (x + x_layer) % self.screen.WIDTH
                new_state = int(pixel_array[x_layer])

                current_state = self.screen.GET_STATE(x_coordinate, y_coordinate)

                if current_state == 1 and new_state == 1:
                    self.GeneralRegisters[0xF] = self.GeneralRegisters[0xF] | 1
                    new_state = 0
                elif new_state == 0 and current_state == 1:
                    self.GeneralRegisters[0xF] = self.GeneralRegisters[0xF] | 0
                    new_state = 1

                self.screen.DRAW(x_coordinate, y_coordinate, new_state)

        self.screen.UPDATE()

    def DRAW_EXT(self,x, y, height):
        """
        Called by draw function in extended mode where sprites are 
        supposed to be 16 x 16
        """

        for y_layer in range(height):

            for offset in range(2):

                pixel_array = bin(self.memory[self.CpuRegisters['I'] + (y_layer*2) + offset])
                pixel_array = pixel_array[2:].zfill(8)

                y_coordinate = (y + y_layer) % self.screen.HEIGHT

                for x_layer in range(8):

                    x_coordinate = (x + x_layer + (offset * 8)) % self.screen.WIDTH

                    new_state = int(pixel_array[x_layer])

                    current_state = self.screen.GET_STATE(x_coordinate, y_coordinate)

                    if current_state == 1 and new_state == 1:
                        self.GeneralRegisters[0xF] = self.GeneralRegisters[0xF] | 1
                        new_state = 0
                    elif new_state == 0 and current_state == 1:
                        new_state = 1

                    self.screen.DRAW(x_coordinate, y_coordinate, new_state)

        self.screen.UPDATE()

    def RESET(self):
        """
        Blanks out registers and resets the stack pointer and PC to initial values
        """
        for i in range(16):
            self.GeneralRegisters[i] = 0
            self.CpuRegisters['RPL'][i] = 0
        
        self.CpuRegisters['PC'] = self.PROGRAM_COUNTER_START
        self.CpuRegisters['SP'] = self.STACK_POINTER_START
        self.CpuRegisters['I'] = 0
        
        self.Timers['DT'] = 0
        self.Timers['ST'] = 0

    def ENABLE_EXT(self):
        """
        Enables extended mode
        """
        self.screen.SET_EXT()
        self.MODE = self.EXTENDED

    def DISABLE_EXT(self):
        """
        Disable extended mode
        """
        self.screen.SET_NORM()
        self.MODE = self.NORMAL
        
    # Debug functions
    def DECREMENT_TIMERS(self):
        """
        Decrement both the sound and delay timer.
        """
        if self.Timers['DT'] > 0:
            self.Timers['DT'] -= 1

        if self.Timers['ST'] > 0:
            self.Timers['ST'] -= 1

    def DUMP_MEMORY(self):
        """
        Print the current contents of the memory
        """
        i = 0
        for binary_line in self.memory:
            if binary_line != 0:
                print("Index: {}, value: {}".format(i, hex(binary_line)))
            i += 1
