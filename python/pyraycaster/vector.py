from math import sin, cos, atan2, sqrt


class Vec2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    @classmethod
    def from_angle(cls, radians: float) -> "Vec2":
        return cls(cos(radians), sin(radians))

    def __str__(self) -> str:
        return f"({self.x}, {self.y})"

    def __abs__(self) -> float:
        return self.magnitude()

    def magnitude(self) -> float:
        return sqrt(self.x*self.x + self.y*self.y)

    def normalized(self) -> "Vec2":
        if self.x == 0 and self.y == 0:
            return self
        mag = self.magnitude()
        return Vec2(self.x / mag, self.y / mag)

    def angle(self) -> float:
        return atan2(self.y, self.x)

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def __add__(self, other: "Vec2") -> "Vec2":
        if isinstance(other, Vec2):
            return Vec2(self.x+other.x, self.y+other.y)
        else:
            raise TypeError("can only add another Vec2d", other)

    def __sub__(self, other: "Vec2") -> "Vec2":
        if isinstance(other, Vec2):
            return Vec2(self.x-other.x, self.y-other.y)
        else:
            raise TypeError("can only sub another Vec2d", other)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x*scalar, self.y*scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x*scalar, self.y*scalar)

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x/scalar, self.y/scalar)

    def dotproduct(self, other: "Vec2") -> float:
        return self.x*other.x + self.y*other.y

    def rotate(self, angle: float) -> None:
        x2 = self.x * cos(angle) - self.y * sin(angle)
        y2 = self.y * cos(angle) + self.x * sin(angle)
        self.x = x2
        self.y = y2


if __name__ == "__main__":
    v = Vec2(1, 2)
    v.x = 10
    v.y = 22
    print(v)
    print(-v)
    print(v.x)
    print(v.y)
    print(v.magnitude())
    print(abs(v))
    v = v.normalized()
    print(v)
    print(abs(v))
    v2 = v * 2.5
    print(v2)
    v2 = 2.5 * v
    print(v2)
    v *= 2.5
    print(v)
    v2 = v / 3.3
    print(v2)
    v /= 3.3
    print(v)
    v = v + v
    v += v
    v = v - v
    v -= v
    v = -v
    v1 = Vec2(2, -5)
    v2 = Vec2(0, 4)
    v3 = Vec2(-3, 1)
    print(v1.dotproduct(v3))
    print(v3.dotproduct(v2))
    from math import pi
    v2 = Vec2(1, 0)
    print(v2)
    v2.rotate(pi/4)
    print(v2)
    v2.rotate(pi)
    print(v2)
