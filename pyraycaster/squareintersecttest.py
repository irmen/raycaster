# This is a little test program to see if the ray-square intersection algorithm works correctly.
#   $ python -m pyraycaster.squareintersecttest

import tkinter
from .vector import Vec2
from .raycaster import Raycaster
from typing import Tuple

width = 3.0
height = 3.0
screen_scale = 200
square_origin = Vec2(1, 1)      # note that this has to be on integer coordinates (squares are 1x1)


class Window(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.wm_title("camera ray intersection with map square")
        lb = tkinter.Label(self, text="click to set camera, move mouse to cast view ray\nNote: all squares are 1x1 units and occur on integer coordinates")
        lb.pack()
        self.raycaster = Raycaster(10, 10)
        self.canvas = tkinter.Canvas(self, width=width*screen_scale, height=height*screen_scale)
        rx1, ry1 = self.to_screen(square_origin.x, square_origin.y)
        rx2, ry2 = self.to_screen(square_origin.x+1, square_origin.y+1)
        self.square = self.canvas.create_rectangle(rx1, ry1, rx2, ry2, fill='teal', outline='navy', width=4)
        self.canvas.create_text(rx1, ry1+10, text=f"{square_origin.x},{square_origin.y}")
        self.canvas.create_text(rx2, ry1+10, text=f"{square_origin.x+1},{square_origin.y}")
        self.canvas.create_text(rx2, ry2-10, text=f"{square_origin.x+1},{square_origin.y+1}")
        self.canvas.create_text(rx1, ry2-10, text=f"{square_origin.x},{square_origin.y+1}")
        self.canvas.bind("<Button-1>", lambda e: self.clicked(e.x, e.y))
        self.canvas.bind("<Motion>", lambda e: self.mousemove(e.x, e.y))
        self.camera = Vec2(0.7, 0.4)
        self.direction = Vec2(1, 0.3).normalized()
        self.cam_circle = self.canvas.create_oval(100, 100, 115, 115, fill='blue')
        self.castray_line = self.canvas.create_line(10, 10, 100, 100, fill='purple', width=2)
        self.intersect_point = self.canvas.create_oval(0, 0, 5, 5, fill='green')
        self.texcoord_lbl = tkinter.Label(self, text="?")
        self.texcoord_lbl.pack()
        self.move_camera()
        self.trace_ray()
        self.canvas.pack()

    def to_screen(self, x: float, y: float) -> Tuple[float, float]:
        return x * screen_scale, (height-y)*screen_scale

    def from_screen(self, sx: float, sy: float) -> Tuple[float, float]:
        return sx / screen_scale, height - sy/screen_scale

    def clicked(self, sx, sy):
        self.camera.x, self.camera.y = self.from_screen(sx, sy)
        self.move_camera()
        self.direction = Vec2(0, 0)
        self.trace_ray()

    def mousemove(self, sx, sy):
        self.direction.x, self.direction.y = self.from_screen(sx, sy)
        self.direction -= self.camera
        self.trace_ray()

    def move_camera(self):
        sx, sy = self.to_screen(self.camera.x, self.camera.y)
        self.canvas.coords(self.cam_circle, sx-7, sy-7, sx+7, sy+7)

    def trace_ray(self) -> None:
        rx1, ry1 = self.to_screen(self.camera.x, self.camera.y)
        cast_ray = self.camera + self.direction
        rx2, ry2 = self.to_screen(cast_ray.x, cast_ray.y)
        self.canvas.coords(self.castray_line, rx1, ry1, rx2, ry2)
        if square_origin.x <= cast_ray.x <= square_origin.x+1 and square_origin.y <= cast_ray.y <= square_origin.y+1:
            self.intersect()
        else:
            self.no_intersect()

    def no_intersect(self):
        self.canvas.coords(self.intersect_point, -10, -10, -20, -20)
        self.canvas.itemconfigure(self.square, fill='grey')
        self.texcoord_lbl.configure(text="<no intersection>")

    def intersect(self) -> None:
        self.canvas.itemconfigure(self.square, fill='teal')
        cast_ray = self.camera + self.direction
        texture_coordinate, intersection = self.raycaster.intersection_with_mapsquare_accurate(self.camera, cast_ray)
        sx, sy = self.to_screen(intersection.x, intersection.y)
        self.canvas.coords(self.intersect_point, sx-5, sy-5, sx+5, sy+5)
        self.texcoord_lbl.configure(text=f"texture coordinate: {texture_coordinate:.2f}")


# for interactive test:
def interactive():
    w = Window()
    w.mainloop()


# for benchmarking:
def bench():
    r = Raycaster(10, 10)
    camera = Vec2(6.5, 2.6)
    cast_ray = Vec2(2.3, 6.2)
    import time
    begin = time.perf_counter()
    for _ in range(100000):
        r.intersection_with_mapsquare_accurate(camera, cast_ray)
    duration = time.perf_counter() - begin
    print(f"original accurate took: {duration:.2f} sec")
    begin = time.perf_counter()
    for _ in range(100000):
        r.intersection_with_mapsquare_fast(cast_ray)
    duration = time.perf_counter() - begin
    print(f"new took: {duration:.2f} sec")


interactive()
# bench()

