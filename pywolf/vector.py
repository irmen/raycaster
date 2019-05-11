from math import sin, cos, atan2, sqrt


class Vec2:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def from_angle(cls, radians):
        return cls(cos(radians), sin(radians))

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __abs__(self):
        return self.magnitude()

    def magnitude(self):
        return sqrt(self.x*self.x + self.y*self.y)

    def normalized(self):
        if self.x == 0 and self.y == 0:
            return self
        mag = self.magnitude()
        return Vec2(self.x / mag, self.y / mag)

    def angle(self):
        return atan2(self.y, self.x)

    def __neg__(self):
        return Vec2(-self.x, -self.y)

    def __add__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x+other.x, self.y+other.y)
        else:
            raise TypeError("can only add another Vec2d", other)

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Vec2):
            return Vec2(self.x-other.x, self.y-other.y)
        else:
            raise TypeError("can only sub another Vec2d", other)

    def __mul__(self, scalar):
        return Vec2(self.x*scalar, self.y*scalar)

    def __rmul__(self, scalar):
        return Vec2(self.x*scalar, self.y*scalar)

    def __truediv__(self, scalar):
        return Vec2(self.x/scalar, self.y/scalar)

    def dotproduct(self, other):
        return self.x*other.x + self.y*other.y

    def rotate(self, radians):
        x2 = self.x * cos(radians) - self.y * sin(radians)
        y2 = self.y * cos(radians) + self.x * sin(radians)
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


