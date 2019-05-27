package net.razorvine.raycaster
import kotlin.math.*


class Vec2d(var x: Double, var y: Double) {
    constructor(x: Int, y: Int) : this(x.toDouble(), y.toDouble())

    companion object {
        fun fromAngle(radians: Double): Vec2d = Vec2d(cos(radians), sin(radians))
    }

    override fun toString() = "($x, $y)"

    fun magnitude() = sqrt(x*x + y*y)

    fun normalized(): Vec2d {
        if(x==0.0 && y==0.0)
            return this
        val mag = magnitude()
        return Vec2d(x / mag, y / mag)
    }

    fun angle() = atan2(y, x)
    fun dotproduct(other: Vec2d) = x*other.x + y*other.y

    fun rotate(angle: Double) {
        val x2 = x * cos(angle) - y * sin(angle)
        val y2 = y * cos(angle) + x * sin(angle)
        x = x2
        y = y2
    }

    operator fun unaryMinus() = Vec2d(-x, -y)
    operator fun times(scalar: Double) = Vec2d(x * scalar, y * scalar)
    operator fun div(scalar: Double) = Vec2d(x / scalar, y / scalar)
    operator fun plus(other: Vec2d) = Vec2d(x + other.x, y + other.y)
    operator fun minus(other: Vec2d) = Vec2d(x - other.x, y - other.y)

}
