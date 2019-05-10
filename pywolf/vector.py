from math import sin, cos


class Vec2:
    def __init__(self, x, y):
        self.xy = complex(x, y)

    @classmethod
    def fromcomplex(cls, cplx):
        return cls(cplx.real, cplx.imag)

    def __str__(self):
        return f"({self.xy.real}, {self.xy.imag})"

    def __abs__(self):
        return abs(self.xy)

    def magnitude(self):
        return abs(self.xy)

    def normalized(self):
        return self.fromcomplex(self.xy / abs(self.xy))

    @property
    def x(self):
        return self.xy.real

    @x.setter
    def x(self, value):
        self.xy = complex(value, self.xy.imag)

    @property
    def y(self):
        return self.xy.imag

    @y.setter
    def y(self, value):
        self.xy = complex(self.xy.real, value)

    def __add__(self, other):
        if isinstance(other, Vec2):
            return self.fromcomplex(self.xy + other.xy)
        else:
            raise TypeError("can only add another Vec2d")

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        if isinstance(other, Vec2):
            return self.fromcomplex(self.xy - other.xy)
        else:
            raise TypeError("can only sub another Vec2d")

    def __rsub__(self, other):
        return (-self) + other

    def __mul__(self, scalar):
        return self.fromcomplex(self.xy * scalar)

    def __rmul__(self, scalar):
        return self.fromcomplex(self.xy * scalar)

    def __truediv__(self, scalar):
        return self.fromcomplex(self.xy / scalar)

    def __neg__(self):
        return self.fromcomplex(-self.xy)

    def dotproduct(self, other):
        return self.x*other.x + self.y*other.y

    def rotate(self, radians):
        x2 = self.xy.real * cos(radians) - self.xy.imag * sin(radians)
        y2 = self.xy.imag * cos(radians) + self.xy.real * sin(radians)
        self.xy = complex(x2, y2)


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
    v1=Vec2(2,-5)
    v2=Vec2(0,4)
    v3=Vec2(-3,1)
    print(v1.dotproduct(v3))
    print(v3.dotproduct(v2))
    from math import pi
    v2 = Vec2(1,0)
    print(v2)
    v2.rotate(pi/4)
    print(v2)
    v2.rotate(pi)
    print(v2)


