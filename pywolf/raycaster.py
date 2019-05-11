from io import BytesIO
from PIL import Image
from typing import Tuple, List, Optional
import pkgutil
import math
from .vector import Vec2


class Texture:
    SIZE = 64      # must be power of 2

    def __init__(self, imagedata: Optional[bytes]) -> None:
        if not imagedata:
            raise ValueError("no image data loaded")
        with Image.open(BytesIO(imagedata)) as img:
            if img.size != (self.SIZE, self.SIZE):
                raise IOError(f"texture is not {self.SIZE}x{self.SIZE}")
            if img.mode != "RGB":
                raise IOError(f"texture is not RGB (must not have alpha-channel)")
            self.pixels = []        # type: List[List[Tuple[int, int, int]]]
            for x in range(self.SIZE):
                column = [img.getpixel((x, y)) for y in range(self.SIZE)]
                self.pixels.append(column)

    def get(self, x: float, y: float) -> Tuple[int, int, int]:
        return self.pixels[int(y) & (self.SIZE - 1)][int(x) & (self.SIZE - 1)]


class Raycaster:
    FOV = math.radians(70)
    CAMERA_HEIGHT = 0.7
    BLACK_DISTANCE = 5.0

    def __init__(self, pixwidth: int, pixheight: int) -> None:
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
        self.wall_textures = [None, self.textures["wall-bricks"], self.textures["wall-stone"]]
        self.frame = 0
        self.player_coords = Vec2(0, 0)
        self.player_direction = Vec2(0, 1)       # always normalized to length 1
        self.camera_plane = Vec2(math.tan(self.FOV/2), 0)
        self.map = self.load_map()      # rows, so map[y][x] to get a square

    def load_map(self) -> List[bytearray]:
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
        # raycast all pixel columns
        for x in range(self.pixwidth):
            wall, distance, texture_x = self.cast_ray(x)
            if wall > 0:
                texture = self.wall_textures[wall]
                if not texture:
                    raise RuntimeError("map specifies unknown wall texture " + str(wall))
                y_top = int(math.sin(x/10) * 10) + 20
                y_bottom = int(math.cos(x/7) * 20) + 70
                dty = texture.SIZE / (y_bottom - y_top)
                self.draw_ceiling(x, y_top-1, distance)
                self.draw_wall_column(x, y_top, y_bottom, distance, texture, texture_x, dty)
                self.draw_floor(x, y_bottom+1, distance)
            else:
                # no wall hit
                # todo draw ceiling / floor
                pass

    def cast_ray(self, pixel_x: int) -> Tuple[int, float, float]:
        return 2, self.BLACK_DISTANCE*abs(1.0-2.0*pixel_x/self.pixwidth), pixel_x

    def draw_wall_column(self, x: int, y_top: int, y_bottom: int, z: float,
                         texture: Texture, tx: float, dty: float) -> None:
        ty = 0.0
        for y in range(y_top, y_bottom+1):
            self.set_pixel(x, y, z, texture.get(tx, ty))
            ty += dty

    def draw_ceiling(self, x: int, y_end: int, z: float) -> None:
        for y in range(y_end+1):
            self.set_pixel(x, y, z, (20, 100, 255))

    def draw_floor(self, x: int, y_start: int, z: float) -> None:
        for y in range(y_start, self.pixheight):
            self.set_pixel(x, y, z, (0, 160, 20))

    def move_player_forward_or_back(self, amount: float) -> None:
        new = self.player_coords + amount * self.player_direction
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_coords = new

    def move_player_left_or_right(self, amount: float) -> None:
        direction = Vec2(self.player_direction.y, -self.player_direction.x)
        new = self.player_coords + amount * direction
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_coords = new

    def rotate_player(self, angle: float) -> None:
        new_angle = self.player_direction.angle() + angle
        self.rotate_player_to(new_angle)

    def rotate_player_to(self, angle: float) -> None:
        self.player_direction = Vec2.from_angle(angle)
        self.camera_plane = Vec2.from_angle(angle - math.pi / 2) * math.tan(self.FOV / 2)

    def clear_zbuffer(self) -> None:
        infinity = float("inf")
        for x in range(self.pixwidth):
            for y in range(self.pixheight):
                self.zbuffer[x][y] = infinity

    def set_pixel(self, x: int, y: int, z: float, rgb: Optional[Tuple[int, int, int]]) -> None:
        """Sets a pixel on the screen (if it is visible) and adjusts its z-buffer value.
        The pixel is darkened according to its z-value, the distance.
        If rgb is None, the pixel is transparent instead of having a color."""
        if z <= self.zbuffer[x][y]:
            if rgb:
                if z > 0:
                    bz = 1.0-min(self.BLACK_DISTANCE, z)/self.BLACK_DISTANCE
                    rgb = self.rgb_brightness(rgb, bz)
                self.image.putpixel((x, y), rgb)
            self.zbuffer[x][y] = z

    def rgb_brightness(self, rgb: Tuple[int, int, int], scale: float) -> Tuple[int, int, int]:
        """adjust brightness of the color. scale 0=black, 1=neutral, >1 = whiter. (clamped at 0..255)"""
        r, g, b = rgb
        return min(int(r*scale), 255), min(int(g*scale), 255), min(int(b*scale), 255)
