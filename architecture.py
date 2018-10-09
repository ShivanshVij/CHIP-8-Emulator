from exceptions import UnknownOpCodeException
from keychecker import KEY_MAPPINGS

from pygame import key

class architecture:
    # Constants:
    MAX_MEMORY = 4096

    def __init__(self):

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
            'RPL': bytearray(self.MAX_MEMORY)
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
            0x4: self.SKIP_REG_NE_VAL,             # 4SNN - SKNE VS, NN        (SKIP IF VS != NN)
            0x5: self.SKIP_REG_E_REG,              # 5ST0 - SKE  VS, VT        (SKIP IF VS == VT)
            0x6: self.LD_VAL_REG,                  # 6SNN - LOAD VS, NN        (LOAD NN INTO VS)
            0x7: self.ADD_VAL_REG,                 # 7SNN - ADD  VS, NN        (ADD NN TO VS)
            0x8: self.ELI,                         # SUBFUNCTION DEFINED BELOW (Execute Logical Instruction)
            0x9: self.SKIP_REG_NE_REG,             # 9ST0 - SKNE VS, VT        (SKIP IF VS != VT)
            0xA: self.LD_I_VAL,                    # ANNN - LOAD I, NNN        (LOAD NNN INTO I)
            0xB: self.JMP_I_VAL,                   # BNNN - JUMP [I] + NNN     (JUMP TO [I] + NNN)
            0xC: self.RND_REG,                     # CTNN - RAND VT, NN        (LOAD RANDOM NUMBER INTO VT WITH SEED NN)
            0xD: self.DRAW,                        # DSTN - DRAW VS, VT, N     (DRAW INTO VS, VT VALUE N)
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
            0x7: self.CLR_REG,                     # 8ST7 - SUBN VT, VT   (VS = VT - VS)
            0xE: self.L_SFT_REG,                   # 8SNE - SHL  VS       ( LEFT SHIFT VS)
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
            0x75: self.STR_REG_RPL,                 # FS75 - SRPL VS        (STORE VS INTO RPL)
            0x85: self.LD_REG_RPS,                  # FS85 - LRPL VS        (LOAD VS FROM RPL)
        }

        # Settings the current operand 
        self.CurrentOperand = 0

        # TODO: Create a screen class
        self.screen = None

        # TODO: Create a reset function
        self.reset()

    def EXECUTE(SELF, OPERAND=None):
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
            if ALL_PRESSED_KEYS[KEY_MAPPINGS[KEY_TO_CHECK]]:
                self.CpuRegisters['PC'] += 2

        # Skip if the key specified in the source register is not pressed
        if OPERATION == 0xA1:
            if not ALL_PRESSED_KEYS[KEY_MAPPINGS[KEY_TO_CHECK]]:
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

        if SUB_OPERATION == 0x00E0:
            SCROLL_PIXELS = self.CurrentOperand & 0x000F
            self.sceen.scroll_down(SCROLL_PIXELS)

        if OPERATION == 0x00E0:
            self.screen.clear_screen()

        if OPERATION == 0x00EE:
            self.RETURN()

        if OPERATION == 0x00FB:
            self.screen.scroll_right()

        if OPERATION == 0x00FC:
            self.screen.scroll_left()

        if OPERATION == 0x00FD:
            pass

        if OPERATION == 0x00FE:
            self.disable_extended_mode()

        if operation == 0x00FF:
            self.enable_extended_mode()

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

