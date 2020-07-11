# This is a little test program to see if the ray-square intersection algorithm works correctly.
#   $ python -m pyraycaster.squareintersecttest2

import tkinter
from .vector import Vec2
from .raycaster import Raycaster
from .mapstuff import Map
from typing import Tuple

screen_scale = 100

dungeon_map = Map(["11111111111111111111",
                   "1..................1",
                   "1..111111222222.2221",
                   "1.....1.....2.....t1",
                   "1.g...1.gh..2..h...1",
                   "1...111t....2222...1",
                   "1....t1222..2......1",
                   "1....g.222..2.1.2.11",
                   "1.h.......s........1",
                   "11111111111111111111"])


class Window(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.wm_title("camera ray intersection with map square")
        lb = tkinter.Label(self, text="click to set camera, move mouse to cast view ray\n"
                                      "Note: all squares are 1x1 units and occur on integer coordinates")
        lb.pack()
        self.raycaster = Raycaster(10, 10, dungeon_map)  # 'screen' pixels
        self.raycaster.BLACK_DISTANCE = 4
        self.canvas = tkinter.Canvas(self, width=dungeon_map.width*screen_scale, height=dungeon_map.height*screen_scale)
        for x in range(dungeon_map.width):
            rx1, ry1 = self.to_screen(x, 0)
            rx2, ry2 = self.to_screen(x, dungeon_map.height)
            self.canvas.create_line(rx1, ry1, rx2, ry2)
        for y in range(dungeon_map.height):
            rx1, ry1 = self.to_screen(0, y)
            rx2, ry2 = self.to_screen(dungeon_map.width, y)
            self.canvas.create_line(rx1, ry1, rx2, ry2)
        for y in range(dungeon_map.height):
            for x in range(dungeon_map.width):
                w = dungeon_map.get_wall(x, y)
                if w>0:
                    rx1, ry1 = self.to_screen(x, y)
                    rx2, ry2 = self.to_screen(x+1, y+1)
                    self.canvas.create_rectangle(rx1, ry1, rx2, ry2, fill='teal', outline='navy', width=4)
        self.canvas.bind("<Button-1>", lambda e: self.clicked(e.x, e.y))
        self.canvas.bind("<Motion>", lambda e: self.mousemove(e.x, e.y))
        self.camera = Vec2(1.7, 1.4)
        self.direction = Vec2(7.9, 4.1)
        self.cam_circle = self.canvas.create_oval(100, 100, 115, 115, fill='blue')
        self.texcoord_lbl = tkinter.Label(self, text="?")
        self.texcoord_lbl.pack()
        self.move_camera()
        self.cast_rays()
        self.canvas.pack()

    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        return x * screen_scale, (dungeon_map.height-y)*screen_scale

    def from_screen(self, sx: float, sy: float) -> Tuple[float, float]:
        return sx / screen_scale, dungeon_map.height - sy/screen_scale

    def clicked(self, sx, sy):
        self.camera.x, self.camera.y = self.from_screen(sx, sy)
        self.move_camera()
        self.direction = Vec2(0, 0)
        self.raycaster.rotate_player_to(0)
        self.cast_rays()

    def mousemove(self, sx, sy):
        self.direction.x, self.direction.y = self.from_screen(sx, sy)
        self.direction -= self.camera
        self.direction = self.direction.normalized()
        self.raycaster.player_position = Vec2(self.camera.x, self.camera.y)
        self.raycaster.rotate_player_to(self.direction.angle())
        self.cast_rays()

    def move_camera(self):
        sx, sy = self.to_screen(self.camera.x, self.camera.y)
        self.canvas.coords(self.cam_circle, sx-7, sy-7, sx+7, sy+7)
        self.raycaster.player_position = Vec2(self.camera.x, self.camera.y)

    def cast_rays(self) -> None:
        self.canvas.delete("cast_points")
        for px in range(self.raycaster.pixwidth):
            points, wall, distance, texture_x, side = self.raycaster.cast_ray_iter(px)
            for p in points:
                sx, sy = self.to_screen(p.x, p.y)
                self.canvas.create_rectangle(sx, sy, sx+4, sy+4, tag="cast_points")


w = Window()
w.mainloop()
