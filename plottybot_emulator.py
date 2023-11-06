import threading
import pygame
import asyncio
import socket
import json
import queue
import math
import time

WIDTH, HEIGHT = 640, 480
WHITE = (255, 255, 255)

STEPPER_DIRRECTION_UP = 1
STEPPER_DIRRECTION_DOWN = 0

class Plotter(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        # Load images
        self.base_image = pygame.image.load("plottybot_base.png")
        self.block_image = pygame.image.load("plottybot_block.png")
        self.arm_image = pygame.image.load("plottybot_arm.png")
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.width = WIDTH
        self.height = HEIGHT
        self.limit_switch_top = False
        self.limit_switch_bottom = False
        self.limit_switch_left = False
        self.limit_switch_right = False
        self.xSteps = 0
        self.ySteps = 0

    def update_position(self, x, y):
        # Store the actual x, y as floating point for precision
        self.xSteps = x 
        self.ySteps = y 

        # Update rect position for drawing (rounded to nearest integer)
        self.rect.topleft = (round(self.xSteps/250)+15, round(self.ySteps/250)-53)

    def update(self):
        # Draw base at the top of the screen
        screen.blit(self.base_image, (0, 0))
        # Draw arm, move horizontally based on x and vertically based on y
        screen.blit(self.arm_image, (self.rect.x, self.rect.y))
        # Draw block, move horizontally based on x
        screen.blit(self.block_image, (self.rect.x, 0))
       

async def move_plotter(robot, x, y, oldX, oldY):
    # Move the robot to the final position
    robot.update_position(x, y)

async def command_plotter(plotter, command_queue):
    while True:
        # Get the next command from the queue (blocks if the queue is empty)
        command = command_queue.get()

        # Process the command
        # GoToXY command
        x, y, oldX, oldY = command
        await move_plotter(plotter, x, y, oldX, oldY)

async def send_command_to_robot(x, y):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect to the server at localhost on port 8765
    client_socket.connect(("127.0.0.1", 8765))
    
    # Construct and send the message
    message = f"{x},{y}"
    client_socket.sendall(message.encode("utf-8"))
    
    # Close the client socket
    client_socket.close()
                                           

async def socket_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("0.0.0.0", 8765))
    server_socket.listen(1)

    while True:
        print("Waiting for a connection...")
        connection, client_address = server_socket.accept()

        try:
            print(f"Connection from {client_address}")
            while True:
                data = connection.recv(1024)
                if data:
                    message = data.decode("utf-8").strip()
                    print(f"Received: {message}")
                    Xsteps, Ysteps = map(int, message.split(","))

                    # Put the command in the queue
                    command_queue.put((Xsteps, Ysteps, 0, 0))
                    
                else:
                    print("No more data from client, closing connection.")
                    break

        finally:
            connection.close()
    

def run_server():
    asyncio.run(socket_server())

def run_plotter():
    asyncio.run(command_plotter(plotter, command_queue))

command_queue = queue.Queue()

pygame.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('PlottyBot Simulation')
screen.fill(WHITE)
pygame.display.flip()

plotter_group = pygame.sprite.Group()
plotter = Plotter()
plotter_group.add(plotter)

# Create a shared surface for the lines
plotter_lines_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

# Start the socket server in a separate thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Start the plotter      
plotter_thread = threading.Thread(target=run_plotter, daemon=True)
plotter_thread.start()

# Create a clock object to control the frame rate
clock = pygame.time.Clock()
desired_fps = 60



# Main loop
while True:
    # Limit the frame rate
    clock.tick(desired_fps)

    #if the user press the C key then clear the screen
    #if the user press the Q key then quit the program
    #if the user press the T key then we send a test command to the robot
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                plotter_lines_surface.fill(WHITE)
                pygame.display.flip()
            elif event.key == pygame.K_q:
                pygame.quit()
                exit()
            elif event.key == pygame.K_UP:
                #send a test command to the robot
                asyncio.run(send_command_to_robot(plotter.xSteps, plotter.ySteps - 250))
            elif event.key == pygame.K_DOWN:
                #send a test command to the robot
                asyncio.run(send_command_to_robot(plotter.xSteps, plotter.ySteps + 250))
            elif event.key == pygame.K_LEFT:
                #send a test command to the robot
                asyncio.run(send_command_to_robot(plotter.xSteps - 250, plotter.ySteps))
            elif event.key == pygame.K_RIGHT:
                #send a test command to the robot
                asyncio.run(send_command_to_robot(plotter.xSteps + 250, plotter.ySteps))
            else: 
                pass
    
            

                
    screen.fill(WHITE)

    # Draw the robot lines
    screen.blit(plotter_lines_surface, (0, 0))

    # Draw the robot
    plotter_group.update()
    # plotter_group.draw(screen)

    # write x and y coordinates on the screen aligned left
    font = pygame.font.Font(None, 20)
    text = font.render(f'x: {plotter.rect.x}, y: {plotter.rect.y}', 1, (10, 10, 10))
    textpos = text.get_rect()
    textpos.left = 0
    textpos.top = 0

    screen.blit(text, textpos)

    # write limit switch status on the screen aligned right
    font = pygame.font.Font(None, 20)
    text = font.render(f'top: {plotter.limit_switch_top}, bottom: {plotter.limit_switch_bottom}, left: {plotter.limit_switch_left}, right: {plotter.limit_switch_right}', 1, (10, 10, 10))
    textpos = text.get_rect()
    textpos.right = WIDTH
    textpos.top = 0

    screen.blit(text, textpos)
    

    # Update the display
    pygame.display.flip()

