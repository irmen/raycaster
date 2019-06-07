import tkinter
import time
import math
from PIL import Image, ImageTk
from .raycaster import Raycaster, Map


class Minimap(tkinter.Canvas):
    SCALE = 20

    def __init__(self, master: tkinter.Widget, worldmap: Map) -> None:
        self.width, self.height = worldmap.width, worldmap.height
        self.view_distance = 3
        super().__init__(master, width=self.width*self.SCALE, height=self.height*self.SCALE, bd=0, highlightthickness=0)
        colors = {
            0: "black",
            1: "blue",
            2: "red",
            3: "green",
            4: "purple",
            5: "yellow",
            6: "pink",
            7: "orange",
            8: "cyan",
            9: "white"
        }
        for y in range(self.height):
            for x in range(self.width):
                c = worldmap.get_wall(x, self.height-y-1)
                self.create_rectangle(x*self.SCALE, y*self.SCALE, (x+1)*self.SCALE, (y+1)*self.SCALE, fill=colors[c])
                m = worldmap.sprites.get((x, self.height - y - 1))
                if m:
                    self.create_oval((x+0.2)*self.SCALE, (y+0.2)*self.SCALE, (x+0.8)*self.SCALE,
                                     (y+0.8)*self.SCALE, fill='orange')
        self.camera = self.create_oval(0, 0, 8, 8, fill='white', outline='brown')
        self.camera_angle = self.create_line(4, 4, 4+15, 4, fill='teal')
        self.cam_polygon = self.create_polygon(10, 10, 20, 20, 30, 30, fill='', outline='blue')

    def move_player(self, location, direction, camera_plane):
        # note that the Y axis of the canvas is inverted
        scr_height = self.height * self.SCALE
        scr_location = location * self.SCALE
        self.coords(self.camera, scr_location.x-4, scr_height-scr_location.y+4,
                    scr_location.x+4, scr_height-scr_location.y-4)
        angle = location + direction * self.view_distance
        scr_angle = angle * self.SCALE
        self.coords(self.camera_angle, scr_location.x, scr_height-scr_location.y, scr_angle.x, scr_height-scr_angle.y)
        triangle = [
            location,
            location + (direction + camera_plane) * self.view_distance,
            location + (direction - camera_plane) * self.view_distance
        ]
        triangle = [v * self.SCALE for v in triangle]
        poly = []
        for v in triangle:
            poly.append(v.x)
            poly.append(scr_height-v.y)
        self.delete(self.cam_polygon)
        self.cam_polygon = self.create_polygon(*poly, fill='', outline='blue')


class RaycasterWindow(tkinter.Tk):
    PIXEL_SCALE = 5
    PIXEL_WIDTH = 160
    PIXEL_HEIGHT = 100

    def __init__(self):
        super().__init__()
        self.perf_timestamp = time.monotonic()
        self.time_msec_epoch = int(time.monotonic() * 1000)
        self.raycaster = Raycaster(self.PIXEL_WIDTH, self.PIXEL_HEIGHT)
        self.imageTk = None
        self.resizable(0, 0)
        self.configure(borderwidth=self.PIXEL_SCALE, background="black")
        self.wm_title("pure Python raycaster")
        self.label = tkinter.Label(self, text="pixels", border=0)
        self.init_gui_image()
        self.label.pack()
        bottomframe = tkinter.Frame(self)
        self.minimap = Minimap(bottomframe, self.raycaster.map)
        self.minimap.pack(side=tkinter.LEFT)
        self.minimap.move_player(self.raycaster.player_position, self.raycaster.player_direction,
                                 self.raycaster.camera_plane)
        controlsframe = tkinter.Frame(bottomframe)
        self.var_fov = tkinter.DoubleVar(value=math.degrees(self.raycaster.HVOF))
        self.var_bd = tkinter.DoubleVar(value=self.raycaster.BLACK_DISTANCE)
        fov_label = tkinter.Label(controlsframe, text="Field Of View")
        fov_entry = tkinter.Entry(controlsframe, textvariable=self.var_fov, justify=tkinter.RIGHT)
        bd_label = tkinter.Label(controlsframe, text="Black distance")
        bd_entry = tkinter.Entry(controlsframe, textvariable=self.var_bd, justify=tkinter.RIGHT)
        controls_label = tkinter.Label(controlsframe, text="\n\nControls:\nw,s,a,d - movement\nq,e - rotation\n"
                                                           "mouse - rotation\nleft button - move (fine)")
        fov_entry.bind("<Return>", self.change_fov)
        bd_entry.bind("<Return>", self.change_black_distance)
        fov_label.pack()
        fov_entry.pack()
        bd_label.pack()
        bd_entry.pack()
        controls_label.pack()
        controlsframe.pack()
        bottomframe.pack()
        self.mouse_button_down = False
        self.minimap.view_distance = self.raycaster.BLACK_DISTANCE
        self.bind("w", lambda e: self.raycaster.move_player_forward_or_back(0.1))
        self.bind("s", lambda e: self.raycaster.move_player_forward_or_back(-0.1))
        self.bind("a", lambda e: self.raycaster.move_player_left_or_right(-0.1))
        self.bind("d", lambda e: self.raycaster.move_player_left_or_right(0.1))
        self.bind("q", lambda e: self.raycaster.rotate_player(math.pi/50))
        self.bind("e", lambda e: self.raycaster.rotate_player(-math.pi/50))
        self.bind("<Motion>", self.mouse_move)
        self.bind("<Button-1>", lambda e: self.mouse_button_change(True))
        self.bind("<ButtonRelease-1>", lambda e: self.mouse_button_change(False))
        self.after(20, self.redraw)

    def change_fov(self, e):
        self.raycaster.set_fov(math.radians(self.var_fov.get()))
        self.focus_set()

    def change_black_distance(self, e):
        self.raycaster.BLACK_DISTANCE = self.var_bd.get()
        self.minimap.view_distance = self.raycaster.BLACK_DISTANCE
        self.focus_set()

    def mouse_move(self, e):
        mousex = self.winfo_pointerx() - self.winfo_rootx()
        mousex -= self.winfo_width()//2
        self.raycaster.rotate_player_to(math.pi / 2.0 + 2.0 * math.pi * -mousex / 800.0)

    def mouse_button_change(self, down: bool) -> None:
        self.mouse_button_down = down

    def init_gui_image(self):
        self.imageTk = ImageTk.PhotoImage(self.raycaster.image.resize(
            (self.PIXEL_WIDTH*self.PIXEL_SCALE, self.PIXEL_HEIGHT*self.PIXEL_SCALE), Image.NEAREST))
        self.label.configure(image=self.imageTk)
        self.update_idletasks()

    def update_gui_image(self):
        self.imageTk.paste(
            self.raycaster.image.resize(
                (
                    self.PIXEL_WIDTH*self.PIXEL_SCALE,
                    self.PIXEL_HEIGHT*self.PIXEL_SCALE
                ),
                Image.NEAREST
            ),
            (0, 0)
        )

    def redraw(self):
        self.raycaster.tick(int(time.monotonic() * 1000) - self.time_msec_epoch)
        self.update_gui_image()
        self.minimap.move_player(self.raycaster.player_position, self.raycaster.player_direction,
                                 self.raycaster.camera_plane)
        now = time.monotonic()
        fps = 1/(now - self.perf_timestamp)
        self.perf_timestamp = now
        self.wm_title(f"pure Python raycaster  -  {fps:.0f} fps")
        if self.mouse_button_down:
            self.raycaster.move_player_forward_or_back(1/fps)
        if fps < 30:
            self.after_idle(self.redraw)
        else:
            self.after(2, self.redraw)


def main():
    w = RaycasterWindow()
    w.mainloop()
