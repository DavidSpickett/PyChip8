'''Python interpreter for Chip8 games. See main.py --help for usage.'''

import random, argparse, pygame, os

DISPLAY_WIDTH = 64
DISPLAY_HEIGHT = 32

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

class Opcode(object):
	def __init__(self, code):
		self.code = code

	def __eq__(self, rhs):
		n = self.code
		for c in reversed(rhs):
			if c != '?' and (n & 0xf) != int(c, 16):
				return False
			n >>= 4
		return True
	
	def __str__(self):
		return '%04x' % self.code

	def __getitem__(self, key):
		return int(str(self)[key], 16)

	def __getslice__(self, i, j):
		return int(str(self)[i:j], 16)


class ChipEightSystem(object):
    '''
    The Chip8 virtual machine.
    '''

    def __init__(self, rom_name, pixel_size, full_screen):
        self.pixel_size = pixel_size

        self.screen = pygame.display.set_mode(
            (DISPLAY_WIDTH * args.pixel_size, DISPLAY_HEIGHT * args.pixel_size),
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

	self.clear_display()

        
        # Delay timer, an 8 bit register.
        self.delay_timer = 0
        # Sound timer, as for the delay timer
        self.sound_timer = 0

        # Colour used to for pixels
        self.colour = (255, 255, 255)

    def clear_display(self):
        # The Display which is 64x32, defined so we can write with x,y
	# You'd think you could do [[0]*H]*W, but that just references
	# the same list each time
        self.display = [([0] * DISPLAY_HEIGHT) for _ in range(DISPLAY_WIDTH)]

    def setup_memory(self, rom_name):
        '''
        Initialise the memory with font and ROM file data.
        '''

        font_data = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,  # Zero
            0x20, 0x60, 0x20, 0x20, 0x70,  # One
            0xF0, 0x10, 0xF0, 0x80, 0xF0,  # Two
            0xF0, 0x10, 0xF0, 0x10, 0xF0,  # Three
            0x90, 0x90, 0xF0, 0x10, 0x10,  # Four
            0xF0, 0x80, 0xF0, 0x10, 0xF0,  # Five
            0xF0, 0x80, 0xF0, 0x90, 0xF0,  # Six
            0xF0, 0x10, 0x20, 0x40, 0x40,  # Seven
            0xF0, 0x90, 0xF0, 0x90, 0xF0,  # Eight
            0xF0, 0x90, 0xF0, 0x10, 0xF0,  # Nine
            0xF0, 0x90, 0xF0, 0x90, 0x90,  # charA
            0xE0, 0x90, 0xE0, 0x90, 0xE0,  # charB
            0xF0, 0x80, 0x80, 0x80, 0xF0,  # charC
            0xE0, 0x90, 0x90, 0x90, 0xE0,  # charD
            0xF0, 0x80, 0xF0, 0x80, 0xF0,  # charE
            0xF0, 0x80, 0xF0, 0x80, 0x80,  # charF
        ]
        self.memory.extend(font_data)

        # Fill up till 0x200
        self.memory.extend([0x00] * 432)

        # Load the rom and make a list of 1 byte hex codes
        with open(rom_name, 'rb') as rom_file:
	    self.memory.extend(map(ord, rom_file.read()))

        # Now pad the rest of the 4kb of virtual RAM
        self.memory.extend([0x00] * (4096 - len(self.memory)))

    def _update_display(self):
        '''
        Draws the data in self.display to the screen.
        '''

        # Clear the screen by filling with black
        self.screen.fill((0, 0, 0))

        for i in range(DISPLAY_WIDTH):
            for j in range(DISPLAY_HEIGHT):
                if self.display[i][j]:
                    self.screen.fill(self.colour,
                                     (i * self.pixel_size, j * self.pixel_size,
                                      self.pixel_size, self.pixel_size))

    def fetch(self):
	o = Opcode((self.memory[self.pc_reg] << 8) | self.memory[self.pc_reg+1])
	self.pc_reg += 2
	return o

    def do_next_opcode(self):
        '''
        Retrieve and process the next opcode.
        '''
        next_code = self.fetch() 

        # Retrieve the instruction where the program counter points to

        # Now look at next_code and see which instruction it is
        # http://devernay.free.fr/hacks/chip8/C8TECH10.HTM

        #00E0 - CLS
        # Clear the display.
        if next_code == "00e0":
	    self.clear_display()

        # 00EE - RET
        # Return from a subroutine.
        elif next_code == "00ee":
            self.pc_reg = self.stack[self.stack_pointer]
            self.stack_pointer -= 1

        # 00FD - QUIT
        # Quit emulator (schip8 instruction)
        elif next_code == "00fd":
            raise RuntimeError("Got QUIT instruction.")

        # 00FE - chip8 mode
        # Set the graphic mode to chip8
        elif next_code == "00fe":
	    pass

        # OOFF - schip8 mode
        # Set the graphic mode to schip 8
        elif next_code == "00ff":
            pass

        # 0nnn - SYS addr
        # Jump to a machine code routine at nnn.
        elif next_code[0] == "0":
	    raise RuntimeError("Implement me!")

        # 1nnn - JP addr
        # Jump to location nnn.
        elif next_code == "1???":
            self.pc_reg = next_code[1:4]

        # 2nnn - CALL addr
        # Call subroutine at nnn.
        elif next_code == "2???":
            self.stack_pointer += 1
            # Save the current pc position
            self.stack[self.stack_pointer] = self.pc_reg
            # Set the PC to nnn
            self.pc_reg = next_code[1:4]

        # 3xkk - SE Vx, byte
        # Skip next instruction if Vx == kk.
        elif next_code == "3???":
            if self.v_regs[next_code[1]] == next_code[2:4]:
                # Move an extra 2, to skip an instruction
                self.pc_reg += 2

        # 4xkk - SNE Vx, byte
        # Skip next instruction if Vx != kk.
        elif next_code == "4???":
            if self.v_regs[next_code[1]] != next_code[2:4]:
                # Move an extra 2, to skip an instruction
                self.pc_reg += 2

        # 5xy0 - SE Vx, Vy
        # Skip next instruction if Vx == Vy.
        elif next_code == "5???":
            if self.v_regs[next_code[1]] == self.v_regs[next_code[2]]:
                # Move an extra 2, skipping the next instruction
                self.pc_reg += 2

        # 6xkk - LD Vx, byte
        # Set Vx = kk.
        elif next_code == "6???":
            n = next_code[2:4]
            self.v_regs[next_code[1]] = next_code[2:4]

        # 7xkk - ADD Vx, byte
        # Set Vx = Vx + kk.
        elif next_code == "7???":
            res = self.v_regs[next_code[1]] + next_code[2:4]
            self.v_regs[next_code[1]] = res

            # Now take the lowest 8 bits
            self.v_regs[next_code[1]] = self.v_regs[next_code[1]] & 0xFF 

        # 8xy0 - LD Vx, Vy
        # Set Vx = Vy.
        elif next_code == "8??0":
            self.v_regs[next_code[1]] = self.v_regs[next_code[2]]

        # 8xy1 - OR Vx, Vy
        # Set Vx = Vx OR Vy.
        elif next_code == "8??1":
            res = self.v_regs[next_code[1]] | self.v_regs[next_code[2]]
            self.v_regs[next_code[1]] = res

        # 8xy2 - AND Vx, Vy
        # Set Vx = Vx AND Vy.
        elif next_code == "8??2":
            res = self.v_regs[next_code[1]] & self.v_regs[next_code[2]]
            self.v_regs[next_code[1]] = res

        # 8xy3 - XOR Vx, Vy
        # Set Vx = Vx XOR Vy.
        elif next_code == "8??3":
            res = self.v_regs[next_code[1]] ^ self.v_regs[next_code[2]]
            self.v_regs[next_code[1]] = res

        # 8xy4 - ADD Vx, Vy
        # Set Vx = Vx + Vy, set VF = carry.
        elif next_code == "8??4":
            res = self.v_regs[next_code[1]] + self.v_regs[next_code[2]]
            self.v_regs[next_code[1]] = res
            # Add the two registers

            if sum > 255:
                self.v_regs[15] = 1  # Set VF (the carry)
                self.v_regs[next_code[1]] = self.v_regs[next_code[1]] & 0xff 
                # Set Vx to the lower 8 bits of the result

        # 8xy5 - SUB Vx, Vy
        # Set Vx = Vx - Vy, set VF = NOT borrow.
        elif next_code == "8??5":
            # Set VF to 0, we'll check if it needs to be 1 next
            self.v_regs[15] = 0

            if self.v_regs[next_code[1]] > self.v_regs[next_code[2]]:
                self.v_regs[15] = 1  # Set VF to 1, because Vx > Vy

            res = self.v_regs[next_code[1]] - self.v_regs[next_code[2]]
            self.v_regs[next_code[1]] = res

            # if self.v_regs[next_code[1]] < 0: #Negative results
            #    self.v_regs[next_code[1]] *= -1

            # Not sure what happens to negative results (if Vy > Vx) so
            # I'm just going to store it and see what happens later on.

        # 8xy6 - SHR Vx {, Vy}
        # Set Vx = Vx SHR 1.
        elif next_code == "8??6":
            # Set VF to the LSB of the value
            self.v_regs[15] = int(next_code[1] & 1)

            # Divide Vx by 2 by shifting right
            self.v_regs[next_code[1]] = self.v_regs[next_code[1]] >> 1

        # 8xy7 - SUBN Vx, Vy
        # Set Vx = Vy - Vx, set VF = NOT borrow.
        elif next_code == "8??7":
            # Set VF to 0, we'll check if it needs to be 1 next
            self.v_regs[15] = 0

            if self.v_regs[next_code[2]] > self.v_regs[next_code[1]]:
                self.v_regs[15] = 1  # Set VF to 1, because Vy > Vx

            res = self.v_regs[next_code[2]] - self.v_regs[next_code[1]]
            self.v_regs[next_code[1]] = res

            # if self.v_regs[next_code[1]] < 0: #Negative results
            #    self.v_regs[next_code[1]] *= -1

            # Not sure what happens to negative results (if Vx > Vy) so
            # I'm just going to store it and see what happens later on.

        # 8xyE - SHL Vx {, Vy}
        # Set Vx = Vx SHL 1.
        elif next_code == "8??e":
            # Check most significant bit (looking for a carry)
	    if self.v_regs[next_code[1]] & 0x80:
                self.v_regs[15] = 1  # Set VF
            else:
                self.v_regs[15] = 0  # Set VF

            # Multiply Vx by 2 by shifting left
            self.v_regs[next_code[1]] = (
                self.v_regs[next_code[1]] << 1) & 0xff 
            # Make sure we only store the lower 8 bits

        # 9xy0 - SNE Vx, Vy
        # Skip next instruction if Vx != Vy.
        elif next_code == "9???":
            if self.v_regs[next_code[1]] != self.v_regs[next_code[2]]:
                # Skipping one instruction
                self.pc_reg += 2

        # Annn - LD I, addr
        # Set I = nnn.
        elif next_code == "a???":
            self.i_reg = next_code[1:4]

        # Bnnn - JP V0, addr
        # Jump to location nnn + V0.
        elif next_code == "b???":
            self.pc_reg = next_code[1:4] + self.v_regs[0]

        # Cxkk - RND Vx, byte
        # Set Vx = random byte AND kk.
        elif next_code == "c???":
            rnd = random.randint(0, 255)
            self.v_regs[next_code[1]] = rnd & next_code[2:4]

        # Dxyn - DRW Vx, Vy, nibble
        # Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.
        # This is done using an XOR function, so writing to an already set
        # pixel will erase it.
        elif next_code == "d???":
            x_pos = self.v_regs[next_code[1]]
            y_pos = self.v_regs[next_code[2]]
            length = next_code[3]

            # Memory adress of the sprite
            start = self.i_reg
            # Hold data to be written to screen
            data = []
            for byte in self.memory[start:start + length]:
                data.append(format(byte, '08b'))

            # Set to indicate no overwrites, set later if one occurs
            self.v_regs[15] = 0

            for i, sprite_row in enumerate(data):  # Rows of the sprite
                for j, pixel in enumerate(sprite_row):  # 0s and 1s in each row
                    new_x = (x_pos + j) % DISPLAY_WIDTH
                    new_y = y_pos % DISPLAY_HEIGHT

                    if pixel == "1":
			# Set if overwriting will occur
			# Note that any single overwrite in a draw will cause
			# v15 to be 1, even if subsequent pixels don't overlap
			if self.display[new_x][new_y]:
				self.v_regs[15] = 1
			# Setting is an XOR operation
			self.display[new_x][new_y] = not self.display[new_x][new_y]

                # Move down for next row
                y_pos += 1

            # Update screen
            self._update_display()
            pygame.display.flip()

        # Ex9E - SKP Vx
        # Skip next instruction if key with the value of Vx is pressed.
        elif next_code == "e?9e":
            if check_keys()[self.v_regs[next_code[1]]]:  # 1 means key is down
                self.pc_reg += 2  # Move an extra instruction along

        # ExA1 - SKNP Vx
        # Skip next instruction if key with the value of Vx is not pressed.
        elif next_code == "e?a1":
            if not check_keys()[self.v_regs[next_code[1]]]:
                # Move an extra instruction along
                self.pc_reg += 2

        # Fx07 - LD Vx, DT
        # Set Vx = delay timer value.
        elif next_code == "f?07":
            self.v_regs[next_code[1]] = self.delay_timer

        # Fx0A - LD Vx, K
        # Wait for a key press, store the value of the key in Vx.
        elif next_code == "f?0a":
            key_states = check_keys()
            while not any(key_states):
                key_states = check_keys()

            self.v_regs[next_code[1]] = key_states.index(True)

        # Fx15 - LD DT, Vx
        # Set delay timer = Vx.
        elif next_code == "f?15":
            self.delay_timer = self.v_regs[next_code[1]]

        # Fx18 - LD ST, Vx
        # Set sound timer = Vx.
        elif next_code == "f?18":
            self.sound_timer = self.v_regs[next_code[1]]

        # Fx1E - ADD I, Vx
        # Set I = I + Vx.
        elif next_code == "f?1e":
            self.i_reg += self.v_regs[next_code[1]]

        # Fx29 - LD F, Vx
        # Set I = location of sprite for digit Vx.
        elif next_code == "f?29":
            # Each char being 5 bytes long
            self.i_reg = self.v_regs[next_code[1]] * 5

        # Fx33 - LD B, Vx
        # Store BCD representation of Vx in memory locations I, I+1, and I+2.
        elif next_code == "f?33":
            # The number we need to process
            number = self.v_regs[next_code[1]]

            # Hundreds
            self.memory[self.i_reg] = number / 100
            number -= 100 * (number / 100)  # Remove that part

            # Tens
            self.memory[self.i_reg + 1] = number / 10
            number -= 10 * (number / 10)  # Remove that part

            # Ones
            self.memory[self.i_reg + 2] = number

        #Fx55 - LD [I], Vx
        # Store registers V0 through Vx in memory starting at location I.
        elif next_code == "f?55":
            for i in range(next_code[1] + 1):
                self.memory[self.i_reg + i] = self.v_regs[i]

        # Fx65 - LD Vx, [I]
        # Read registers V0 through Vx from memory starting at location I.
        elif next_code == "f?65":
            for i in range(next_code[1] + 1):
                self.v_regs[i] = self.memory[self.i_reg + i]

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
    
    if not os.path.isfile("sound.wav"):
        print "Warning: \"sound.wav\" file required for sound."
        sound = None
    else:
        sound = pygame.mixer.Sound("sound.wav")

    cpu = ChipEightSystem(args.filename[0], args.pixel_size, args.full_screen)
    # 60Hz timer for decrementing delay registers
    pygame.time.set_timer(pygame.USEREVENT + 1, 17)

    #Try is belt and braces in case something goes wrong in fullscreen mode.
    try:
        run = True;
        while run:
            cpu.do_next_opcode()
            event = pygame.event.poll()

            if cpu.sound_timer != 0 and args.sound and sound:
                sound.play()

            if event.type == pygame.USEREVENT + 1:
                # Timer register
                if cpu.delay_timer > 0:
                    cpu.delay_timer -= 1

                # Sound register
                if cpu.sound_timer > 0:
                    cpu.sound_timer -= 1

            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                run = False

            # Limit instructions per second
            pygame.time.Clock().tick(500)
    finally:
        pygame.quit()
