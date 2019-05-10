import tkinter
import time
from PIL import Image, ImageTk
from .raycaster import Raycaster


class RaycasterWindow(tkinter.Tk):
    PIXEL_SCALE = 6
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
        self.update_gui_image()
        self.label.pack()
        self.after(20, self.redraw)

    def update_gui_image(self):
        self.imageTk = ImageTk.PhotoImage(self.raycaster.image.resize(
            (self.PIXEL_WIDTH*self.PIXEL_SCALE, self.PIXEL_HEIGHT*self.PIXEL_SCALE), Image.NEAREST))
        self.label.configure(image=self.imageTk)
        self.update_idletasks()

    def redraw(self):
        self.raycaster.tick(int(time.monotonic() * 1000) - self.time_msec_epoch)
        self.update_gui_image()
        now = time.monotonic()
        fps = 1/(now - self.perf_timestamp)
        self.perf_timestamp = now
        self.wm_title(f"pure Python raycaster  -  {fps:.0f} fps")
        if fps < 30:
            self.after_idle(self.redraw)
        else:
            self.after(2, self.redraw)
