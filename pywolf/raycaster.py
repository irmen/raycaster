import pkgutil
import io
from math import pi, tan, radians, cos
from typing import Tuple, List, Optional, BinaryIO
from PIL import Image
from .vector import Vec2


# optimization ideas:
#
# - get rid of the Vector class and inline trig functions
#   (does result in code that is less easier to understand, imo)
#

class Texture:
    SIZE = 64      # must be power of 2

    def __init__(self, image_data: BinaryIO) -> None:
        img = Image.open(image_data)
        if img.size != (self.SIZE, self.SIZE):
            raise IOError(f"texture is not {self.SIZE}x{self.SIZE}")
        if img.mode != "RGB":
            raise IOError(f"texture is not RGB (must not have alpha-channel)")
        self.image = img.load()

    @classmethod
    def from_resource(cls, name: str) -> "Texture":
        data = pkgutil.get_data(__name__, name)
        if not data:
            raise IOError("can't find texture "+name)
        return cls(io.BytesIO(data))

    def sample(self, x: float, y: float) -> Tuple[int, int, int]:
        """Sample a texture color at the given coordinates, normalized 0.0 ... 1.0"""
        # TODO weighted interpolation sampling?
        return self.image[round(x * (self.SIZE-1)), round(y * (self.SIZE-1))]


class Raycaster:
    FOV = radians(80)
    BLACK_DISTANCE = 5.0

    def __init__(self, pixwidth: int, pixheight: int) -> None:
        self.pixwidth = pixwidth
        self.pixheight = pixheight
        self.zbuffer = [[0.0] * pixheight for _ in range(pixwidth)]
        self.image = Image.new('RGB', (pixwidth, pixheight), color=0)
        self.textures = {
            "test": Texture.from_resource("textures/test.png"),
            "floor": Texture.from_resource("textures/floor.png"),
            "ceiling": Texture.from_resource("textures/ceiling.png"),
            "wall-bricks": Texture.from_resource("textures/wall-bricks.png"),
            "wall-stone": Texture.from_resource("textures/wall-stone.png"),
        }
        self.wall_textures = [None, self.textures["wall-bricks"], self.textures["wall-stone"]]
        self.frame = 0
        self.player_position = Vec2(0, 0)
        self.player_direction = Vec2(0, 1)
        self.camera_plane = Vec2(tan(self.FOV/2), 0)
        self.map = self.load_map()      # rows, so map[y][x] to get a square

    def load_map(self) -> List[bytearray]:
        cmap = ["11111111111111111111",
                "1..................1",
                "1..111111222222....1",
                "1.....2.....2......1",
                "1.....2.....2......1",
                "1...112.....2222...1",
                "1.....1222..2......1",
                "1...........2......1",
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
        # self.clear_zbuffer()        # TODO actually use the z-buffer for something
        self.frame += 1
        # cast a ray per pixel column on the screen!
        # (we end up redrawing all pixels of the screen, so no explicit clear is needed)
        # TODO fix rounding issues that cause uneven wall edges and texture noise
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
        # TODO more efficient algorithm: use map square dx/dy steps to hop map squares, instead of 'tracing the ray'
        camera_plane_ray = (pixel_x / self.pixwidth - 0.5) * 2 * self.camera_plane
        cast_ray = (self.player_direction + camera_plane_ray).normalized()
        step = 0.0
        square = 0
        tx = 0.0
        while step <= self.BLACK_DISTANCE and square == 0:
            step += 0.02        # lower this to increase ray resolution
            ray = self.player_position + cast_ray * step
            square = self.get_map_square(ray.x, ray.y)
        if square:
            # TODO correct walltexture x-coordinate by calculating ray intersection with square
            tx = (pixel_x/self.pixwidth * 4) % 1.0
        # avoid fish-eye effect by taking the distance perpendicular to the camera direction
        distance = step * cos(cast_ray.angle() - self.player_direction.angle())
        return square, distance, tx

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
        self.player_direction = Vec2.from_angle(angle)
        self.camera_plane = Vec2.from_angle(angle - pi / 2) * tan(self.FOV / 2)

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
        #     if rgb:
        #         self.zbuffer[x][y] = z
        #         if z > 0:
        #             rgb = self.rgb_brightness(rgb, bz = 1.0-min(self.BLACK_DISTANCE, z)/self.BLACK_DISTANCE)
        #         self.image.putpixel((x, y), rgb)
        if rgb:
            if z > 0:
                rgb = self.rgb_brightness(rgb, 1.0-min(self.BLACK_DISTANCE, z)/self.BLACK_DISTANCE)
            self.image.putpixel((x, y), rgb)

    def rgb_brightness(self, rgb: Tuple[int, int, int], scale: float) -> Tuple[int, int, int]:
        """adjust brightness of the color. scale 0=black, 1=neutral, >1 = whiter. (clamped to 0..255)"""
        # while theoretically it's more accurate to adjust the luminosity (by doing rgb->hls->rgb),
        # it's almost as good and a lot faster to just scale the r,g,b values themselves.
        # from colorsys import rgb_to_hls, hls_to_rgb
        # h, l, s = rgb_to_hls(*rgb)
        # r, g, b = hls_to_rgb(h, l*scale, s)
        r, g, b = rgb[0]*scale, rgb[1]*scale, rgb[2]*scale
        return min(int(r), 255), min(int(g), 255), min(int(b), 255)
