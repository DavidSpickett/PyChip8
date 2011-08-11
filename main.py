'''
Created on Jul 27, 2010

@author: davidspickett

Usage:
cd to the directory the script is in and run the following...

python main.py ROMNAME SOUND(0 or 1) FULLSCREEN(0 or 1) PIXELSIZE

So if your rom is called PONG  and you want sound on in windowed mode with 8x8 pixels run...

python main.py PONG 1 0 8

'''

import binascii, pygame, random, sys
from pygame import *

pygame.init()                                      #Begin pygame

clock = pygame.time.Clock() #Clock to limit frames per second
instructionsPerSecond = 200        #We want to run the game at 20ips

try:
    pixelSize = int(sys.argv[4]) #Size of each pixel
except:
    pixelSize = 10 #Default to 10
     
sheight = 32*pixelSize
swidth  = 64*pixelSize

try:
    if sys.argv[3] == "1": #Full screen toggle
        screen = pygame.display.set_mode((swidth,sheight),pygame.FULLSCREEN) #Set up screen
    elif sys.argv[3] == "0": 
        screen = pygame.display.set_mode((swidth,sheight))
except:
    screen = pygame.display.set_mode((swidth,sheight)) #Default to windowed

pygame.display.set_caption('Chip 8 Emulator')      #Set window title
sound = pygame.mixer.Sound("sound.wav")            #Load the 60th second sound fx

class chipEightCpu(): #Hold all the memory and pointers and shit
    def __init__(self):
        self.programCounter = 512
        #Programs begin after the interpreter at 0x200 (byte 512)
        self.memory = []
        
        #Font data 
        Zero  = ["F0","90","90","90","F0"]
        One   = ["20","60","20","20","70"]
        Two   = ["F0","10","F0","80","F0"]
        Three = ["F0","10","F0","10","F0"]
        Four  = ["90","90","F0","10","10"]
        Five  = ["F0","80","F0","10","F0"]
        Six   = ["F0","80","F0","90","F0"]
        Seven = ["F0","10","20","40","40"]
        Eight = ["F0","90","F0","90","F0"]
        Nine  = ["F0","90","F0","10","F0"]
        charA = ["F0","90","F0","90","90"]
        charB = ["E0","90","E0","90","E0"]
        charC = ["F0","80","80","80","F0"]
        charD = ["E0","90","90","90","E0"]
        charE = ["F0","80","F0","80","F0"]
        charF = ["F0","80","F0","80","80"]
        
        #This array makes adding them to memory easier
        fontData = [Zero,One,Two,Three,Four,Five,Six,Seven,Eight,Nine,charA,charB,charC,charD,charE,charF]
        
        for i in range(16): #Position in fontData array
            data = fontData[i]
            for j in range(5): #Position in a given character's data
                self.memory.append(data[j])
        
        #Now fill the memory up till 0x200
        for i in range(432):
            self.memory.append("00")
        
        #Memory 0x00 to 0x200, then the program itself...

        #Load the rom and make a list of 1 byte hex codes
        try: #See we were given a command line arg
            f = open(sys.argv[1],'rb')
        except:
            f = open('UFO','rb') #Else open default rom
        data = f.read()
        f.close()
        

        #http://www.daniweb.com/forums/post815259.html#post815259
        hex_str = str(binascii.hexlify(data)) 

        for i in range(len(hex_str)%4): #Make sure the string is 
            hex_str += '0'              #a multiple of 4 chars long

        #Move through it from start to end in steps of 2 (2 hex chars = 1 byte)
        for i in range(0, len(hex_str)-1, 2): 
            hexValue = hex_str[i]+hex_str[i+1]
            self.memory.append(hexValue)   #Add these on to the end of the system's memory
            
        while len(self.memory) < 4096: #Now pad the rest of the 4kb of virtual RAM
            self.memory.append("00")

        #16 General purpose 8 bit registers
        self.V = [0  for i in range(16)]

        #I, a 16 bit register (usually holds memory addresses)
        self.I = 0

        #The stack, an array of 16, 16 bit values
        self.stack = [0 for i in range(16)]
        #Stack pointer, 8 bit
        self.stackPointer = 0

        #The Display which is 64x32, defined so we can write with x,y like normal
        self.display = [[0 for i in range(32)] for j in range(64)]

        #Delay timer, an 8 bit register. Decrements at 60Hz
        self.delayTimer = 0

        #Sound timer, as for the delay timer
        self.soundTimer = 0
        
        #Sound option, 1 = on, 0 = off
        try:
            self.soundEnable = int(sys.argv[2]) #Use user choice
        except:
            self.soundEnable = 1 #Default to on 
        
        #Above are the keys used by the user, in the order the Chip 8 has them
        self.softKeys = [pygame.K_x,pygame.K_1,pygame.K_2,pygame.K_3,pygame.K_q,pygame.K_w,pygame.K_e,pygame.K_a,
                    pygame.K_s,pygame.K_d,pygame.K_z,pygame.K_c,pygame.K_4,pygame.K_r,pygame.K_f,pygame.K_v]
        
        #Colour used to render pixels
        self.colour = (255,255,255) #Default to white
        
    def updateDisplay(self): #Draws the data in 'display' to the screen
        global screen 
        
        screen.fill((0,0,0)) #Clear the screen by filling with black
        
        for i in range(64):
            for j in range(32):
                if self.display[i][j] == 1:
                    screen.fill(self.colour, (i*pixelSize,j*pixelSize,pixelSize,pixelSize))
                    
    def getNextOpCode(self): #Retrieves the next opcode for processing
        global done
        nextCode = self.memory[self.programCounter] + self.memory[self.programCounter+1]
        #print nextCode
        
        #Retrieve the instruction where the program counter points to
            
        #Now look at nextCode and see which instruction it is
        #http://devernay.free.fr/hacks/chip8/C8TECH10.HTM#00E0
        
        #00E0 - CLS
        #Clear the display.
        if nextCode == "00e0":
            self.display = [[0 for i in range(32)] for j in range(64)]
            self.programCounter += 2
        
        #00EE - RET
        #Return from a subroutine.
        elif nextCode == "00ee":
            self.programCounter = self.stack[self.stackPointer] #Set PC to the address on top of the stack
            self.stackPointer -= 1 #Decrement the stack pointer
            self.programCounter += 2
            
        #00FD - QUIT
        #Quit emulator (schip8 instruction)
        elif nextCode == "00fd":
            done = 1 #Exit main loop
            
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
        elif nextCode[0] == "1":
            self.programCounter = int(nextCode[1]+nextCode[2]+nextCode[3],16)
            
        #2nnn - CALL addr
        #Call subroutine at nnn.
        elif nextCode[0] == "2":
            self.stackPointer += 1 #Increment the stack pointer
            self.stack[self.stackPointer] = self.programCounter #Save the current pc position
            self.programCounter = int(nextCode[1]+nextCode[2]+nextCode[3],16) #Set the PC to nnn
        
        #3xkk - SE Vx, byte
        #Skip next instruction if Vx = kk.
        elif nextCode[0] == "3":
            if self.V[int(nextCode[1],16)] == int(nextCode[2] + nextCode[3],16):
                self.programCounter += 4 #Move an extra 2, to skip an instruction
            else:
                self.programCounter += 2
        
        #4xkk - SNE Vx, byte
        #Skip next instruction if Vx != kk.
        elif nextCode[0] == "4":
            if self.V[int(nextCode[1],16)] != int(nextCode[2] + nextCode[3],16):
                self.programCounter += 4 #Move an extra 2, to skip an instruction
            else:
                self.programCounter += 2
             
        #5xy0 - SE Vx, Vy
        #Skip next instruction if Vx = Vy.
        elif nextCode[0] == "5":
            if self.V[int(nextCode[1],16)] == self.V[int(nextCode[2],16)]:
                self.programCounter += 4 #Move an extra 2, skipping the next instruction
            else:
                self.programCounter += 2
             
        #6xkk - LD Vx, byte
        #Set Vx = kk.
        elif nextCode[0] == "6":
            self.V[int(nextCode[1],16)] = int(nextCode[2] + nextCode[3],16)
            self.programCounter += 2
            
        #7xkk - ADD Vx, byte
        #Set Vx = Vx + kk.
        elif nextCode[0] == "7":
            
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] + int(nextCode[2] + nextCode[3], 16) 
            
            #Now take the lowest 8 bits
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] & 255 
                    
            self.programCounter += 2
                
        #8xy0 - LD Vx, Vy
        #Set Vx = Vy.
        elif nextCode[0] == "8" and nextCode[3] == "0":
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[2],16)]
            self.programCounter += 2
            
        #8xy1 - OR Vx, Vy
        #Set Vx = Vx OR Vy.
        elif nextCode[0] == "8" and nextCode[3] == "1":
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] | self.V[int(nextCode[2],16)]
            self.programCounter += 2
           
        #8xy2 - AND Vx, Vy
        #Set Vx = Vx AND Vy.
        elif nextCode[0] == "8" and nextCode[3] == "2":
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] & self.V[int(nextCode[2],16)]
            self.programCounter += 2
        
        #8xy3 - XOR Vx, Vy
        #Set Vx = Vx XOR Vy.
        elif nextCode[0] == "8" and nextCode[3] == "3":
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] ^ self.V[int(nextCode[2],16)]
            self.programCounter += 2
               
        #8xy4 - ADD Vx, Vy
        #Set Vx = Vx + Vy, set VF = carry.
        elif nextCode[0] == "8" and nextCode[3] == "4":
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] + self.V[int(nextCode[2],16)] 
            #Add the two registers
            
            if sum > 255:
                self.V[15] = 1 #Set VF (the carry)
                self.V[int(nextCode[1],16)] =  self.V[int(nextCode[1],16)] & 255
                #Set Vx to the lower 8 bits of the result
                
            self.programCounter += 2
              
        #8xy5 - SUB Vx, Vy
        #Set Vx = Vx - Vy, set VF = NOT borrow.
        elif nextCode[0] == "8" and nextCode[3] == "5":
            
            self.V[15] = 0 #Set VF to 0, we'll check if it needs to be 1 next
            
            if self.V[int(nextCode[1],16)] > self.V[int(nextCode[2],16)]:
                self.V[15] = 1 #Set VF to 1, because Vx > Vy
                
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] - self.V[int(nextCode[2],16)]
            
            #if self.V[int(nextCode[1],16)] < 0: #Negative results
            #    self.V[int(nextCode[1],16)] *= -1
            
            #Not sure what happens to negative results (if Vy > Vx) so 
            #I'm just going to store it and see what happens later on.
            
            self.programCounter += 2
              
        #8xy6 - SHR Vx {, Vy}
        #Set Vx = Vx SHR 1.
        elif nextCode[0] == "8" and nextCode[3] == "6":
            
            binary = bin(self.V[int(nextCode[1],16)]) #Make binary string from integer
            
            if   binary[len(binary)-1] == "1": #Check least significant bit (looking for a remainder)
                self.V[15] = 1 #Set VF
            elif binary[len(binary)-1] == "0":
                self.V[15] = 0
                
            #Divide Vx by 2 by shifting right
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[1],16)] >> 1
            
            self.programCounter += 2
            
        #8xy7 - SUBN Vx, Vy
        #Set Vx = Vy - Vx, set VF = NOT borrow.
        elif nextCode[0] == "8" and nextCode[3] == "7":
            
            self.V[15] = 0 #Set VF to 0, we'll check if it needs to be 1 next
            
            if self.V[int(nextCode[2],16)] > self.V[int(nextCode[1],16)]:
                self.V[15] = 1 #Set VF to 1, because Vy > Vx
                
            self.V[int(nextCode[1],16)] = self.V[int(nextCode[2],16)] - self.V[int(nextCode[1],16)]
            
            #if self.V[int(nextCode[1],16)] < 0: #Negative results
            #    self.V[int(nextCode[1],16)] *= -1
                
            #Not sure what happens to negative results (if Vx > Vy) so 
            #I'm just going to store it and see what happens later on.
            
            self.programCounter += 2
        
        #8xyE - SHL Vx {, Vy}
        #Set Vx = Vx SHL 1.
        elif nextCode[0] == "8" and nextCode[3] == "e":
                    
            if   self.V[int(nextCode[1],16)]/255 > 1: #Check most significant bit (looking for a carry)
                self.V[15] = 1 #Set VF
            else:
                self.V[15] = 0 #Set VF
                
            #Multiply Vx by 2 by shifting left
            self.V[int(nextCode[1],16)] = (self.V[int(nextCode[1],16)] << 1) & 255
            #Make sure we only store the lower 8 bits
            
            self.programCounter += 2
        
        #9xy0 - SNE Vx, Vy
        #Skip next instruction if Vx != Vy.
        elif nextCode[0] == "9":
            if self.V[int(nextCode[1],16)] != self.V[int(nextCode[2],16)]:
                self.programCounter += 4 #4 means Skipping one instruction
            else:
                self.programCounter += 2

        #Annn - LD I, addr
        #Set I = nnn.
        elif nextCode[0] == "a":
            self.I = int(nextCode[1]+nextCode[2]+nextCode[3],16)
            self.programCounter += 2

        #Bnnn - JP V0, addr
        #Jump to location nnn + V0.
        elif nextCode[0] == "b":
            self.programCounter = int(nextCode[1]+nextCode[2]+nextCode[3],16) + self.V[0]

        #Cxkk - RND Vx, byte
        #Set Vx = random byte AND kk.
        elif nextCode[0] == "c":
            random.seed()
            self.V[int(nextCode[1],16)] = random.randint(0,255) & int(nextCode[2]+nextCode[3],16)
            self.programCounter += 2

        #Dxyn - DRW Vx, Vy, nibble
        #Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.
        #This is done using an XOR function, so writing to an already set pixel will erase it.
        elif nextCode[0] == "d":
            
            x = self.V[int(nextCode[1],16)] #X to begin drawing
            y = self.V[int(nextCode[2],16)] #Y to begin drawing
            length = int(nextCode[3],16)
            
            start = self.I          #Memory adress of the sprite
            data = []     #Hold data to be written to screen
            
            for i in range(length):    #Read the n-bytes into the data array
                
                data.append(bin(int(self.memory[start+i],16)))
                data[i] = data[i].replace('0', '', 1) #Remove '0b'
                data[i] = data[i].replace('b', '', 1) #So we just have a string of 0s and 1s
                
                while len(data[i]) < 8: #Pad the data so it's all 8 chars long
                    data[i] = '0' + data[i]
            
            #Now iterate through data and write it to self.display
            self.V[15] = 0 #Set to indicate no overwrites, we will set it if and when one occurs
            #print data
            for i in range(len(data)): #Rows of the sprite
                spriteRow = data[i]
                for j in range(8): #0s and 1s in each row
                        
                        newX = x+j

                        if newX < 64: #Check for overflow on X axis
                            pass
                        elif newX >= 64:
                            while newX >= 64:
                                newX -= 64 #Wrap to other side
                         
                        newY = y
   
                        if newY < 32: #Check for overflow on Y axis
                            pass
                        elif newY >= 32:
                            while newY >= 32:
                                newY -= 32 #Wrap to other side
                        
                        #print "J: " + str(j) + " newX: " + str(newX) + " newY: " + str(newY)    
                        
                        if spriteRow[j] == "1" and self.display[newX][newY] == 1: #XOR means we overwrite a pixel 
                            self.display[newX][newY] = 0 #Turn off pixel
                            self.V[15] = 1 #Indiciate overwriting occured   
                        elif spriteRow[j] == "1" and self.display[newX][newY] == 0: #Write a pixel with no collisions
                            self.display[newX][newY] = 1 #Set the pixel
                        
                y += 1 #Move down for next row
            
            self.programCounter += 2

            #Update screen
            self.updateDisplay() #Draw to 'screen'
            pygame.display.flip()

        #Ex9E - SKP Vx
        #Skip next instruction if key with the value of Vx is pressed.
        elif nextCode[0] == "e" and nextCode[2] == "9" and nextCode[3] == "e":
            print "Skip if pressed, key: " + str(self.V[int(nextCode[1],16)])
            if self.checkKeys()[self.V[int(nextCode[1],16)]] == 1: #1 means key is down
                self.programCounter += 4 #Move an extra instruction along
            else:
                self.programCounter += 2

        #ExA1 - SKNP Vx
        #Skip next instruction if key with the value of Vx is not pressed.
        elif nextCode[0] == "e" and nextCode[2] == "a" and nextCode[3] == "1":
            print "Skip if not pressed, key: " + str(self.V[int(nextCode[1],16)]) 

            if (self.checkKeys())[self.V[int(nextCode[1],16)]] == 0: #0 means key is not down
                self.programCounter += 4 #Move an extra instruction along
            else:
                self.programCounter += 2
        
        #Fx07 - LD Vx, DT
        #Set Vx = delay timer value.
        elif nextCode[0] == "f" and nextCode[2] == "0" and nextCode[3] == "7":
            self.V[int(nextCode[1],16)] = self.delayTimer
            #print self.V[int(nextCode[1],16)]
            self.programCounter += 2

        #Fx0A - LD Vx, K
        #Wait for a key press, store the value of the key in Vx.
        elif nextCode[0] == "f" and nextCode[2] == "0" and nextCode[3] == "a":
            keyPressed = 0 #0 means no key pressed, 1 means a key is pressed
            
            while keyPressed == 0: #While no key is pressed
                
                for i in range(16):
                    keyStates = self.checkKeys()
                    
                    if keyStates[i] == 1: #If a key is held down
                        keyPressed = 1 #Exit our while loop
                        keyCode = i #Record which key was bieng pressed
            
            self.V[int(nextCode[1],16)] = keyCode #Store key number in Vx
            
            self.programCounter += 2

        #Fx15 - LD DT, Vx
        #Set delay timer = Vx.
        elif nextCode[0] == "f" and nextCode[2] == "1" and nextCode[3] == "5":
            self.delayTimer = self.V[int(nextCode[1],16)]
            self.programCounter += 2

        #Fx18 - LD ST, Vx
        #Set sound timer = Vx.
        elif nextCode[0] == "f" and nextCode[2] == "1" and nextCode[3] == "8":
            self.soundTimer = self.V[int(nextCode[1],16)]
            self.programCounter += 2

        #Fx1E - ADD I, Vx
        #Set I = I + Vx.
        elif nextCode[0] == "f" and nextCode[2] == "1" and nextCode[3] == "e":
            self.I += self.V[int(nextCode[1],16)]
            self.programCounter += 2

        #Fx29 - LD F, Vx
        #Set I = location of sprite for digit Vx.
        elif nextCode[0] == "f" and nextCode[2] == "2" and nextCode[3] == "9":
            self.I = self.V[int(nextCode[1],16)]*5 #Each char bieng 5 bytes long
            self.programCounter += 2

        #Fx33 - LD B, Vx
        #Store BCD representation of Vx in memory locations I, I+1, and I+2.
        elif nextCode[0] == "f" and nextCode[2] == "3" and nextCode[3] == "3":
            number = self.V[int(nextCode[1],16)] #The number we need to process
            
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
        elif nextCode[0] == "f" and nextCode[2] == "5" and nextCode[3] == "5":
            for i in range(int(nextCode[1],16)+1):
                self.memory[self.I+i] = hex(self.V[i])
            self.programCounter += 2

        #Fx65 - LD Vx, [I]
        #Read registers V0 through Vx from memory starting at location I.
        elif nextCode[0] == "f" and nextCode[2] == "6" and nextCode[3] == "5":
            for i in range(int(nextCode[1],16)+1):
                self.V[i] = int(self.memory[self.I+i],16)
            self.programCounter += 2
        
    def checkKeys(self):  #Check the keyboard and return an array representing key states
        global done
        
        keyStates = [0 for i in range(16)] 
        #Each item represents a key on the keypad of the Chip-8
        #0 means it is not down, 1 means it is down
        
        pygame.event.pump()            #Refresh events
        key = pygame.key.get_pressed() #State of all keys
        
        if key[pygame.K_ESCAPE]:
            done = 1 #Quit emulator
        
        for i in range(16): 
            if key[self.softKeys[i]]: #Check all 16 keys in turn
                keyStates[i] = 1 #If held down, record this
            else:
                keyStates[i] = 0 #Otherwise set to 0
                
        return keyStates #Return the array for use 
 
done = 0
cpu = chipEightCpu() #Create a virtual CPU
pygame.time.set_timer(USEREVENT+1, 17) #60Hz timer for decrementing delay registers

while done == 0: #Main loop
    
    timeStart = pygame.time.get_ticks()
    cpu.getNextOpCode() #Fetch next opcode
    
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
    
    key = pygame.key.get_pressed()
    
    if key[pygame.K_ESCAPE]: #escape key
        done = 1 #end game
        
    deltat = clock.tick(instructionsPerSecond) #Limit instructions per seconds
    
pygame.quit()




