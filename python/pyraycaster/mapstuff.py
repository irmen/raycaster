import io
import pkgutil
from PIL import Image
from typing import Union, List, Dict, Tuple, BinaryIO


class Texture:
    SIZE = 64

    def __init__(self, image: Union[str, BinaryIO]) -> None:
        if isinstance(image, str):
            data = pkgutil.get_data(__name__, image)
            if not data:
                raise IOError("can't find texture "+image)
            image = io.BytesIO(data)
        with image, Image.open(image) as img:
            if img.size != (self.SIZE, self.SIZE):
                raise IOError(f"texture is not {self.SIZE}x{self.SIZE}")
            img = img.convert('RGBA')
            self.image = img.load()

    def sample(self, x: float, y: float) -> Tuple[int, int, int, int]:
        """Sample a texture color at the given coordinates, normalized 0.0 ... 0.999999999, wrapping around"""
        return self.image[int((x % 1.0)*self.SIZE), int((y % 1.0)*self.SIZE)]


class Map:
    def __init__(self, mapdef: List[str]) -> None:
        self.player_start = (1, 1)
        self.sprites = {}    # type: Dict[Tuple[int, int], str]
        self.width = len(mapdef[0])
        self.height = len(mapdef)
        self.map = []   # type: List[bytearray]
        mapdef = list(mapdef)
        mapdef.reverse()  # flip the Y axis so (0,0) is at bottom left
        for y, line in enumerate(mapdef):
            for x in range(self.width):
                if line[x] == 's':
                    self.player_start = x, y
                elif line[x] in "ght":
                    self.sprites[(x, y)] = line[x]
        for mapline in mapdef:
            self.map.append(bytearray([self.translate_walls(c) for c in mapline]))

    def translate_walls(self, c: str) -> int:
        if '0' <= c <= '9':
            return ord(c)-ord('0')
        return 0

    def get_wall(self, x: int, y: int) -> int:
        return self.map[y][x]
