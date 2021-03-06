from math import pi, tan, radians, cos
from typing import Tuple, List, Optional
from PIL import Image
from .vector import Vec2
from .mapstuff import Map, Texture


# Micro Optimization ideas:
#
# - get rid of the Vector class and inline the trig functions instead.
#   (but that results in code that is harder to understand)


class Raycaster:
    HVOF = radians(80)
    BLACK_DISTANCE = 4.5

    def __init__(self, pixwidth: int, pixheight: int, dungeon_map: Map) -> None:
        self.pixwidth = pixwidth
        self.pixheight = pixheight
        self.empty_zbuffer = [float("inf")] * pixheight * pixwidth
        self.zbuffer = self.empty_zbuffer[:]
        self.ceiling_sizes = [0] * pixwidth
        self.image = Image.new('RGB', (pixwidth, pixheight), color=0)
        self.image_buf = self.image.load()
        self.textures = {
            "test": Texture("textures/test.png"),
            "floor": Texture("textures/floor.png"),
            "ceiling": Texture("textures/ceiling.png"),
            "wall-bricks": Texture("textures/wall-bricks.png"),
            "wall-stone": Texture("textures/wall-stone.png"),
            "creature-gargoyle": Texture("textures/gargoyle.png"),
            "creature-hero": Texture("textures/legohero.png"),
            "treasure": Texture("textures/treasure.png")
        }
        self.wall_textures = [self.textures["test"], self.textures["wall-bricks"], self.textures["wall-stone"]]
        self.frame = 0
        self.player_position = Vec2(0, 0)
        self.player_direction = Vec2(0, 1)
        self.camera_plane = Vec2(tan(self.HVOF / 2), 0)
        self.map = dungeon_map
        self.player_position = Vec2(self.map.player_start[0]+0.5, self.map.player_start[1]+0.5)

    def tick(self, walltime_msec: float) -> None:
        self.frame += 1
        self.zbuffer[:] = self.empty_zbuffer    # clear zbuffer
        # cast a ray per pixel column on the screen!
        # (we end up redrawing all pixels of the screen, so no explicit clear is needed)
        # NOTE: multithreading is not useful because of Python's GIL
        #       multiprocessing is probably not useful because of IPC overhead to sync the world state...
        d_screen = self.screen_distance()
        for x in range(self.pixwidth):
            wall, distance, texture_x = self.cast_ray_dda(x)
            if distance > 0:
                ceiling_size = int(self.pixheight * (1.0 - d_screen / distance) / 2.0)
                self.ceiling_sizes[x] = ceiling_size
                if wall > 0:
                    self.draw_column(x, ceiling_size, distance, self.wall_textures[wall], texture_x)
                else:
                    self.draw_black_column(x, ceiling_size, distance)
            else:
                self.ceiling_sizes[x] = 0
        self.draw_floor_and_ceiling(self.ceiling_sizes, d_screen)
        self.draw_sprites(d_screen)

    def cast_ray_dda(self, pixel_x: int) -> Tuple[int, float, float]:
        # code adapted from: https://lodev.org/cgtutor/raycasting.html

        # calculate ray position and direction
        cameraX = 2.0 * pixel_x / self.pixwidth - 1.0   # x-coordinate in camera space
        ray = self.player_direction + self.camera_plane * cameraX

        # which box of the map we're in
        mapX = int(self.player_position.x)
        mapY = int(self.player_position.y)

        # length of ray from one x or y-side to next x or y-side
        deltaDistX = abs(1 / ray.x) if ray.x else float("inf")
        deltaDistY = abs(1 / ray.y) if ray.y else float("inf")

        side = False  # was a NS or a EW wall hit?

        # calculate step and initial sideDist
        # stepX,Y = what direction to step in x or y-direction (either +1 or -1)
        # sideDistX,Y = length of ray from current position to next x or y-side
        if ray.x < 0:
            stepX = -1
            sideDistX = (self.player_position.x - mapX) * deltaDistX
        else:
            stepX = 1
            sideDistX = (mapX + 1.0 - self.player_position.x) * deltaDistX

        if ray.y < 0:
            stepY = -1
            sideDistY = (self.player_position.y - mapY) * deltaDistY
        else:
            stepY = 1
            sideDistY = (mapY + 1.0 - self.player_position.y) * deltaDistY

        # perform DDA
        wall = 0
        while wall==0:
            # jump to next map square, OR in x-direction, OR in y-direction
            if sideDistX < sideDistY:
                sideDistX += deltaDistX
                mapX += stepX
                side = False
            else:
                sideDistY += deltaDistY
                mapY += stepY
                side = True

            # Check if ray has hit a wall
            wall = self.map.get_wall(mapX, mapY)

        # Calculate distance of perpendicular ray (Euclidean distance will give fisheye effect!)
        if side:
            distance = (mapY - self.player_position.y + (1 - stepY) / 2) / ray.y
        else:
            distance = (mapX - self.player_position.x + (1 - stepX) / 2) / ray.x

        if 0 < distance < self.BLACK_DISTANCE:
            # calculate texture X of wall (0.0 - 1.0)
            if side:
                wall_tex_x = self.player_position.x + distance * ray.x
            else:
                wall_tex_x = self.player_position.y + distance * ray.y
            # wall_tex_x -= floor(wall_tex_x)
            return wall, distance, wall_tex_x
        else:
            return -1, self.BLACK_DISTANCE, 0.0

    def map_square(self, x: float, y: float) -> int:
        mx = int(x)
        my = int(y)
        if mx < 0 or mx >= self.map.width or my < 0 or my >= self.map.height:
            return 255
        return self.map.get_wall(mx, my)

    def brightness(self, distance: float) -> float:
        return max(0.0, 1.0 - distance / self.BLACK_DISTANCE)

    def draw_column(self, x: int, ceiling: int, distance: float,
                    texture: Texture, tx: float) -> None:
        start_y = max(0, ceiling)
        num_pixels = self.pixheight - 2*start_y
        wall_height = self.pixheight - 2*ceiling
        brightness = self.brightness(distance)
        for y in range(start_y, start_y+num_pixels):
            self.set_pixel(x, y, distance, brightness, texture.sample(tx, (y-ceiling) / wall_height))

    def draw_black_column(self, x: int, ceiling: int, distance: float) -> None:
        start_y = max(0, ceiling)
        num_pixels = self.pixheight - 2*start_y
        for y in range(start_y, start_y+num_pixels):
            self.set_pixel(x, y, distance, 1.0, (0, 0, 0, 0))

    def draw_floor_and_ceiling(self, ceiling_sizes: List[int], d_screen: float) -> None:
        mcs = max(ceiling_sizes)
        if mcs <= 0:
            return
        max_height_possible = int(self.pixheight*(1.0-d_screen/self.BLACK_DISTANCE)/2.0)
        ceiling_tex = self.textures["ceiling"]
        floor_tex = self.textures["floor"]
        for y in range(min(mcs, max_height_possible)):
            sy = 0.5 - y / self.pixheight
            d_ground = 0.5 * d_screen / sy    # how far, horizontally over the ground, is this away from us?
            brightness = self.brightness(d_ground)
            for x, h in enumerate(ceiling_sizes):
                if y < h and d_ground < self.zbuffer[x+y*self.pixwidth]:
                    camera_plane_ray = (x / self.pixwidth - 0.5) * 2 * self.camera_plane
                    ray = self.player_position + d_ground*(self.player_direction + camera_plane_ray)
                    # we use the fact that the ceiling and floor are mirrored
                    self.set_pixel(x, y, d_ground, brightness, ceiling_tex.sample(ray.x, ray.y))
                    self.set_pixel(x, self.pixheight-y-1, d_ground, brightness, floor_tex.sample(ray.x, ray.y))

    def get_sprite_texture(self, spritetype: str) -> Tuple[Texture, float]:
        if spritetype == "g":
            return self.textures["creature-gargoyle"], 0.8
        elif spritetype == "h":
            return self.textures["creature-hero"], 0.7
        elif spritetype == "t":
            return self.textures["treasure"], 0.6
        else:
            raise KeyError("unknown sprite: " + spritetype)

    def draw_sprites(self, d_screen: float) -> None:
        for (mx, my), mc in self.map.sprites.items():
            sprite_pos = Vec2(mx + 0.5, my + 0.5)
            sprite_vec = sprite_pos - self.player_position
            sprite_direction = sprite_vec.angle()
            sprite_distance = sprite_vec.magnitude()
            sprite_view_angle = self.player_direction.angle() - sprite_direction
            if sprite_view_angle < -pi:
                sprite_view_angle += 2*pi
            elif sprite_view_angle > pi:
                sprite_view_angle -= 2*pi
            if sprite_distance < self.BLACK_DISTANCE and abs(sprite_view_angle) < self.HVOF/1.4:
                texture, sprite_size = self.get_sprite_texture(mc)
                middle_pixel_column = int((0.5*(sprite_view_angle/(self.HVOF/2))+0.5) * self.pixwidth)
                sprite_perpendicular_distance = sprite_distance * cos(sprite_view_angle)
                if sprite_perpendicular_distance < 0.2:
                    continue
                ceiling_above_sprite_square = int(self.pixheight * (1.0 - d_screen / sprite_perpendicular_distance) / 2.0)
                pixel_height = self.pixheight - ceiling_above_sprite_square*2
                y_offset = int((1.0-sprite_size) * pixel_height) + ceiling_above_sprite_square
                tex_y_offset = 0
                if y_offset < 0:
                    tex_y_offset = abs(y_offset)
                    y_offset = 0
                brightness = self.brightness(sprite_perpendicular_distance)
                pixel_height = int(sprite_size * pixel_height)
                pixel_width = pixel_height
                for y in range(min(pixel_height, self.pixheight-y_offset)):
                    for x in range(max(0, int(middle_pixel_column - pixel_width/2)),
                                   min(self.pixwidth, int(middle_pixel_column + pixel_width/2))):
                        tc = texture.sample((x-middle_pixel_column)/pixel_width - 0.5, (y+tex_y_offset)/pixel_height)
                        if tc[3] > 200:  # consider alpha channel
                            self.set_pixel(x, y+y_offset, sprite_perpendicular_distance, brightness, tc)

    def set_pixel(self, x: int, y: int, z: float, brightness: float, rgba: Optional[Tuple[int, int, int, int]]) -> None:
        """Sets a pixel on the screen (if it is visible) and adjusts its z-buffer value.
        The pixel's brightness is adjusted as well.
        If rgba is None, the pixel is transparent instead of having a color."""
        if rgba and z < self.zbuffer[x+y*self.pixwidth]:
            self.zbuffer[x+y*self.pixwidth] = z
            if z > 0 and brightness != 1.0:
                rgba = self.color_brightness(rgba, brightness)
            self.image_buf[x, y] = rgba

    def color_brightness(self, rgba: Tuple[int, int, int, int], brightness: float) -> Tuple[int, int, int, int]:
        """adjust brightness of the color. brightness 0=pitch black, 1=normal"""
        # while theoretically it's more accurate to adjust the luminosity (by doing rgb->hls->rgb),
        # it's almost as good and a lot faster to just scale the r,g,b values themselves.
        # from colorsys import rgb_to_hls, hls_to_rgb
        # h, l, s = rgb_to_hls(*rgb)
        # r, g, b = hls_to_rgb(h, l*scale, s)
        return int(rgba[0] * brightness), int(rgba[1] * brightness), int(rgba[2] * brightness), rgba[3]

    def move_player_forward_or_back(self, amount: float) -> None:
        new = self.player_position + amount * self.player_direction.normalized()
        self._move_player(new.x, new.y)

    def move_player_left_or_right(self, amount: float) -> None:
        dn = self.player_direction.normalized()
        new = self.player_position + amount * Vec2(dn.y, -dn.x)
        self._move_player(new.x, new.y)

    def _move_player(self, x: float, y: float) -> None:
        if self.map_square(x, y) == 0:
            # stay a certain minimum distance from the walls
            if self.map_square(x + 0.1, y):
                x = int(x) + 0.9
            if self.map_square(x - 0.1, y):
                x = int(x) + 0.1
            if self.map_square(x, y + 0.1):
                y = int(y) + 0.9
            if self.map_square(x, y - 0.1):
                y = int(y) + 0.1
            self.player_position = Vec2(x, y)

    def rotate_player(self, angle: float) -> None:
        new_angle = self.player_direction.angle() + angle
        self.rotate_player_to(new_angle)

    def rotate_player_to(self, angle: float) -> None:
        self.player_direction = Vec2.from_angle(angle)
        self.camera_plane = Vec2.from_angle(angle - pi / 2) * tan(self.HVOF / 2)

    def set_fov(self, fov: float) -> None:
        self.HVOF = fov
        self.rotate_player(0.0)

    def screen_distance(self):
        return 0.5/(tan(self.HVOF/2) * self.pixheight/self.pixwidth)
