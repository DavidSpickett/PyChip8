import binascii, pygame, random, sys, argparse
from pygame import USEREVENT

DISPLAY_WDITH  = 64
DISPLAY_HEIGHT = 32

def to_int(chr):
    return int(chr, 16)
    
class OpCode(str):
    def __eq__(self, rhs):
        for a, b in zip(self, rhs):
            if b != '?' and a != b:
                return False
        return True
        
class ChipEightSystem():
    def __init__(self, rom_name, pixel_size, sound_enable, full_screen):
        self.pixel_size = pixel_size
        
        self.screen = pygame.display.set_mode(
            (DISPLAY_WDITH*args.pixel_size, DISPLAY_HEIGHT*args.pixel_size),
            pygame.FULLSCREEN if full_screen else 0)
        
        #Programs begin after the interpreter
        self.programCounter = 0x200
        
        self.memory = []
        self.setup_memory(rom_name)
        
        #16 General purpose 8 bit registers
        self.V = [0]*16

        #I, a 16 bit register (usually holds memory addresses)
        self.I = 0

        #The stack, an array of 16, 16 bit values
        self.stack = [0]*16
        #Stack pointer, 8 bit
        self.stackPointer = 0

        #The Display which is 64x32, defined so we can write with x,y like normal
        self.display = [([0]*DISPLAY_HEIGHT) for j in range(DISPLAY_WDITH)]

        #Delay timer, an 8 bit register. Decrements at 60Hz
        self.delayTimer = 0

        #Sound timer, as for the delay timer
        self.soundTimer = 0
        self.soundEnable = sound_enable
        
        #Above are the keys used by the user, in the order the Chip 8 has them
        self.softKeys = [pygame.K_x, pygame.K_1, pygame.K_2, pygame.K_3,
            pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_a, pygame.K_s,
            pygame.K_d, pygame.K_z, pygame.K_c, pygame.K_4, pygame.K_r, 
            pygame.K_f, pygame.K_v]
        
        #Colour used to for pixels
        self.colour = (255,255,255)
        
    def setup_memory(self, rom_name):
        #Font data 
        font_data = [
             "F0","90","90","90","F0", # Zero 
             "20","60","20","20","70", # One  
             "F0","10","F0","80","F0", # Two  
             "F0","10","F0","10","F0", # Three
             "90","90","F0","10","10", # Four 
             "F0","80","F0","10","F0", # Five 
             "F0","80","F0","90","F0", # Six  
             "F0","10","20","40","40", # Seven
             "F0","90","F0","90","F0", # Eight
             "F0","90","F0","10","F0", # Nine 
             "F0","90","F0","90","90", # charA
             "E0","90","E0","90","E0", # charB
             "F0","80","80","80","F0", # charC
             "E0","90","90","90","E0", # charD
             "F0","80","F0","80","F0", # charE
             "F0","80","F0","80","80", # charF
        ]
        
        self.memory.extend(font_data)
        
        #Fill up till 0x200
        self.memory.extend(["00"]*432)
        
        #Load the rom and make a list of 1 byte hex codes
        with open(rom_name,'rb') as f:
            data = f.read()
            #2 hex chars = 1 byte
            chunk = 2
        
            hex_str = binascii.hexlify(data)
            #Pad to make sure we have whole bytes
            hex_str += ''.join(['0']*(len(hex_str)%chunk))

            for n in range(0, len(hex_str), chunk):
                self.memory.append(hex_str[n:n+chunk])
            
        #Now pad the rest of the 4kb of virtual RAM
        self.memory.extend(["00"]*(4096-len(self.memory)))
        
    def updateDisplay(self): #Draws the data in 'display' to the screen
        self.screen.fill((0,0,0)) #Clear the screen by filling with black
        
        for i in range(DISPLAY_WDITH):
            for j in range(DISPLAY_HEIGHT):
                if self.display[i][j]:
                    self.screen.fill(self.colour, 
                        (i*self.pixel_size, j*self.pixel_size, self.pixel_size, self.pixel_size))
                    
    def doNextOpCode(self): #Retrieves the next opcode for processing
        nextCode = OpCode(self.memory[self.programCounter] + self.memory[self.programCounter+1])
        
        #Retrieve the instruction where the program counter points to
            
        #Now look at nextCode and see which instruction it is
        #http://devernay.free.fr/hacks/chip8/C8TECH10.HTM
        
        #00E0 - CLS
        #Clear the display.
        if nextCode == "00e0":
            self.display = [[False]*DISPLAY_HEIGHT for j in range(DISPLAY_WDITH)]
            self.programCounter += 2
        
        #00EE - RET
        #Return from a subroutine.
        elif nextCode == "00ee":
            self.programCounter = self.stack[self.stackPointer]
            self.stackPointer -= 1
            self.programCounter += 2
            
        #00FD - QUIT
        #Quit emulator (schip8 instruction)
        elif nextCode == "00fd":
            raise RuntimeError("Got QUIT instruction.")
            
        #00FE - chip8 mode
        #Set the graphic mode to chip8
        elif nextCode == "00fe":
            self.programCounter += 2
            
        #OOFF - schip8 mode
        #Set the graphic mode to schip 8
        elif nextCode == "00ff":
            self.programCounter += 2
        
        #0nnn - SYS addr
        #Jump to a machine code routine at nnn.
        elif nextCode[0] == "0": 
            self.programCounter += 2
        
        #1nnn - JP addr
        #Jump to location nnn.
        elif nextCode == "1???":
            self.programCounter = to_int(nextCode[1:4])
            
        #2nnn - CALL addr
        #Call subroutine at nnn.
        elif nextCode == "2???":
            self.stackPointer += 1 
            #Save the current pc position
            self.stack[self.stackPointer] = self.programCounter 
            #Set the PC to nnn
            self.programCounter = to_int(nextCode[1:4]) 
        
        #3xkk - SE Vx, byte
        #Skip next instruction if Vx == kk.
        elif nextCode == "3???":
            if self.V[to_int(nextCode[1])] == to_int(nextCode[2:4]):
                #Move an extra 2, to skip an instruction
                self.programCounter += 4 
            else:
                self.programCounter += 2
        
        #4xkk - SNE Vx, byte
        #Skip next instruction if Vx != kk.
        elif nextCode == "4???":
            if self.V[to_int(nextCode[1])] != to_int(nextCode[2:4]):
                #Move an extra 2, to skip an instruction
                self.programCounter += 4 
            else:
                self.programCounter += 2
             
        #5xy0 - SE Vx, Vy
        #Skip next instruction if Vx == Vy.
        elif nextCode == "5???":
            if self.V[to_int(nextCode[1])] == self.V[to_int(nextCode[2])]:
                #Move an extra 2, skipping the next instruction
                self.programCounter += 4 
            else:
                self.programCounter += 2
             
        #6xkk - LD Vx, byte
        #Set Vx = kk.
        elif nextCode == "6???":
            self.V[to_int(nextCode[1])] = to_int(nextCode[2:4])
            self.programCounter += 2
            
        #7xkk - ADD Vx, byte
        #Set Vx = Vx + kk.
        elif nextCode == "7???":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] + to_int(nextCode[2:4]) 
            
            #Now take the lowest 8 bits
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] & 255 
                    
            self.programCounter += 2
                
        #8xy0 - LD Vx, Vy
        #Set Vx = Vy.
        elif nextCode == "8??0":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[2])]
            self.programCounter += 2
            
        #8xy1 - OR Vx, Vy
        #Set Vx = Vx OR Vy.
        elif nextCode == "8??1":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] | self.V[to_int(nextCode[2])]
            self.programCounter += 2
           
        #8xy2 - AND Vx, Vy
        #Set Vx = Vx AND Vy.
        elif nextCode == "8??2":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] & self.V[to_int(nextCode[2])]
            self.programCounter += 2
        
        #8xy3 - XOR Vx, Vy
        #Set Vx = Vx XOR Vy.
        elif nextCode == "8??3":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] ^ self.V[to_int(nextCode[2])]
            self.programCounter += 2
               
        #8xy4 - ADD Vx, Vy
        #Set Vx = Vx + Vy, set VF = carry.
        elif nextCode == "8??4":
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] + self.V[to_int(nextCode[2])] 
            #Add the two registers
            
            if sum > 255:
                self.V[15] = 1 #Set VF (the carry)
                self.V[to_int(nextCode[1])] =  self.V[to_int(nextCode[1])] & 255
                #Set Vx to the lower 8 bits of the result
                
            self.programCounter += 2
              
        #8xy5 - SUB Vx, Vy
        #Set Vx = Vx - Vy, set VF = NOT borrow.
        elif nextCode == "8??5":
            self.V[15] = 0 #Set VF to 0, we'll check if it needs to be 1 next
            
            if self.V[to_int(nextCode[1])] > self.V[to_int(nextCode[2])]:
                self.V[15] = 1 #Set VF to 1, because Vx > Vy
                
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] - self.V[to_int(nextCode[2])]
            
            #if self.V[to_int(nextCode[1])] < 0: #Negative results
            #    self.V[to_int(nextCode[1])] *= -1
            
            #Not sure what happens to negative results (if Vy > Vx) so 
            #I'm just going to store it and see what happens later on.
            
            self.programCounter += 2
              
        #8xy6 - SHR Vx {, Vy}
        #Set Vx = Vx SHR 1.
        elif nextCode == "8??6":
            #Set VF to the LSB of the value
            self.V[15] = int(to_int(nextCode[1]) & 1)
                
            #Divide Vx by 2 by shifting right
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[1])] >> 1
            
            self.programCounter += 2
            
        #8xy7 - SUBN Vx, Vy
        #Set Vx = Vy - Vx, set VF = NOT borrow.
        elif nextCode == "8??7":
            self.V[15] = 0 #Set VF to 0, we'll check if it needs to be 1 next
            
            if self.V[to_int(nextCode[2])] > self.V[to_int(nextCode[1])]:
                self.V[15] = 1 #Set VF to 1, because Vy > Vx
                
            self.V[to_int(nextCode[1])] = self.V[to_int(nextCode[2])] - self.V[to_int(nextCode[1])]
            
            #if self.V[to_int(nextCode[1])] < 0: #Negative results
            #    self.V[to_int(nextCode[1])] *= -1
                
            #Not sure what happens to negative results (if Vx > Vy) so 
            #I'm just going to store it and see what happens later on.
            
            self.programCounter += 2
        
        #8xyE - SHL Vx {, Vy}
        #Set Vx = Vx SHL 1.
        elif nextCode == "8??e":
            if self.V[to_int(nextCode[1])]/255 > 1: #Check most significant bit (looking for a carry)
                self.V[15] = 1 #Set VF
            else:
                self.V[15] = 0 #Set VF
                
            #Multiply Vx by 2 by shifting left
            self.V[to_int(nextCode[1])] = (self.V[to_int(nextCode[1])] << 1) & 255
            #Make sure we only store the lower 8 bits
            
            self.programCounter += 2
        
        #9xy0 - SNE Vx, Vy
        #Skip next instruction if Vx != Vy.
        elif nextCode == "9???":
            if self.V[to_int(nextCode[1])] != self.V[to_int(nextCode[2])]:
                self.programCounter += 4 #4 means Skipping one instruction
            else:
                self.programCounter += 2

        #Annn - LD I, addr
        #Set I = nnn.
        elif nextCode == "a???":
            self.I = to_int(nextCode[1]+nextCode[2]+nextCode[3])
            self.programCounter += 2

        #Bnnn - JP V0, addr
        #Jump to location nnn + V0.
        elif nextCode == "b???":
            self.programCounter = to_int(nextCode[1:4]) + self.V[0]

        #Cxkk - RND Vx, byte
        #Set Vx = random byte AND kk.
        elif nextCode == "c???":
            self.V[to_int(nextCode[1])] = random.randint(0,255) & to_int(nextCode[2:4])
            self.programCounter += 2

        #Dxyn - DRW Vx, Vy, nibble
        #Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.
        #This is done using an XOR function, so writing to an already set pixel will erase it.
        elif nextCode == "d???":
            x = self.V[to_int(nextCode[1])]
            y = self.V[to_int(nextCode[2])]
            length = to_int(nextCode[3])
            
            #Memory adress of the sprite
            start = self.I  
            #Hold data to be written to screen
            data = []     
            for byte in self.memory[start:start+length]:
                data.append(format(to_int(byte), '08b'))
            
            #Now iterate through data and write it to self.display
            self.V[15] = 0 #Set to indicate no overwrites, we will set it if and when one occurs
            
            for i, sprite_row in enumerate(data): #Rows of the sprite
                for j, pixel in enumerate(sprite_row): #0s and 1s in each row
                        newX = x+j
                        if newX >= DISPLAY_WDITH:
                            newX = newX % DISPLAY_WDITH
                         
                        newY = y
                        if newY >= DISPLAY_HEIGHT:
                            newY = newY % DISPLAY_HEIGHT
                                
                        if pixel == "1":
                            if self.display[newX][newY]: #XOR means we overwrite a pixel 
                                self.display[newX][newY] = 0
                                self.V[15] = 1 #Indiciate overwriting occured   
                            else:
                                self.display[newX][newY] = 1
                       
                #Move down for next row
                y += 1 
            
            self.programCounter += 2

            #Update screen
            self.updateDisplay()
            pygame.display.flip()

        #Ex9E - SKP Vx
        #Skip next instruction if key with the value of Vx is pressed.
        elif nextCode == "e?9e":
            if self.checkKeys()[self.V[to_int(nextCode[1])]]: #1 means key is down
                self.programCounter += 4 #Move an extra instruction along
            else:
                self.programCounter += 2

        #ExA1 - SKNP Vx
        #Skip next instruction if key with the value of Vx is not pressed.
        elif nextCode == "e?a1":
            if (self.checkKeys())[self.V[to_int(nextCode[1])]]:
                self.programCounter += 2
            else:
                self.programCounter += 4 #Move an extra instruction along
                
        #Fx07 - LD Vx, DT
        #Set Vx = delay timer value.
        elif nextCode == "f?07":
            self.V[to_int(nextCode[1])] = self.delayTimer
            self.programCounter += 2

        #Fx0A - LD Vx, K
        #Wait for a key press, store the value of the key in Vx.
        elif nextCode == "f?0a":
            key_states = self.checkKeys()
            while not any(key_states):
                key_states = self.checkKeys()
                
            self.V[to_int(nextCode[1])] = key_states.index(True)
            self.programCounter += 2

        #Fx15 - LD DT, Vx
        #Set delay timer = Vx.
        elif nextCode == "f?15":
            self.delayTimer = self.V[to_int(nextCode[1])]
            self.programCounter += 2

        #Fx18 - LD ST, Vx
        #Set sound timer = Vx.
        elif nextCode == "f?18":
            self.soundTimer = self.V[to_int(nextCode[1])]
            self.programCounter += 2

        #Fx1E - ADD I, Vx
        #Set I = I + Vx.
        elif nextCode == "f?1e":
            self.I += self.V[to_int(nextCode[1])]
            self.programCounter += 2

        #Fx29 - LD F, Vx
        #Set I = location of sprite for digit Vx.
        elif nextCode == "f?29":
            self.I = self.V[to_int(nextCode[1])]*5 #Each char bieng 5 bytes long
            self.programCounter += 2

        #Fx33 - LD B, Vx
        #Store BCD representation of Vx in memory locations I, I+1, and I+2.
        elif nextCode == "f?33":
            number = self.V[to_int(nextCode[1])] #The number we need to process
            
            #Hundreds
            self.memory[self.I] = hex(number/100)
            number -= 100*(number/100) #Remove that part
            
            #Tens 
            self.memory[self.I+1] = hex(number/10)
            number -= 10*(number/10) #Remove that part
            
            #Ones
            self.memory[self.I+2] = hex(number)
            
            self.programCounter += 2

        #Fx55 - LD [I], Vx
        #Store registers V0 through Vx in memory starting at location I.
        elif nextCode == "f?55":
            for i in range(to_int(nextCode[1])+1):
                self.memory[self.I+i] = hex(self.V[i])
            self.programCounter += 2

        #Fx65 - LD Vx, [I]
        #Read registers V0 through Vx from memory starting at location I.
        elif nextCode == "f?65":
            for i in range(to_int(nextCode[1])+1):
                self.V[i] = to_int(self.memory[self.I+i])
            self.programCounter += 2
        
    def checkKeys(self):  #Check the keyboard and return an array representing key states
        pygame.event.pump()            
        keys = pygame.key.get_pressed()
        return [keys[soft_key] for soft_key in self.softKeys]
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run the Chip8 interpreter.')
    
    parser.add_argument('filename', nargs=1, type=str, help='Filename of game to load.')
    parser.add_argument('--pixel-size', action="store", dest="pixel_size", type=int, default=10, 
        help='Size of an individual pixel (e.g. 2= a 2x2 square).')
    parser.add_argument('--sound', dest='sound', action='store_const',
                    const=True, default=False, help='Enable sound.')
    parser.add_argument('--fullscreen', dest='full_screen', action='store_const',
                    const=True, default=False, help='Display fullscreen.')
    
    args = parser.parse_args()
    pygame.init()

    clock = pygame.time.Clock() #Clock to limit frames per second
    instructionsPerSecond = 200

    pygame.display.set_caption('PyChip8')
    sound = pygame.mixer.Sound("sound.wav")

    done = False
    cpu = ChipEightSystem(args.filename[0], args.pixel_size, args.sound, args.full_screen)
    pygame.time.set_timer(USEREVENT+1, 17) #60Hz timer for decrementing delay registers
    
    try:
        while True:
            timeStart = pygame.time.get_ticks()
            cpu.doNextOpCode() #Fetch next opcode
            event = pygame.event.poll()
            
            if cpu.soundTimer != 0 and cpu.soundEnable == 1:
                sound.play()
            
            if event.type == USEREVENT+1:
                #Timer register
                if cpu.delayTimer > 0: #Decrement until 0
                    cpu.delayTimer -= 1 
                
                #Sound register
                if cpu.soundTimer > 0: #Decrement until 0
                    cpu.soundTimer -= 1
            
            if pygame.key.get_pressed()[pygame.K_ESCAPE]:
                raise RuntimeError("User pressed escape.")
            
            #Limit instructions per second
            deltat = clock.tick(instructionsPerSecond) 
    finally:
        pygame.quit()
