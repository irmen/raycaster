import tkinter
import time
from PIL import Image, ImageTk
from math import sin, cos
from typing import Tuple

WIDTH = 160
HEIGHT = 100
SCALE = 6
TEXTURE_SIZE = 64      # must be power of 2
TEX_SIZE_MASK = TEXTURE_SIZE-1


class Texture:
    def __init__(self, filename):
        with Image.open(filename) as img:
            if img.size != (TEXTURE_SIZE, TEXTURE_SIZE):
                raise IOError(f"texture {filename} is not {TEXTURE_SIZE}x{TEXTURE_SIZE}")
            self.pixels = []
            for x in range(TEXTURE_SIZE):
                column = [img.getpixel((x, y)) for y in range(TEXTURE_SIZE)]
                self.pixels.append(column)

    def get(self, x: float, y: float) -> Tuple[int, int, int]:
        return self.pixels[int(y) & TEX_SIZE_MASK][int(x) & TEX_SIZE_MASK]


def brightness(rgb: Tuple[int, int, int], scale: float) -> Tuple[float, float, float]:
    """adjust brightness of the color. scale 0=black, 1=neutral, >1 = whiter. (clamped at 0..255)"""
    r, g, b = rgb
    return min(r*scale, 255.0), min(g*scale, 255.0), min(b*scale, 255.0)


class Raycaster(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.perf_timestamp = time.monotonic()
        self.time_msec_epoch = int(time.monotonic() * 1000)
        self.image = Image.new('RGB', (WIDTH, HEIGHT), color=0)
        self.textures = {
            "floor": Texture("floor.png"),
            "ceiling": Texture("ceiling.png"),
        }
        self.imageTk = None

    def start(self):
        self.resizable(0, 0)
        self.configure(borderwidth=16, background="black")
        self.wm_title("pure Python raycaster")
        self.label = tkinter.Label(self, text="pixels", border=0)
        self.update_gui_image()
        self.label.pack()
        self.after(30, self.redraw)

    def update_gui_image(self):
        self.imageTk = ImageTk.PhotoImage(self.image.resize((WIDTH*SCALE, HEIGHT*SCALE), Image.NEAREST))
        self.label.configure(image=self.imageTk)

    def redraw(self):
        self.tick(int(time.monotonic() * 1000) - self.time_msec_epoch)
        self.update_gui_image()
        now = time.monotonic()
        fps = 1/(now - self.perf_timestamp)
        self.perf_timestamp = now
        self.wm_title(f"pure Python raycaster  -  {fps:.0f} fps")
        self.after_idle(self.redraw)

    def tick(self, walltime_msec: float) -> None:
        pix = self.image.putpixel
        tex = self.textures["ceiling"]
        angle = walltime_msec/1000
        for x in range(WIDTH):
            tx = TEXTURE_SIZE/2+x*cos(angle)
            ty = TEXTURE_SIZE/2-x*sin(angle)
            tdx = sin(angle)
            tdy = cos(angle)
            for y in range(HEIGHT):
                tx += tdx
                ty += tdy
                r, g, b = brightness(tex.get(tx, ty), y/HEIGHT)
                pix((x, y), (int(r), int(g), int(b)))


window = Raycaster()
window.start()
window.mainloop()

