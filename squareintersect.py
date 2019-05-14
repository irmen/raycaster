import tkinter
from pywolf.vector import Vec2
from typing import Tuple

width = 3.0
height = 3.0
screen_scale = 200
square_origin = Vec2(1, 1)      # note: always on integer coordinates (squares are 1x1)


class Window(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.wm_title("camera ray intersection with map square")
        lb = tkinter.Label(self, text="click to set camera, move mouse to cast view ray\nNote: all squares are 1x1 units")
        lb.pack()
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
        self.viewray = Vec2(2, 0.9)
        self.cam_circle = self.canvas.create_oval(100, 100, 115, 115, fill='blue')
        self.viewray_line = self.canvas.create_line(10,10, 100, 100, fill='purple', width=2)
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
        self.viewray = Vec2(0, 0)
        self.trace_ray()

    def mousemove(self, sx, sy):
        self.viewray.x, self.viewray.y = self.from_screen(sx, sy)
        self.viewray -= self.camera
        self.trace_ray()

    def move_camera(self):
        sx, sy = self.to_screen(self.camera.x, self.camera.y)
        self.canvas.coords(self.cam_circle, sx-7, sy-7, sx+7, sy+7)

    def trace_ray(self) -> None:
        rx1, ry1 = self.to_screen(self.camera.x, self.camera.y)
        viewray_end = self.camera + self.viewray
        rx2, ry2 = self.to_screen(viewray_end.x, viewray_end.y)
        self.canvas.coords(self.viewray_line, rx1, ry1, rx2, ry2)
        if square_origin.x <= viewray_end.x <= square_origin.x+1 and square_origin.y <= viewray_end.y <= square_origin.y+1:
            self.intersect()
        else:
            self.no_intersect()

    def no_intersect(self):
        self.canvas.coords(self.intersect_point, -10, -10, -20, -20)
        self.canvas.itemconfigure(self.square, fill='grey')
        self.texcoord_lbl.configure(text="<no intersection>")

    def intersect(self) -> None:
        self.canvas.itemconfigure(self.square, fill='teal')
        texture_coordinate, intersection = self.calc_intersection_with_mapsquare(self.camera, self.viewray)
        sx, sy = self.to_screen(intersection.x, intersection.y)
        self.canvas.coords(self.intersect_point, sx-5, sy-5, sx+5, sy+5)
        self.texcoord_lbl.configure(text=f"texture coordinate: {texture_coordinate:.2f}")

    def calc_intersection_with_mapsquare(self, camera: Vec2, viewray: Vec2) -> Tuple[float, Vec2]:
        """Returns (texturecoordinate, Vec2(intersect x, intersect y))"""
        ray_end = camera + viewray
        square_center = Vec2(int(ray_end.x) + 0.5, int(ray_end.y) + 0.5)
        if camera.x < square_center.x:
            # left half of square
            if camera.y < square_center.y:
                vertex_angle = ((square_center + Vec2(-0.5, -0.5)) - camera).angle()
                intersects = "bottom" if viewray.angle() < vertex_angle else "left"
            else:
                vertex_angle = ((square_center + Vec2(-0.5, 0.5)) - camera).angle()
                intersects = "left" if viewray.angle() < vertex_angle else "top"
        else:
            # right half of square
            # TODO optimize this a bit more
            if camera.y < square_center.y:
                # mirror camera x around square center (and flip the viewray too) to avoid angle sign flip
                flipped_cam = Vec2(square_center.x - camera.x + square_center.x, camera.y)
                flipped_viewray = Vec2(-viewray.x, viewray.y)
                vertex_angle = ((square_center + Vec2(-0.5, -0.5)) - flipped_cam).angle()
                intersects = "bottom" if flipped_viewray.angle() < vertex_angle else "right"
            else:
                # mirror camera x around square center (and flip the viewray too) to avoid angle sign flip
                flipped_cam = Vec2(square_center.x - camera.x + square_center.x, camera.y)
                flipped_viewray = Vec2(-viewray.x, viewray.y)
                vertex_angle = ((square_center + Vec2(-0.5, 0.5)) - flipped_cam).angle()
                intersects = "right" if flipped_viewray.angle() < vertex_angle else "top"
        if intersects == "top":
            # determine x coordinate of intersection of the line from the camera, with the line y=square_center.y+0.5
            iy = square_center.y + 0.5
            ix = 0.0 if viewray.y == 0 else camera.x + (iy - camera.y) * viewray.x / viewray.y
            return square_center.x + 0.5 - ix, Vec2(ix, iy)
        elif intersects == "bottom":
            # determine x coordinate of intersection of the line from the camera, with the line y=square_center.y-0.5
            iy = square_center.y - 0.5
            ix = 0.0 if viewray.y == 0 else camera.x + (iy - camera.y) * viewray.x / viewray.y
            return ix - square_center.x + 0.5, Vec2(ix, iy)
        elif intersects == "left":
            # determine y coordinate of intersection of the line from the camera, with the line x=square_center.x-0.5
            ix = square_center.x - 0.5
            iy = 0.0 if viewray.x == 0 else camera.y + (ix - camera.x) * viewray.y / viewray.x
            return square_center.y + 0.5 - iy, Vec2(ix, iy)
        else:   # right
            # determine y coordinate of intersection of the line from the camera, with the line x=square_center.x+0.5
            ix = square_center.x + 0.5
            iy = 0.0 if viewray.x == 0 else camera.y + (ix - camera.x) * viewray.y / viewray.x
            return iy - square_center.y + 0.5, Vec2(ix, iy)


w = Window()
w.mainloop()

