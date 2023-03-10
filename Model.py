from enum import Enum
import pickle
from threading import Lock


class Game:
    color = 'white'

    def __init__(self):
        self.field = Field()
        self.isYourTurn = True
        self.state = 'not initialized'  # wait, play, menu , end ...
        self.lock = Lock()

    def set_color(self, color):
        self.lock.acquire()
        self.color = color
        self.lock.release()

    def set_state(self, state):
        self.lock.acquire()
        self.state = state
        self.lock.release()

    def set_field(self, width, height):
        self.lock.acquire()
        self.field = Field(width, height)
        self.lock.release()

    def set_isYourTurn(self, isYourTurn):
        self.lock.acquire()
        self.isYourTurn = isYourTurn
        self.lock.release()

    def set_move(self, x, y, isBlue):
        self.lock.acquire()
        if self.field.can_move(x, y):
            print(f'move to {x}, {y} isBlue = {isBlue}')
            self.field.move(x, y, isBlue)
            if self.field.no_moves():
                if isBlue:
                    self.state = 'red won'
                else:
                    self.state = 'blue won'
            point_color = self.field.currColor()
            if point_color == 'red':
                self.state = 'blue won'
                print('Goal')
            elif point_color == 'blue':
                self.state = 'red won'
                print('Goal')
        self.lock.release()

    def set_visited(self):
        self.lock.acquire()
        self.field.curr_visited()
        self.lock.release()

    def is_game_over(self):
        self.lock.acquire()
        if self.state == 'blue won' or self.state == 'red won':
            self.lock.release()
            return True
        self.lock.release()
        return False

    def serialize(self):
        return pickle.dumps({
            'field': self.field.serialize(),
            'isYourTurn': self.isYourTurn,
            'state': self.state,
            'color': self.color
        })

    def deserialize(self, data):
        data = pickle.loads(data)
        self.field.deserialize(data['field'])
        self.isYourTurn = data['isYourTurn']
        self.state = data['state']
        self.color = data['color']


class Point:
    def __init__(self, x, y, color='White'):
        self.x = x
        self.y = y
        self.isVisited = False
        self.isGoal = False
        self.color = color

    def serialize(self):
        return pickle.dumps({
            'x': self.x,
            'y': self.y,
            'isVisited': self.isVisited,
            'isGoal': self.isGoal,
            'color': self.color
        })

    def deserialize(self, data):
        data = pickle.loads(data)
        self.x = data['x']
        self.y = data['y']
        self.isVisited = data['isVisited']
        self.isGoal = data['isGoal']
        self.color = data['color']


class Field:
    def __init__(self, width=9, height=13, goal_size=3):
        self.width = width
        self.height = height
        self.goal_size = goal_size
        self.points = [[Point(x, y) for x in range(width)] for y in range(height)]
        self.wall_lines = []  # (Point, Point)
        self.red_lines = []
        self.blue_lines = []
        self.ball = Point(width // 2, height // 2)
        self.points[self.ball.y][self.ball.x].isVisited = True
        self.set_walls()

        self.set_goals()

    def currColor(self):
        return self.points[self.ball.y][self.ball.x].color

    def can_move(self, toX, toY):
        free_neighbours = self.point_free_neighbours(self.points[self.ball.y][self.ball.x])
        if self.points[toY][toX] in free_neighbours:
            return True
        return False

    def point_free_neighbours(self, point):
        neighbours = []
        if point.x - 1 >= 0 and point.y - 1 >= 0 and self.check_lines(point, self.points[point.y - 1][point.x - 1]):
            neighbours.append(self.points[point.y - 1][point.x - 1])
        if point.y - 1 >= 0 and self.check_lines(point, self.points[point.y - 1][point.x]):
            neighbours.append(self.points[point.y - 1][point.x])
        if point.x + 1 < self.width and point.y - 1 >= 0 and self.check_lines(point,
                                                                              self.points[point.y - 1][point.x + 1]):
            neighbours.append(self.points[point.y - 1][point.x + 1])
        if point.x - 1 >= 0 and self.check_lines(point, self.points[point.y][point.x - 1]):
            neighbours.append(self.points[point.y][point.x - 1])
        if point.x + 1 < self.width and self.check_lines(point, self.points[point.y][point.x + 1]):
            neighbours.append(self.points[point.y][point.x + 1])
        if point.x - 1 >= 0 and point.y + 1 < self.height and self.check_lines(point,
                                                                               self.points[point.y + 1][point.x - 1]):
            neighbours.append(self.points[point.y + 1][point.x - 1])
        if point.y + 1 < self.height and self.check_lines(point, self.points[point.y + 1][point.x]):
            neighbours.append(self.points[point.y + 1][point.x])
        if point.x + 1 < self.width and point.y + 1 < self.height and self.check_lines(point, self.points[point.y + 1][
            point.x + 1]):
            neighbours.append(self.points[point.y + 1][point.x + 1])

        return neighbours

    def curr_visited(self):
        self.points[self.ball.y][self.ball.x].isVisited = True

    def isNear(self, x, y):
        neighbours = self.point_free_neighbours(self.points[self.ball.y][self.ball.x])
        return self.points[y][x] in neighbours

    def move(self, toX, toY, isBlue):
        if not isBlue:
            self.blue_lines.append((self.points[self.ball.y][self.ball.x], self.points[toY][toX]))
        else:
            self.red_lines.append((self.points[self.ball.y][self.ball.x], self.points[toY][toX]))
        self.ball.x = toX
        self.ball.y = toY

    def no_moves(self):
        return len(self.point_free_neighbours(self.points[self.ball.y][self.ball.x])) == 0

    def set_walls(self):
        for line in self.points:
            for point in line:
                if point.x == 0 or point.x == self.width - 1 or point.y == 0 or point.y == self.height - 1:
                    point.isVisited = True
                    if (point.x == 0 or point.x == self.width - 1) and point.y < self.height - 1:  # drawing walls
                        self.wall_lines.append((point, self.points[point.y + 1][point.x]))
                    if (point.y == 0 or point.y == self.height - 1) and point.x < self.width - 1:
                        self.wall_lines.append((point, self.points[point.y][point.x + 1]))

        not_goal = (self.width - self.goal_size) // 2
        for x in range(1, not_goal + 1):
            self.points[1][x].isVisited = True
            self.points[self.height - 2][x].isVisited = True
            self.points[1][x + not_goal + self.goal_size - 2].isVisited = True
            self.points[self.height - 2][x + not_goal + self.goal_size - 2].isVisited = True
            self.wall_lines.append((self.points[1][x - 1], self.points[1][x]))
            self.wall_lines.append((self.points[self.height - 2][x - 1], self.points[self.height - 2][x]))

            self.wall_lines.append(
                (self.points[1][x + not_goal + self.goal_size - 1], self.points[1][x + not_goal + self.goal_size - 2]))
            self.wall_lines.append((self.points[self.height - 2][x + not_goal + self.goal_size - 1],
                                    self.points[self.height - 2][x + not_goal + self.goal_size - 2]))

            self.wall_lines.append((self.points[1][x], self.points[0][x - 1]))
            self.wall_lines.append((self.points[1][x - 1], self.points[0][x]))
            self.wall_lines.append((self.points[1][x], self.points[0][x]))

            self.wall_lines.append(
                (self.points[1][x + not_goal + self.goal_size - 1],
                 self.points[0][x + not_goal + self.goal_size - 2]))
            self.wall_lines.append(
                (self.points[1][x + not_goal + self.goal_size - 2],
                 self.points[0][x + not_goal + self.goal_size - 1]))
            self.wall_lines.append(
                (self.points[1][x + not_goal + self.goal_size - 2],
                 self.points[0][x + not_goal + self.goal_size - 2]))

            self.wall_lines.append((self.points[self.height - 2][x], self.points[self.height - 1][x - 1]))
            self.wall_lines.append((self.points[self.height - 2][x - 1], self.points[self.height - 1][x]))
            self.wall_lines.append((self.points[self.height - 2][x], self.points[self.height - 1][x]))

            self.wall_lines.append(
                (self.points[self.height - 2][x + not_goal + self.goal_size - 1],
                 self.points[self.height - 1][x + not_goal + self.goal_size - 2]))
            self.wall_lines.append(
                (self.points[self.height - 2][x + not_goal + self.goal_size - 2],
                 self.points[self.height - 1][x + not_goal + self.goal_size - 1]))
            self.wall_lines.append(
                (self.points[self.height - 2][x + not_goal + self.goal_size - 2],
                 self.points[self.height - 1][x + not_goal + self.goal_size - 2]))

            for x in range(self.goal_size - 1):
                self.red_lines.append((self.points[0][x + not_goal], self.points[0][x + not_goal + 1]))
                self.blue_lines.append(
                    (self.points[self.height - 1][x + not_goal], self.points[self.height - 1][x + not_goal + 1]))

    def check_lines(self, fromPoint, toPoint):
        inWalls = (fromPoint, toPoint) in self.wall_lines or (toPoint, fromPoint) in self.wall_lines
        inRed = (fromPoint, toPoint) in self.red_lines or (toPoint, fromPoint) in self.red_lines
        inBlue = (fromPoint, toPoint) in self.blue_lines or (toPoint, fromPoint) in self.blue_lines
        return not (inWalls or inBlue or inRed)

    def set_goals(self):
        not_goal = (self.width - self.goal_size) // 2
        for x in range(self.goal_size):
            self.points[0][x + not_goal].isGoal = True
            self.points[0][x + not_goal].color = 'blue'
            self.points[self.height - 1][x + not_goal].isGoal = True
            self.points[self.height - 1][x + not_goal].color = 'red'

    def serialize(self):
        return pickle.dumps({
            'width': self.width,
            'height': self.height,
            'goal_size': self.goal_size,
            'ball': self.ball.serialize(),
            'points': [[point.serialize() for point in line] for line in self.points],
            'wall_lines': [(line[0].serialize(), line[1].serialize()) for line in self.wall_lines],
            'red_lines': [(line[0].serialize(), line[1].serialize()) for line in self.red_lines],
            'blue_lines': [(line[0].serialize(), line[1].serialize()) for line in self.blue_lines],
        })

    def deserialize(self, data):
        data = pickle.loads(data)
        self.width = data['width']
        self.height = data['height']
        self.goal_size = data['goal_size']
        self.points = [[Point(0, 0) for x in range(self.width)] for y in range(self.height)]
        for y, row in enumerate(data['points']):
            for x, point_data in enumerate(row):
                self.points[y][x] = Point(0, 0)
                self.points[y][x].deserialize(point_data)
        self.wall_lines = [(Point(0, 0), Point(0, 0)) for _ in range(len(data['wall_lines']))]
        for i, line_data in enumerate(data['wall_lines']):
            self.wall_lines[i] = (Point(0, 0), Point(0, 0))
            self.wall_lines[i][0].deserialize(line_data[0])
            self.wall_lines[i][1].deserialize(line_data[1])
        self.red_lines = [(Point(0, 0), Point(0, 0)) for _ in range(len(data['red_lines']))]
        for i, line_data in enumerate(data['red_lines']):
            self.red_lines[i] = (Point(0, 0), Point(0, 0))
            self.red_lines[i][0].deserialize(line_data[0])
            self.red_lines[i][1].deserialize(line_data[1])
        self.blue_lines = [(Point(0, 0), Point(0, 0)) for _ in range(len(data['blue_lines']))]
        for i, line_data in enumerate(data['blue_lines']):
            self.blue_lines[i] = (Point(0, 0), Point(0, 0))
            self.blue_lines[i][0].deserialize(line_data[0])
            self.blue_lines[i][1].deserialize(line_data[1])
        self.ball = Point(0, 0)
        self.ball.deserialize(data['ball'])
