PyChip8 is a Python interpreter of the CHIP-8 programming language. 
It requires at least Python 2.6 and PyGame along with roms and a "sound.wav" 
file for the blip sound (if enabled).

![INVADERS](/screenshots/invaders_1.png) <img height="10" hspace="10"/> ![INVADERS](/screenshots/invaders_2.png)

![BLINKY](/screenshots/blinky_1.png) <img height="10" hspace="10"/> ![BRIX](/screenshots/brix_1.png)

Examples
--------
	python main.py INVADERS --pixel-size=5 --fullscreen
	python main.py BLINKY --sound
	
Input
-----

|Chip8 keys  |PyChip8 keys|
|------------|------------|
|1	2	3	C|1 2 3 4     |
|4	5	6	D|q w e r     |
|7	8	9	E|a s d f     |
|A	0	B	F|z x c v     |

To exit press 'esc'.

Command Line Options
--------------------
 main<i></i>.py [-h] [--pixel-size PIXEL_SIZE] [--sound] [--fullscreen] filename

### positional arguments

  filename
  
  	Filename of game to load

### optional arguments:

  -h, --help
  	
    show help message and exit
  
  --pixel-size PIXEL_SIZE
  	
    Size of an individual pixel (e.g. 2= a 2x2 square).
                        
  --sound               
  	
    Enable sound
  
  --fullscreen          
  	
    Display fullscreen

Resources
---------

- http://devernay.free.fr/hacks/chip8/C8TECH10.HTM (Technical docs)
- http://www.pong-story.com/chip8/ (Homebrew Roms)