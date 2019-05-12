import pkgutil
import io
from math import pi, tan, radians, atan2, cos, modf
from typing import Tuple, List, Optional
from PIL import Image
from .vector import Vec2


class Texture:
    SIZE = 64      # must be power of 2

    def __init__(self, imagedata: Optional[bytes]) -> None:
        if not imagedata:
            raise ValueError("no image data loaded")
        with Image.open(io.BytesIO(imagedata)) as img:
            if img.size != (self.SIZE, self.SIZE):
                raise IOError(f"texture is not {self.SIZE}x{self.SIZE}")
            if img.mode != "RGB":
                raise IOError(f"texture is not RGB (must not have alpha-channel)")
            self.pixels = []        # type: List[List[Tuple[int, int, int]]]
            for x in range(self.SIZE):
                column = [img.getpixel((x, y)) for y in range(self.SIZE)]
                self.pixels.append(column)

    def sample(self, x: float, y: float) -> Tuple[int, int, int]:
        """Sample a texture color at the given coordinates, normalized 0.0 ... 1.0"""
        # TODO weighted interpolation sampling
        sc = self.SIZE-1
        # x = min(1.0, x)
        # y = min(1.0, y)
        return self.pixels[round(x * sc)][round(y * sc)]


class Raycaster:
    FOV = radians(70)
    FOCAL_LENGTH = 3.0
    BLACK_DISTANCE = 6.0

    def __init__(self, pixwidth: int, pixheight: int) -> None:
        self.pixwidth = pixwidth
        self.pixheight = pixheight
        self.zbuffer = [[0.0] * pixheight for _ in range(pixwidth)]
        self.image = Image.new('RGB', (pixwidth, pixheight), color=0)
        self.textures = {
            "test": Texture(pkgutil.get_data(__name__, "textures/test.png")),
            "floor": Texture(pkgutil.get_data(__name__, "textures/floor.png")),
            "ceiling": Texture(pkgutil.get_data(__name__, "textures/ceiling.png")),
            "wall-bricks": Texture(pkgutil.get_data(__name__, "textures/wall-bricks.png")),
            "wall-stone": Texture(pkgutil.get_data(__name__, "textures/wall-stone.png")),
        }
        self.wall_textures = [None, self.textures["wall-bricks"], self.textures["wall-stone"]]
        self.frame = 0
        self.player_position = Vec2(0, 0)
        self.player_direction = Vec2(0, self.FOCAL_LENGTH)
        self.camera_plane = Vec2(tan(self.FOV/2) * self.FOCAL_LENGTH, 0)
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
                self.player_position = Vec2(x + 0.5, y + 0.5)
                break
        m2 = []
        for mapline in cmap:
            m2.append(bytearray([translate(c) for c in mapline]))
        return m2

    def tick(self, walltime_msec: float) -> None:
        # self.clear_zbuffer()        # TODO actually use the z-buffer for something useful
        self.frame += 1
        # raycast all pixel columns
        for x in range(self.pixwidth):
            wall, distance, texture_x = self.cast_ray(x)
            if distance > 0:
                distance = max(0.1, distance)
                wall_height = self.pixheight / distance
                if wall_height <= self.pixheight:
                    # column fits on the screen; no clipping
                    y_top = int((self.pixheight - wall_height) / 2)
                    num_y_pixels = int(wall_height)
                    texture_y = 0.0
                else:
                    # column extends outside the screen; clip it
                    y_top = 0
                    num_y_pixels = self.pixheight
                    texture_y = 0.5 - self.pixheight/wall_height/2
                self.draw_ceiling(x, y_top)
                if wall > 0:
                    texture = self.textures["test"]  # self.wall_textures[wall]
                    if not texture:
                        raise KeyError("map specifies unknown wall texture " + str(wall))
                    self.draw_wall_column(x, y_top, num_y_pixels, distance, texture, texture_x, texture_y, wall_height)
                else:
                    self.draw_black_column(x, y_top, num_y_pixels, distance)
                self.draw_floor(x, y_top + num_y_pixels)

    def cast_ray(self, pixel_x: int) -> Tuple[int, float, float]:
        camera_plane_ray = (pixel_x / self.pixwidth - 0.5) * 2 * self.camera_plane
        cast_ray = (self.player_direction + camera_plane_ray).normalized()
        # TODO correct fisheye effect: program this without using vectors and instead calc sin/cos steps?
        step = 0.0
        square = 0
        tx = 0.0
        while step <= self.BLACK_DISTANCE and square == 0:
            step += 0.02
            ray = self.player_position + cast_ray * step
            square = self.get_map_square(ray.x, ray.y)
        if square:
            # TODO walltexture x-coordinate
            tx = (pixel_x/self.pixwidth * 4) % 1.0
        return square, step, tx
        # TODO more efficient algorithm: use map square dx/dy steps to hop to the next map square instead of 'tracing the ray'

    def get_map_square(self, x: float, y: float) -> int:
        mx = int(x)
        my = int(y)
        if mx < 0 or mx >= len(self.map[0]) or my <0 or my >= len(self.map):
            return 0
        return self.map[my][mx]

    def draw_wall_column(self, x: int, y_top: int, num_y_pixels: int, distance: float,
                         texture: Texture, tx: float, ty: float, wall_height: float) -> None:
        dty = 1/int(wall_height-1)
        for y in range(y_top, y_top+num_y_pixels):
            self.set_pixel(x, y, distance, texture.sample(tx, ty))
            ty += dty

    def draw_black_column(self, x: int, y_top: int, num_y_pixels: int, distance: float) -> None:
        for y in range(y_top, y_top+num_y_pixels):
            self.set_pixel(x, y, distance, (0, 0, 0))

    def draw_ceiling(self, x: int, num_y_pixels: int) -> None:
        # TODO draw ceiling with texture
        df = 1/((self.pixheight - self.pixheight/self.BLACK_DISTANCE)/2/self.BLACK_DISTANCE)
        for y in range(num_y_pixels):
            self.set_pixel(x, y, y * df, (20, 100, 255))

    def draw_floor(self, x: int, y_start: int) -> None:
        # TODO draw floor with texture
        df = 1/((self.pixheight - self.pixheight/self.BLACK_DISTANCE)/2/self.BLACK_DISTANCE)
        for y in range(y_start, self.pixheight):
            self.set_pixel(x, y, (self.pixheight-y)*df, (0, 255, 20))

    def move_player_forward_or_back(self, amount: float) -> None:
        # TODO enforce a certain minimum distance to a wall
        new = self.player_position + amount * self.player_direction.normalized()
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_position = new

    def move_player_left_or_right(self, amount: float) -> None:
        # TODO enforce a certain minimum distance to a wall
        dn = self.player_direction.normalized()
        new = self.player_position + amount * Vec2(dn.y, -dn.x)
        if self.map[int(new.y)][int(new.x)] == 0:
            self.player_position = new

    def rotate_player(self, angle: float) -> None:
        new_angle = self.player_direction.angle() + angle
        self.rotate_player_to(new_angle)

    def rotate_player_to(self, angle: float) -> None:
        self.player_direction = Vec2.from_angle(angle) * self.FOCAL_LENGTH
        self.camera_plane = Vec2.from_angle(angle - pi / 2) * tan(self.FOV / 2) * self.FOCAL_LENGTH

    def clear_zbuffer(self) -> None:
        infinity = float("inf")
        for x in range(self.pixwidth):
            for y in range(self.pixheight):
                self.zbuffer[x][y] = infinity

    def set_pixel(self, x: int, y: int, z: float, rgb: Optional[Tuple[int, int, int]]) -> None:
        """Sets a pixel on the screen (if it is visible) and adjusts its z-buffer value.
        The pixel is darkened according to its z-value, the distance.
        If rgb is None, the pixel is transparent instead of having a color."""
        # TODO use the z-buffer (for now we ignore it because there's nothing using it at the moment)
        # if z <= self.zbuffer[x][y]:
        #     self.zbuffer[x][y] = z
        #     if rgb:
        #         if z > 0:
        #             rgb = self.rgb_brightness(rgb, bz = 1.0-min(self.BLACK_DISTANCE, z)/self.BLACK_DISTANCE)
        #         self.image.putpixel((x, y), rgb)
        if rgb:
            if z > 0:
                rgb = self.rgb_brightness(rgb, 1.0-min(self.BLACK_DISTANCE, z)/self.BLACK_DISTANCE)
            self.image.putpixel((x, y), rgb)

    def rgb_brightness(self, rgb: Tuple[int, int, int], scale: float) -> Tuple[int, int, int]:
        """adjust brightness of the color. scale 0=black, 1=neutral, >1 = whiter. (clamped at 0..255)"""
        r, g, b = rgb
        return min(int(r*scale), 255), min(int(g*scale), 255), min(int(b*scale), 255)
