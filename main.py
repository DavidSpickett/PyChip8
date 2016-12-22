'''Python interpreter for Chip8 games. See main.py --help for usage.'''

import binascii
import random
import argparse
import pygame

DISPLAY_WDITH = 64
DISPLAY_HEIGHT = 32


def to_int(hbyte):
    '''
    Convert hex byte like "1F" to decimal.
    '''
    return int(hbyte, 16)


def check_keys():
    '''
    Check the keyboard and return a list of key states for the keys we're
    interested in.
    '''
    pygame.event.pump()
    keys = pygame.key.get_pressed()
    # Above are the keys used by the user, in the order the Chip 8 has them
    soft_keys = [pygame.K_x, pygame.K_1, pygame.K_2, pygame.K_3,
                 pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_a,
                 pygame.K_s, pygame.K_d, pygame.K_z, pygame.K_c,
                 pygame.K_4, pygame.K_r, pygame.K_f, pygame.K_v]
    return [keys[soft_key] for soft_key in soft_keys]


class OpCode(str):
    '''
    Like a string but allows '?' for wild card comparisons.
    e.g. 'abcd' == 'a?b?'.
    '''

    def __eq__(self, rhs):
        for lchar, rchar in zip(self, rhs):
            if rchar != '?' and lchar != rchar:
                return False
        return True


class ChipEightSystem(object):
    '''
    The Chip8 virtual machine.
    '''

    def __init__(self, rom_name, pixel_size, full_screen):
        self.pixel_size = pixel_size

        self.screen = pygame.display.set_mode(
            (DISPLAY_WDITH * args.pixel_size, DISPLAY_HEIGHT * args.pixel_size),
            pygame.FULLSCREEN if full_screen else 0)

        # Programs begin after the interpreter
        self.pc_reg = 0x200

        self.memory = []
        self.setup_memory(rom_name)

        # 16 General purpose 8 bit registers
        self.v_regs = [0] * 16

        # I, a 16 bit register (usually holds memory addresses)
        self.i_reg = 0

        # The stack, an array of 16, 16 bit values
        self.stack = [0] * 16
        # Stack pointer, 8 bit
        self.stack_pointer = 0

        # The Display which is 64x32, defined so we can write with x,y
        self.display = [([0] * DISPLAY_HEIGHT) for _ in range(DISPLAY_WDITH)]

        # Delay timer, an 8 bit register.
        self.delay_timer = 0

        # Sound timer, as for the delay timer
        self.sound_timer = 0

        # Colour used to for pixels
        self.colour = (255, 255, 255)

    def setup_memory(self, rom_name):
        '''
        Initialise the memory with font and ROM file data.
        '''

        font_data = [
            "F0", "90", "90", "90", "F0",  # Zero
            "20", "60", "20", "20", "70",  # One
            "F0", "10", "F0", "80", "F0",  # Two
            "F0", "10", "F0", "10", "F0",  # Three
            "90", "90", "F0", "10", "10",  # Four
            "F0", "80", "F0", "10", "F0",  # Five
            "F0", "80", "F0", "90", "F0",  # Six
            "F0", "10", "20", "40", "40",  # Seven
            "F0", "90", "F0", "90", "F0",  # Eight
            "F0", "90", "F0", "10", "F0",  # Nine
            "F0", "90", "F0", "90", "90",  # charA
            "E0", "90", "E0", "90", "E0",  # charB
            "F0", "80", "80", "80", "F0",  # charC
            "E0", "90", "90", "90", "E0",  # charD
            "F0", "80", "F0", "80", "F0",  # charE
            "F0", "80", "F0", "80", "80",  # charF
        ]

        self.memory.extend(font_data)

        # Fill up till 0x200
        self.memory.extend(["00"] * 432)

        # Load the rom and make a list of 1 byte hex codes
        with open(rom_name, 'rb') as rom_file:
            hex_str = binascii.hexlify(rom_file.read())

            # 2 hex chars = 1 byte
            chunk = 2
            # Pad to make sure we have whole bytes
            hex_str += ''.join(['0'] * (len(hex_str) % chunk))

            for index in range(0, len(hex_str), chunk):
                self.memory.append(hex_str[index:index + chunk])

        # Now pad the rest of the 4kb of virtual RAM
        self.memory.extend(["00"] * (4096 - len(self.memory)))

    def _update_display(self):
        '''
        Draws the data in self.display to the screen.
        '''

        # Clear the screen by filling with black
        self.screen.fill((0, 0, 0))

        for i in range(DISPLAY_WDITH):
            for j in range(DISPLAY_HEIGHT):
                if self.display[i][j]:
                    self.screen.fill(self.colour,
                                     (i * self.pixel_size, j * self.pixel_size,
                                      self.pixel_size, self.pixel_size))

    def do_next_opcode(self):
        '''
        Retrieve and process the next opcode.
        '''
        next_code = OpCode(
            self.memory[self.pc_reg] + self.memory[self.pc_reg + 1])

        # Retrieve the instruction where the program counter points to

        # Now look at next_code and see which instruction it is
        # http://devernay.free.fr/hacks/chip8/C8TECH10.HTM

        #00E0 - CLS
        # Clear the display.
        if next_code == "00e0":
            self.display = [
                [False] * DISPLAY_HEIGHT for j in range(DISPLAY_WDITH)]
            self.pc_reg += 2

        # 00EE - RET
        # Return from a subroutine.
        elif next_code == "00ee":
            self.pc_reg = self.stack[self.stack_pointer]
            self.stack_pointer -= 1
            self.pc_reg += 2

        # 00FD - QUIT
        # Quit emulator (schip8 instruction)
        elif next_code == "00fd":
            raise RuntimeError("Got QUIT instruction.")

        # 00FE - chip8 mode
        # Set the graphic mode to chip8
        elif next_code == "00fe":
            self.pc_reg += 2

        # OOFF - schip8 mode
        # Set the graphic mode to schip 8
        elif next_code == "00ff":
            self.pc_reg += 2

        # 0nnn - SYS addr
        # Jump to a machine code routine at nnn.
        elif next_code[0] == "0":
            self.pc_reg += 2

        # 1nnn - JP addr
        # Jump to location nnn.
        elif next_code == "1???":
            self.pc_reg = to_int(next_code[1:4])

        # 2nnn - CALL addr
        # Call subroutine at nnn.
        elif next_code == "2???":
            self.stack_pointer += 1
            # Save the current pc position
            self.stack[self.stack_pointer] = self.pc_reg
            # Set the PC to nnn
            self.pc_reg = to_int(next_code[1:4])

        # 3xkk - SE Vx, byte
        # Skip next instruction if Vx == kk.
        elif next_code == "3???":
            if self.v_regs[to_int(next_code[1])] == to_int(next_code[2:4]):
                # Move an extra 2, to skip an instruction
                self.pc_reg += 4
            else:
                self.pc_reg += 2

        # 4xkk - SNE Vx, byte
        # Skip next instruction if Vx != kk.
        elif next_code == "4???":
            if self.v_regs[to_int(next_code[1])] != to_int(next_code[2:4]):
                # Move an extra 2, to skip an instruction
                self.pc_reg += 4
            else:
                self.pc_reg += 2

        # 5xy0 - SE Vx, Vy
        # Skip next instruction if Vx == Vy.
        elif next_code == "5???":
            if self.v_regs[to_int(next_code[1])] == self.v_regs[to_int(next_code[2])]:
                # Move an extra 2, skipping the next instruction
                self.pc_reg += 4
            else:
                self.pc_reg += 2

        # 6xkk - LD Vx, byte
        # Set Vx = kk.
        elif next_code == "6???":
            self.v_regs[to_int(next_code[1])] = to_int(next_code[2:4])
            self.pc_reg += 2

        # 7xkk - ADD Vx, byte
        # Set Vx = Vx + kk.
        elif next_code == "7???":
            res = self.v_regs[to_int(next_code[1])] + to_int(next_code[2:4])
            self.v_regs[to_int(next_code[1])] = res

            # Now take the lowest 8 bits
            self.v_regs[to_int(next_code[1])] = self.v_regs[to_int(next_code[1])] & 255

            self.pc_reg += 2

        # 8xy0 - LD Vx, Vy
        # Set Vx = Vy.
        elif next_code == "8??0":
            self.v_regs[to_int(next_code[1])] = self.v_regs[to_int(next_code[2])]
            self.pc_reg += 2

        # 8xy1 - OR Vx, Vy
        # Set Vx = Vx OR Vy.
        elif next_code == "8??1":
            res = self.v_regs[to_int(next_code[1])] | self.v_regs[to_int(next_code[2])]
            self.v_regs[to_int(next_code[1])] = res
            self.pc_reg += 2

        # 8xy2 - AND Vx, Vy
        # Set Vx = Vx AND Vy.
        elif next_code == "8??2":
            res = self.v_regs[to_int(next_code[1])] & self.v_regs[to_int(next_code[2])]
            self.v_regs[to_int(next_code[1])] = res
            self.pc_reg += 2

        # 8xy3 - XOR Vx, Vy
        # Set Vx = Vx XOR Vy.
        elif next_code == "8??3":
            res = self.v_regs[to_int(next_code[1])] ^ self.v_regs[to_int(next_code[2])]
            self.v_regs[to_int(next_code[1])] = res
            self.pc_reg += 2

        # 8xy4 - ADD Vx, Vy
        # Set Vx = Vx + Vy, set VF = carry.
        elif next_code == "8??4":
            res = self.v_regs[to_int(next_code[1])] + self.v_regs[to_int(next_code[2])]
            self.v_regs[to_int(next_code[1])] = res
            # Add the two registers

            if sum > 255:
                self.v_regs[15] = 1  # Set VF (the carry)
                self.v_regs[to_int(next_code[1])] = self.v_regs[to_int(next_code[1])] & 255
                # Set Vx to the lower 8 bits of the result

            self.pc_reg += 2

        # 8xy5 - SUB Vx, Vy
        # Set Vx = Vx - Vy, set VF = NOT borrow.
        elif next_code == "8??5":
            # Set VF to 0, we'll check if it needs to be 1 next
            self.v_regs[15] = 0

            if self.v_regs[to_int(next_code[1])] > self.v_regs[to_int(next_code[2])]:
                self.v_regs[15] = 1  # Set VF to 1, because Vx > Vy

            res = self.v_regs[to_int(next_code[1])] - self.v_regs[to_int(next_code[2])]
            self.v_regs[to_int(next_code[1])] = res

            # if self.v_regs[to_int(next_code[1])] < 0: #Negative results
            #    self.v_regs[to_int(next_code[1])] *= -1

            # Not sure what happens to negative results (if Vy > Vx) so
            # I'm just going to store it and see what happens later on.

            self.pc_reg += 2

        # 8xy6 - SHR Vx {, Vy}
        # Set Vx = Vx SHR 1.
        elif next_code == "8??6":
            # Set VF to the LSB of the value
            self.v_regs[15] = int(to_int(next_code[1]) & 1)

            # Divide Vx by 2 by shifting right
            self.v_regs[to_int(next_code[1])] = self.v_regs[to_int(next_code[1])] >> 1

            self.pc_reg += 2

        # 8xy7 - SUBN Vx, Vy
        # Set Vx = Vy - Vx, set VF = NOT borrow.
        elif next_code == "8??7":
            # Set VF to 0, we'll check if it needs to be 1 next
            self.v_regs[15] = 0

            if self.v_regs[to_int(next_code[2])] > self.v_regs[to_int(next_code[1])]:
                self.v_regs[15] = 1  # Set VF to 1, because Vy > Vx

            res = self.v_regs[to_int(next_code[2])] - self.v_regs[to_int(next_code[1])]
            self.v_regs[to_int(next_code[1])] = res

            # if self.v_regs[to_int(next_code[1])] < 0: #Negative results
            #    self.v_regs[to_int(next_code[1])] *= -1

            # Not sure what happens to negative results (if Vx > Vy) so
            # I'm just going to store it and see what happens later on.

            self.pc_reg += 2

        # 8xyE - SHL Vx {, Vy}
        # Set Vx = Vx SHL 1.
        elif next_code == "8??e":
            # Check most significant bit (looking for a carry)
            if self.v_regs[to_int(next_code[1])] / 255 > 1:
                self.v_regs[15] = 1  # Set VF
            else:
                self.v_regs[15] = 0  # Set VF

            # Multiply Vx by 2 by shifting left
            self.v_regs[to_int(next_code[1])] = (
                self.v_regs[to_int(next_code[1])] << 1) & 255
            # Make sure we only store the lower 8 bits

            self.pc_reg += 2

        # 9xy0 - SNE Vx, Vy
        # Skip next instruction if Vx != Vy.
        elif next_code == "9???":
            if self.v_regs[to_int(next_code[1])] != self.v_regs[to_int(next_code[2])]:
                # 4 means Skipping one instruction
                self.pc_reg += 4
            else:
                self.pc_reg += 2

        # Annn - LD I, addr
        # Set I = nnn.
        elif next_code == "a???":
            self.i_reg = to_int(next_code[1] + next_code[2] + next_code[3])
            self.pc_reg += 2

        # Bnnn - JP V0, addr
        # Jump to location nnn + V0.
        elif next_code == "b???":
            self.pc_reg = to_int(next_code[1:4]) + self.v_regs[0]

        # Cxkk - RND Vx, byte
        # Set Vx = random byte AND kk.
        elif next_code == "c???":
            rnd = random.randint(0, 255)
            self.v_regs[to_int(next_code[1])] = rnd & to_int(next_code[2:4])
            self.pc_reg += 2

        # Dxyn - DRW Vx, Vy, nibble
        # Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.
        # This is done using an XOR function, so writing to an already set
        # pixel will erase it.
        elif next_code == "d???":
            x_pos = self.v_regs[to_int(next_code[1])]
            y_pos = self.v_regs[to_int(next_code[2])]
            length = to_int(next_code[3])

            # Memory adress of the sprite
            start = self.i_reg
            # Hold data to be written to screen
            data = []
            for byte in self.memory[start:start + length]:
                data.append(format(to_int(byte), '08b'))

            # Set to indicate no overwrites, set later if one occurs
            self.v_regs[15] = 0

            for i, sprite_row in enumerate(data):  # Rows of the sprite
                for j, pixel in enumerate(sprite_row):  # 0s and 1s in each row
                    new_x = x_pos + j
                    if new_x >= DISPLAY_WDITH:
                        new_x = new_x % DISPLAY_WDITH

                    new_y = y_pos
                    if new_y >= DISPLAY_HEIGHT:
                        new_y = new_y % DISPLAY_HEIGHT

                    if pixel == "1":
                        if self.display[new_x][new_y]:  # XOR means we overwrite a pixel
                            self.display[new_x][new_y] = 0
                            # Indiciate overwriting occured
                            self.v_regs[15] = 1
                        else:
                            self.display[new_x][new_y] = 1

                # Move down for next row
                y_pos += 1

            self.pc_reg += 2

            # Update screen
            self._update_display()
            pygame.display.flip()

        # Ex9E - SKP Vx
        # Skip next instruction if key with the value of Vx is pressed.
        elif next_code == "e?9e":
            if check_keys()[self.v_regs[to_int(next_code[1])]]:  # 1 means key is down
                self.pc_reg += 4  # Move an extra instruction along
            else:
                self.pc_reg += 2

        # ExA1 - SKNP Vx
        # Skip next instruction if key with the value of Vx is not pressed.
        elif next_code == "e?a1":
            if check_keys()[self.v_regs[to_int(next_code[1])]]:
                self.pc_reg += 2
            else:
                self.pc_reg += 4  # Move an extra instruction along

        # Fx07 - LD Vx, DT
        # Set Vx = delay timer value.
        elif next_code == "f?07":
            self.v_regs[to_int(next_code[1])] = self.delay_timer
            self.pc_reg += 2

        # Fx0A - LD Vx, K
        # Wait for a key press, store the value of the key in Vx.
        elif next_code == "f?0a":
            key_states = check_keys()
            while not any(key_states):
                key_states = check_keys()

            self.v_regs[to_int(next_code[1])] = key_states.index(True)
            self.pc_reg += 2

        # Fx15 - LD DT, Vx
        # Set delay timer = Vx.
        elif next_code == "f?15":
            self.delay_timer = self.v_regs[to_int(next_code[1])]
            self.pc_reg += 2

        # Fx18 - LD ST, Vx
        # Set sound timer = Vx.
        elif next_code == "f?18":
            self.sound_timer = self.v_regs[to_int(next_code[1])]
            self.pc_reg += 2

        # Fx1E - ADD I, Vx
        # Set I = I + Vx.
        elif next_code == "f?1e":
            self.i_reg += self.v_regs[to_int(next_code[1])]
            self.pc_reg += 2

        # Fx29 - LD F, Vx
        # Set I = location of sprite for digit Vx.
        elif next_code == "f?29":
            # Each char being 5 bytes long
            self.i_reg = self.v_regs[to_int(next_code[1])] * 5
            self.pc_reg += 2

        # Fx33 - LD B, Vx
        # Store BCD representation of Vx in memory locations I, I+1, and I+2.
        elif next_code == "f?33":
            # The number we need to process
            number = self.v_regs[to_int(next_code[1])]

            # Hundreds
            self.memory[self.i_reg] = hex(number / 100)
            number -= 100 * (number / 100)  # Remove that part

            # Tens
            self.memory[self.i_reg + 1] = hex(number / 10)
            number -= 10 * (number / 10)  # Remove that part

            # Ones
            self.memory[self.i_reg + 2] = hex(number)

            self.pc_reg += 2

        #Fx55 - LD [I], Vx
        # Store registers V0 through Vx in memory starting at location I.
        elif next_code == "f?55":
            for i in range(to_int(next_code[1]) + 1):
                self.memory[self.i_reg + i] = hex(self.v_regs[i])
            self.pc_reg += 2

        # Fx65 - LD Vx, [I]
        # Read registers V0 through Vx from memory starting at location I.
        elif next_code == "f?65":
            for i in range(to_int(next_code[1]) + 1):
                self.v_regs[i] = to_int(self.memory[self.i_reg + i])
            self.pc_reg += 2

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Chip8 interpreter.')

    parser.add_argument('filename', nargs=1, type=str,
                        help='Filename of game to load.')
    parser.add_argument('--pixel-size', action="store", dest="pixel_size", type=int, default=10,
                        help='Size of an individual pixel (e.g. 2= a 2x2 square).')
    parser.add_argument('--sound', dest='sound', action='store_const',
                        const=True, default=False, help='Enable sound.')
    parser.add_argument('--fullscreen', dest='full_screen', action='store_const',
                        const=True, default=False, help='Display fullscreen.')

    args = parser.parse_args()
    pygame.init()

    pygame.display.set_caption('PyChip8')
    sound = pygame.mixer.Sound("sound.wav")

    cpu = ChipEightSystem(args.filename[0], args.pixel_size, args.full_screen)
    # 60Hz timer for decrementing delay registers
    pygame.time.set_timer(pygame.USEREVENT + 1, 17)

    try:
        while True:
            cpu.do_next_opcode()
            event = pygame.event.poll()

            if cpu.sound_timer != 0 and args.sound:
                sound.play()

            if event.type == pygame.USEREVENT + 1:
                # Timer register
                if cpu.delay_timer > 0:
                    cpu.delay_timer -= 1

                # Sound register
                if cpu.sound_timer > 0:
                    cpu.sound_timer -= 1

            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                raise RuntimeError("User pressed escape.")

            # Limit instructions per second
            pygame.time.Clock().tick(500)
    finally:
        pygame.quit()
