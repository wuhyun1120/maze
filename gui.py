'''
    gui.py

    A GUI for displaying and running/stopping/stepping through games.
'''
from collections import defaultdict

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (QFormLayout, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QVBoxLayout, QWidget, QCheckBox)

from maze import Game, Maze, Goody

class GameViewer(QWidget):
    ''' The main game viewer GUI '''

    def __init__(self):
        super(GameViewer, self).__init__()

        self.cell_size = 100  # Arbitrary units
        self.scene = None
        self.game = None
        self.game_generator = None
        self.goody0 = None
        self.goody1 = None
        self.baddy = None
        self.ping_marker = {}
        self.results = defaultdict(int)
        self.round_timer = QTimer(interval=50, timeout=self._play)  # milliseconds
        self.running = False

        self.view = QGraphicsView()
        self.view.scale(1, -1)  # We want x to increase rightwards and y to increase upwards
        self.view.setMinimumSize(500, 500)

        self.round = QLabel()
        self.status = QLabel()
        self.goodies_win_count = QLineEdit(readOnly=True)
        self.draw_count = QLineEdit(readOnly=True)
        self.baddy_wins_count = QLineEdit(readOnly=True)

        self.auto_start = QCheckBox("Auto-start new game", checked=True)

        self.new_game_button = QPushButton("&New Game", clicked=self.new_game, enabled=False)
        self.step_button = QPushButton("S&tep", clicked=self.do_round, enabled=False)
        self.go_stop_button = QPushButton("&Go", clicked=self.toggle_running, enabled=False)

        stats_layout = QHBoxLayout()
        stats_layout.addWidget(QLabel("Goodies:"))
        stats_layout.addWidget(self.goodies_win_count)
        stats_layout.addWidget(QLabel("Draw:"))
        stats_layout.addWidget(self.draw_count)
        stats_layout.addWidget(QLabel("Baddy:"))
        stats_layout.addWidget(self.baddy_wins_count)

        info_layout = QFormLayout()
        info_layout.addRow("Round:", self.round)
        info_layout.addRow("Status:", self.status)
        info_layout.addRow(stats_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.new_game_button)
        buttons_layout.addWidget(self.step_button)
        buttons_layout.addWidget(self.go_stop_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addLayout(info_layout)
        layout.addWidget(self.auto_start)
        layout.addLayout(buttons_layout)


    def set_game(self, game):
        ''' Set the Game object that should be viewed by this GUI '''

        if self.running:
            self.toggle_running()

        # Alter the GUI widgets
        self.game = game
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.go_stop_button.setEnabled(True)
        self.step_button.setEnabled(True)

        height = game.maze.height
        width = game.maze.width
        cell = self.cell_size

        # Leave a border of cell_size units, and put (0, 0) at the bottom corner of the maze's interior
        self.scene.setSceneRect(-cell, -cell, (width + 2) * cell, (height + 2) * cell)
        self.view.fitInView(self.scene.sceneRect())

        wall_brush = QBrush(QColor("black"))
        wall_pen = QPen(wall_brush, 0)

        goody_brush = QBrush(QColor("green"))
        goody_pen = QPen(goody_brush, 0)

        baddy_brush =  QBrush(QColor("red"))
        baddy_pen = QPen(baddy_brush, 0)

        ping_brush = QBrush(QColor("white"))

        # Create the border
        self.scene.addRect(-cell, -cell, (width + 2) * cell, cell, pen=wall_pen, brush=wall_brush)
        self.scene.addRect(-cell, height * cell, (width + 2) * cell, cell, pen=wall_pen, brush=wall_brush)
        self.scene.addRect(-cell, 0, cell, height * cell, pen=wall_pen, brush=wall_brush)
        self.scene.addRect(width * cell, 0, cell, height * cell, pen=wall_pen, brush=wall_brush)

        # Add the obstructions:
        for y in xrange(width):
            for x in xrange(height):
                if game.maze[x, y] == Maze.wall:
                    self.scene.addRect(x * cell, y * cell, cell, cell, pen=wall_pen, brush=wall_brush)

        # Add the players
        goody0_pos = game.position[game.goody0]
        goody1_pos = game.position[game.goody1]
        baddy_pos = game.position[game.baddy]
        self.goody0 = self.scene.addEllipse(0, 0, cell, cell, pen=goody_pen, brush=goody_brush)
        self.goody0.setPos(goody0_pos.x * cell, goody0_pos.y * cell)
        self.goody1 = self.scene.addEllipse(0, 0, cell, cell, pen=goody_pen, brush=goody_brush)
        self.goody1.setPos(goody1_pos.x * cell, goody1_pos.y * cell)
        self.baddy = self.scene.addEllipse(0, 0, cell, cell, pen=baddy_pen, brush=baddy_brush)
        self.baddy.setPos(baddy_pos.x * cell, baddy_pos.y * cell)

        # Add the ping markers
        for player in (game.goody0, game.goody1, game.baddy):
            pen = goody_pen if isinstance(player, Goody) else baddy_pen
            marker = self.scene.addEllipse(cell // 4, cell // 4, cell // 2, cell // 2, pen=pen, brush=ping_brush)
            marker.hide()
            marker.setZValue(-1)
            self.ping_marker[player] = marker

        # Set the info
        self.round.setText(str(game.round))
        self.status.setText(game.status)
        self.running = False

        # Change the window title
        self.setWindowTitle("{} and {} vs. {}".format(type(game.goody0).__name__, type(game.goody1).__name__,
                                                      type(game.baddy).__name__))

    def set_game_generator(self, game_generator):
        ''' Set the game generator (a generator of Game instances) that the GUI can take from '''
        self.game_generator = game_generator
        self.new_game_button.setEnabled(True)
        self.new_game()

    def new_game(self):
        ''' Take the next Game from the generator '''
        if self.game_generator is not None:
            self.set_game(next(self.game_generator))

    def toggle_running(self):
        ''' Switch between automatically stepping through the game and allowing manual "Step" clicks '''
        if self.running:
            self.round_timer.stop()
            self.running = False
        else:
            self.round_timer.start()
            self.running = True
        self._update_widgets()

    def _play(self):
        ''' Private - called to do a round of turns and check if the game has ended '''
        result = self.do_round()
        if result != Game.in_play:
            self.toggle_running()
            if not self.running and self.auto_start.isChecked():
                self.new_game()
                self.toggle_running()


    def _update_widgets(self):
        ''' Private - Make the GUI show the current state of the Game '''
        if self.running:
            self.go_stop_button.setText("&Stop")
            self.step_button.setEnabled(False)
        else:
            self.go_stop_button.setText("&Go")
            if self.game.status == Game.in_play:
                self.step_button.setEnabled(True)
            else:
                self.go_stop_button.setEnabled(False)
                self.step_button.setEnabled(False)
        self.goodies_win_count.setText(str(self.results[Game.goodies_win]))
        self.draw_count.setText(str(self.results[Game.draw]))
        self.baddy_wins_count.setText(str(self.results[Game.baddy_wins]))

    def do_round(self):
        ''' Take a round of turns '''
        self.started = True
        game = self.game
        if game is None:
            return
        result = game.do_round()
        for graphic, player in ((self.goody0, game.goody0), (self.goody1, game.goody1), (self.baddy, game.baddy)):
            new_pos = game.position[player]
            new_x = new_pos.x * self.cell_size
            new_y = new_pos.y * self.cell_size
            graphic.setPos(new_x, new_y)
            if game.ping:
                marker = self.ping_marker[player]
                marker.setPos(new_x, new_y)
                marker.show()

        if result != Game.in_play:
            self.results[result] += 1
        if not self.running:
            self._update_widgets()
        self.round.setText(str(self.game.round))
        self.status.setText(self.game.status)
        return result
