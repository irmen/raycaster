from io import BytesIO
from PIL import Image
from typing import Tuple, Optional
import pkgutil
import math
from .vector import Vec2


class Texture:
    TEXTURE_SIZE = 64      # must be power of 2
    __TEX_SIZE_MASK = TEXTURE_SIZE-1

    def __init__(self, imagedata):
        with Image.open(BytesIO(imagedata)) as img:
            if img.size != (self.TEXTURE_SIZE, self.TEXTURE_SIZE):
                raise IOError(f"texture is not {self.TEXTURE_SIZE}x{self.TEXTURE_SIZE}")
            if img.mode != "RGB":
                raise IOError(f"texture is not RGB (must not have alpha-channel)")
            self.pixels = []
            for x in range(self.TEXTURE_SIZE):
                column = [img.getpixel((x, y)) for y in range(self.TEXTURE_SIZE)]
                self.pixels.append(column)

    def get(self, x: float, y: float) -> Tuple[int, int, int]:
        return self.pixels[int(y) & self.__TEX_SIZE_MASK][int(x) & self.__TEX_SIZE_MASK]


class Raycaster:
    FOV = math.radians(70)

    def __init__(self, pixwidth, pixheight):
        self.pixwidth = pixwidth
        self.pixheight = pixheight
        self.zbuffer = [[0.0] * pixheight for _ in range(pixwidth)]
        self.image = Image.new('RGB', (pixwidth, pixheight), color=0)
        self.textures = {
            "floor": Texture(pkgutil.get_data(__name__, "textures/floor.png")),
            "ceiling": Texture(pkgutil.get_data(__name__, "textures/ceiling.png")),
            "wall-bricks": Texture(pkgutil.get_data(__name__, "textures/wall-bricks.png")),
            "wall-stone": Texture(pkgutil.get_data(__name__, "textures/wall-stone.png")),
        }
        self.frame = 0
        self.player_coords = Vec2(0, 0)
        self.player_direction = Vec2(0, 1)       # always normalized to length 1
        self.camera_plane = Vec2(math.tan(self.FOV/2), 0)
        self.map = self.load_map()      # rows, so map[y][x] to get a square

    def load_map(self):
        cmap = ["11111111111111111111",
                "1..................1",
                "1..111111222222....1",
                "1.....2.....1......1",
                "1.....2.....1......1",
                "1...112.....1222...1",
                "1.....2222..1......1",
                "1...........1......1",
                "1........s.........1",
                "11111111111111111111"]         # (0,0) is bottom left
        cmap.reverse()  # flip the Y axis so (0,0) is at bottom left

        def translate(c):
            if '0' <= c <= '9':
                return ord(c)-ord('0')
            return 0

        for y, line in enumerate(cmap):
            x = line.find('s')
            if x >= 0:
                self.player_coords = Vec2(x+0.5, y+0.5)
                break
        m2 = []
        for mapline in cmap:
            m2.append(bytearray([translate(c) for c in mapline]))
        return m2

    def tick(self, walltime_msec: float) -> None:
        self.clear_zbuffer()
        self.frame += 1
        eye_height = self.pixheight * 2 // 3      # @todo real 3d coordinates
        for x in range(self.pixwidth):
            # draw ceiling
            tex = self.textures["wall-stone"]
            for y in range(0, self.pixheight - eye_height):
                rgb = tex.get(x + walltime_msec//20, y)
                z = 1000*y/(self.pixheight - eye_height)        # @todo based on real 3d distance
                self.set_pixel((x, y), z, rgb)
            # draw floor
            tex = self.textures["wall-bricks"]
            for y in range(self.pixheight - eye_height, self.pixheight):
                rgb = tex.get(x - walltime_msec//20, y)
                z = 1000 * (self.pixheight - y) / eye_height     # @todo based on real 3d distance
                self.set_pixel((x, y), z, rgb)

    def move_player_forward_or_back(self, step):
        new = self.player_coords + step*self.player_direction
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_coords = new

    def move_player_left_or_right(self, step):
        direction = Vec2(self.player_direction.y, -self.player_direction.x)
        new = self.player_coords + step * direction
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_coords = new

    def rotate_player(self, radians):
        new_angle = self.player_direction.angle() + radians
        self.rotate_player_absolute(new_angle)

    def rotate_player_absolute(self, radians):
        self.player_direction = Vec2.from_angle(radians)
        self.camera_plane = Vec2.from_angle(radians-math.pi/2) * math.tan(self.FOV/2)

    def clear_zbuffer(self) -> None:
        infinity = float("inf")
        for x in range(self.pixwidth):
            for y in range(self.pixheight):
                self.zbuffer[x][y] = infinity

    def set_pixel(self, xy: Tuple[int, int], z: float, rgb: Optional[Tuple[int, int, int]]) -> None:
        """Sets a pixel on the screen (if it is visible) and adjusts its z-buffer value.
        The pixel is darkened according to its z-value, the distance.
        If rgb is None, the pixel is transparent instead of having a color."""
        x, y = xy
        if z <= self.zbuffer[x][y]:
            if rgb:
                if z > 0:
                    bz = 1.0-min(1000.0, z)/1000.0        # @todo z=1000 is the distance of absolute black
                    rgb = self.rgb_brightness(rgb, bz)
                self.image.putpixel(xy, rgb)
            self.zbuffer[x][y] = z

    def rgb_brightness(self, rgb: Tuple[int, int, int], scale: float) -> Tuple[int, int, int]:
        """adjust brightness of the color. scale 0=black, 1=neutral, >1 = whiter. (clamped at 0..255)"""
        r, g, b = rgb
        return min(int(r*scale), 255), min(int(g*scale), 255), min(int(b*scale), 255)
