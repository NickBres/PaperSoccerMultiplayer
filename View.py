import time

import pygame
import Model


class View:

    isInitialized = False
    def __init__(self, controller, game):
        pygame.init()
        self.game = game
        self.field = game.field
        self.screen_num = 3  # 0 - menu, 1 - game, 2 - end, 3 - wait
        self.controller = controller
        self.tile_size = 70
        self.screen_width = 0
        self.screen_height = 0
        pygame.display.set_caption('Paper Soccer: ' + self.game.color)
        self.clock = pygame.time.Clock()
        self.change_screen()

        self.menu = pygame.image.load('graphics/menu.png').convert()
        self.buttons = pygame.sprite.Group()
        self.counts = pygame.sprite.Group()
        self.create_buttons()
        self.again = pygame.sprite.GroupSingle()
        self.again_btn()
        self.font = pygame.font.Font('graphics/square-deal.ttf', 70)
        self.text = self.font.render('Wait', True, 'White')
        self.text_rect = self.text.get_rect(center=(self.screen_width / 4 - 50, self.screen_height / 2))
        self.ball = pygame.sprite.GroupSingle()
        self.ball.add(Ball(self.field, self.tile_size, self.game))

        # ////////////////////////////////////////////////////////////////////////////////////////
        # /////////////////////////////////may corrupt when run in linux////////////////////////
        # ////////////////////////////////////////////////////////////////////////////////////////
        #self.click = pygame.mixer.Sound('sound/click.mp3')
        #self.kick_sound = pygame.mixer.Sound('sound/kick.mp3')
        #self.win = pygame.mixer.Sound('sound/win.mp3')
        # ////////////////////////////////////////////////////////////////////////////////////////

    def run(self):
        count = 300
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.controller.send_exit()
                    pygame.quit()
                    exit()
                if self.screen_num == 1:  # game
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if self.game.isYourTurn:
                            for tile in self.grass_tiles:
                                if tile.check_click(event.pos):
                                    self.controller.send_move(tile.x // self.tile_size, tile.y // self.tile_size)
                                    #self.kick_sound.play()
                        else:
                            print('Wait for your turn')

                if self.screen_num == 0:  # menu
                    if event.type == pygame.MOUSEBUTTONUP:
                        for button in self.buttons:
                            if button.check_click(event.pos):
                                #self.click.play()
                                if button.type == 'Up1':
                                    self.counts.sprites()[0].increase()
                                if button.type == 'Down1':
                                    self.counts.sprites()[0].decrease()
                                if button.type == 'Up2':
                                    self.counts.sprites()[1].increase()
                                if button.type == 'Down2':
                                    self.counts.sprites()[1].decrease()
                                self.counts.update()
                                if button.type == 'Start':
                                    self.controller.send_options(self.counts.sprites()[0].count,
                                                                 self.counts.sprites()[1].count)
                if self.screen_num == 2:  # end
                    if event.type == pygame.MOUSEBUTTONUP:
                        if self.again.sprite.check_click(event.pos):
                            #self.click.play()
                            self.controller.send_again()


            if self.screen_num == 0:  # menu
                self.screen.blit(self.menu, (0, 0))
                self.buttons.draw(self.screen)
                self.counts.draw(self.screen)
            if self.screen_num == 1:  # game
                self.grass_tiles.draw(self.screen)
                self.lines.draw(self.screen)
                self.lines.update(self.field)
                self.points.draw(self.screen)
                self.points.update()
                self.ball.draw(self.screen)
                self.ball.update(self.field)
            if self.screen_num == 2:  # end
                self.screen.blit(self.menu, (0, 0))
                self.again.draw(self.screen)
                self.screen.blit(self.text, self.text_rect)
            if self.screen_num == 3:  # wait
                self.screen.blit(self.menu, (0, 0))
                self.text = self.font.render('Wait', True, 'White')
                self.screen.blit(self.text, self.text_rect)
                self.ball.draw(self.screen)
                self.ball.update(self.field)
            if self.game.state == 'wait' or self.game.state == 'wait move':
                count -= 1
                if count == 0:
                    self.controller.ask_for_update()
                    count = 300



            pygame.display.update()
            self.clock.tick(60)  # limit the loop to 60 times per sec

    def again_btn(self):
        button = pygame.image.load('graphics/buttons/b_1.png').convert_alpha()
        self.again.add(Button(self.screen_width / 4, self.screen_height / 2 + 200, button, 'Again', 'Again'))

    def game_init(self):
        self.screen = pygame.display.set_mode((self.field.width * self.tile_size, self.field.height * self.tile_size))
        self.grass_tiles = pygame.sprite.Group()
        self.lines = pygame.sprite.GroupSingle()
        self.lines.add(Lines(self.tile_size, self.field))
        self.points = pygame.sprite.Group()
        self.build_field()

    def change_screen(self):
        screen_num = 3  # wait
        if self.game.state == 'play' or self.game.state == 'wait move':
            screen_num = 1
        elif self.game.state == 'blue won' or self.game.state == 'red won':
            screen_num = 2
        elif self.game.state == 'menu':
            screen_num = 0

        if screen_num == 2:  # end
            self.screen_width = 10 * self.tile_size
            self.screen_height = 10 * self.tile_size
            self.text = self.font.render(self.game.state, True, 'White')
            self.win.play()
        if screen_num == 1:  # game
            if not self.isInitialized:
                self.game_init()
                self.isInitialized = True
            self.screen_width = self.field.width * self.tile_size
            self.screen_height = self.field.height * self.tile_size
        if screen_num == 0 or screen_num == 3:  # menu or wait
            self.screen_width = 10 * self.tile_size
            self.screen_height = 10 * self.tile_size
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.screen_num = screen_num

    def build_field(self):
        for x in range(self.field.width):
            for y in range(self.field.height):
                self.grass_tiles.add(GrassTile(x * self.tile_size, y * self.tile_size, self.tile_size))
                self.points.add(
                    Point(self.tile_size // 2 + (self.tile_size * x), self.tile_size // 2 + (self.tile_size * y),
                          self.tile_size, self.field))

    def create_buttons(self):
        button = pygame.image.load('graphics/buttons/b_1.png').convert_alpha()
        button1 = pygame.image.load('graphics/buttons/b_6.png').convert_alpha()
        button2 = pygame.image.load('graphics/buttons/b_7.png').convert_alpha()

        self.buttons.add(Button(self.screen_width / 4, self.screen_height / 1.2, button, 'Start', 'Start'))

        # first count
        self.buttons.add(Button(self.screen_width / 4 - 100, self.screen_height / 2, button1, type='Down1'))
        self.counts.add(Count(self.screen_width / 4, self.screen_height / 2, 9))
        self.buttons.add(Button(self.screen_width / 4 + 100, self.screen_height / 2, button2, type='Up1'))

        # second count
        self.buttons.add(Button(self.screen_width / 4 - 100, self.screen_height / 2 + 100, button1, type='Down2'))
        self.counts.add(Count(self.screen_width / 4, self.screen_height / 2 + 100, 13))
        self.buttons.add(Button(self.screen_width / 4 + 100, self.screen_height / 2 + 100, button2, type='Up2'))

    def set_game(self,game):
        self.game = game
        self.field = game.field


class Count(pygame.sprite.Sprite):
    def __init__(self, x, y, count):
        super().__init__()
        self.count = count
        self.font = pygame.font.Font('graphics/square-deal.ttf', 60)
        self.text = self.font.render(str(self.count), True, 'White')
        self.image = pygame.image.load('graphics/buttons/b_8.png').convert_alpha()
        posY = self.image.get_height() // 2
        posX = self.image.get_width() // 2
        self.text_rect = self.text.get_rect(center=(posX, posY))
        self.image.blit(self.text, self.text_rect)
        self.rect = self.image.get_rect(center=(x, y))

    def increase(self):
        self.count += 2
        if self.count > 19:
            self.count = 19

    def decrease(self):
        self.count -= 2
        if self.count < 3:
            self.count = 3

    def update(self):
        self.image = pygame.image.load('graphics/buttons/b_8.png').convert_alpha()
        self.text = self.font.render(str(self.count), True, 'White')
        self.image.blit(self.text, self.text_rect)


class Button(pygame.sprite.Sprite):
    def __init__(self, x, y, image, type, text=''):
        super().__init__()
        self.type = type
        self.font = pygame.font.Font('graphics/square-deal.ttf', 70)
        self.text = self.font.render(text, True, 'White')
        posY = image.get_height() // 2
        posX = image.get_width() // 2
        self.text_rect = self.text.get_rect(center=(posX, posY))
        self.image = image
        self.image.blit(self.text, self.text_rect)
        self.rect = self.image.get_rect(center=(x, y))
        self.text = text

    def check_click(self, pos):
        if self.rect.collidepoint(pos):
            return True
        return False


class Ball(pygame.sprite.Sprite):
    def __init__(self, field, tilesize, game):
        super().__init__()
        self.game = game
        self.tile_size = tilesize
        self.ball_b = pygame.image.load('graphics/balls/ball_b.png').convert_alpha()
        self.ball_r = pygame.image.load('graphics/balls/ball_r.png').convert_alpha()
        self.image = self.ball_b
        self.x = self.tile_size // 2 + (self.tile_size * field.ball.x)
        self.y = self.tile_size // 2 + (self.tile_size * field.ball.y)
        self.rect = self.image.get_rect(center=(self.x, self.y))
        self.angle = 0

    def update(self, field):
        self.x = self.tile_size // 2 + (self.tile_size * field.ball.x)
        self.y = self.tile_size // 2 + (self.tile_size * field.ball.y)
        if self.game.state == 'wait':
            self.x = 350
            self.y = 350
        if self.game.color == 'blue':
            self.image = self.ball_b
        else:
            self.image = self.ball_r
        if self.game.state == 'wait' or self.game.state == 'play':
            self.angle += 5
            angle = self.angle % 360
            self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=(self.x, self.y))


class Lines(pygame.sprite.Sprite):
    def __init__(self, tilesize, field):
        super().__init__()
        self.tile_size = tilesize
        self.field = field
        self.image = pygame.Surface((field.width * self.tile_size, field.height * self.tile_size), pygame.SRCALPHA,
                                    32).convert_alpha()
        self.draw_lines(self.field.red_lines, 'Blue')
        self.draw_lines(self.field.blue_lines, 'Red')
        self.draw_lines(self.field.wall_lines, 'White')
        self.rect = self.image.get_rect(topleft=(0, 0))

    def draw_lines(self, lines, color):
        for points in lines:
            fromX = self.tile_size // 2 + (self.tile_size * points[0].x)
            fromY = self.tile_size // 2 + (self.tile_size * points[0].y)
            toX = self.tile_size // 2 + (self.tile_size * points[1].x)
            toY = self.tile_size // 2 + (self.tile_size * points[1].y)

            width = ((self.tile_size // 10) * 2) - 1
            if fromY == toY or fromX == toX:
                width -= 2
            pygame.draw.line(self.image, color, (fromX, fromY), (toX, toY), width)

    def update(self, field):
        self.field = field
        self.draw_lines(self.field.red_lines, 'Blue')
        self.draw_lines(self.field.blue_lines, 'Red')


class Point(pygame.sprite.Sprite):
    def __init__(self, x, y, tilesize, field):
        super().__init__()
        self.field = field
        self.x = x
        self.y = y
        self.tile_size = tilesize
        self.image_w = pygame.image.load('graphics/points/point.png').convert_alpha()
        self.image_g = pygame.image.load('graphics/points/point_g.png').convert_alpha()
        self.image_r = pygame.image.load('graphics/points/point_r.png').convert_alpha()
        self.image = self.image_w
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        mouse = pygame.mouse.get_pos()
        isNear = self.field.isNear(self.x // self.tile_size, self.y // self.tile_size)
        if self.rect.collidepoint(mouse) and isNear:
            self.image = self.image_g
        elif self.rect.collidepoint(mouse):
            self.image = self.image_r
        else:
            self.image = self.image_w


class GrassTile(pygame.sprite.Sprite):
    def __init__(self, x, y, tilesize):
        super().__init__()
        self.x = x
        self.y = y
        self.tile_size = tilesize
        self.image = pygame.image.load('graphics/grass.png').convert_alpha()
        # pygame.draw.circle(self.image, 'White', (self.tile_size // 2, self.tile_size // 2), self.tile_size // 10)
        self.rect = self.image.get_rect(topleft=(x, y))

    def check_click(self, mouse):
        return self.rect.collidepoint(mouse)
