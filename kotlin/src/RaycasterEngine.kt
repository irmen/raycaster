package net.razorvine.raycaster

import java.awt.Color
import java.awt.image.BufferedImage
import java.lang.Math.toRadians
import kotlin.math.*


// TODO possible optimization: use Graphics2d to draw the columns and scale the sprites
//      it also has to apply the brightness level to the pasted pixels somehow



infix fun Int.fdiv(i: Int): Double = this / i.toDouble()


class RaycasterEngine(private val pixwidth: Int, private val pixheight: Int, private val image: BufferedImage) {
    var HVOF = toRadians(80.0)
    var BLACK_DISTANCE = 4.0

    val map = WorldMap(listOf(
            "11111111111111111111",
            "1..................1",
            "1..111111222222.2221",
            "1.....1.....2.....t1",
            "1.g...1.gh..2..h...1",
            "1...111t....2222...1",
            "1....t1222..2......1",
            "1....g.222..2.1.2.11",
            "1.h.......s........1",
            "11111111111111111111"
    ))

    var playerPosition = Vec2d(map.playerStartX + 0.5, map.playerStartY + 0.5)
    var playerDirection = Vec2d(0, 1)
    var cameraPlane = Vec2d(tan(HVOF / 2.0), 0.0)
    private var frame = 0
    private val ceilingSizes = IntArray(pixwidth)
    private val zbuffer = List(pixwidth) { DoubleArray(pixheight) }
    private val textures = mapOf(
            "test" to Texture.fromFile("python/pyraycaster/textures/test.png"),
            "floor" to Texture.fromFile("python/pyraycaster/textures/floor.png"),
            "ceiling" to Texture.fromFile("python/pyraycaster/textures/ceiling.png"),
            "wall-bricks" to Texture.fromFile("python/pyraycaster/textures/wall-bricks.png"),
            "wall-stone" to Texture.fromFile("python/pyraycaster/textures/wall-stone.png"),
            "creature-gargoyle" to Texture.fromFile("python/pyraycaster/textures/gargoyle.png"),
            "creature-hero" to Texture.fromFile("python/pyraycaster/textures/legohero.png"),
            "treasure" to Texture.fromFile("python/pyraycaster/textures/treasure.png")
    )
    private val wallTextures = listOf(null, textures["wall-bricks"], textures["wall-stone"])


    fun tick(timer: Long) {
        clearZbuffer()
        frame++

        // cast a ray per pixel column on the screen!
        // (we end up redrawing all pixels of the screen, so no explicit clear is needed)
        val scrDist = screenDistance()
        for (x in 0 until pixwidth) {
            val (wall, distance, textureX) = castRay(x)
            if (distance > 0) {
                val ceilingSize = (pixheight * (1.0 - scrDist / distance) / 2.0).toInt()
                ceilingSizes[x] = ceilingSize
                if (wall > 0)
                    drawColumn(x, ceilingSize, distance, wallTextures[wall]!!, textureX)
                else
                    drawBlackColumn(x, ceilingSize, distance)
            } else
                ceilingSizes[x] = 0
        }
        drawFloorAndCeiling(ceilingSizes, scrDist)
        drawSprites(scrDist)
    }

    private fun castRay(pixelX: Int): Triple<Int, Double, Double> {
        // TODO more efficient xy dda algorithm: use map square dx/dy steps to hop map squares,
        //      instead of 'tracing the ray' with small steps. See https://lodev.org/cgtutor/raycasting.html
        //      and https://youtu.be/eOCQfxRQ2pY?t=6m0s
        //      That also makes the intersection test a lot simpler!?
        val cameraPlaneRay = cameraPlane * ( ((pixelX fdiv pixwidth) - 0.5) * 2.0)
        val castRay = playerDirection + cameraPlaneRay
        val stepSize = 0.02   // lower this to increase ray resolution
        val rayStep = castRay * stepSize
        var ray = playerPosition
        var distance = 0.0     // distance perpendicular to the camera view plane
        while(distance <= BLACK_DISTANCE) {
            distance += stepSize
            ray += rayStep
            val square = mapSquare(ray.x, ray.y)
            if(square>0) {
                val (tx, _) = intersectionWithMapsquareAccurate(playerPosition, ray)
                // XXX tx = intersection_with_mapsquare_fast (ray)
                return Triple(square, distance, tx)
            }
        }
        return Triple(-1, distance, 0.0)
    }

    enum class Intersection {
        Left,
        Right,
        Top,
        Bottom
    }

    /**
     * Cast_ray is the ray that we know intersects with a square.
     * This method returns (wall texture sample coordinate, Vec2(intersect x, intersect y)).
     */
    private fun intersectionWithMapsquareAccurate(camera: Vec2d, cast_ray: Vec2d): Pair<Double, Vec2d> {
        // Note: this method is a bit slow, but very accurate.
        // It always determines the correct quadrant/edge that is intersected,
        // and calculates the texture sample coordinate based off the actual intersection point
        // of the cast camera ray with that square's edge.
        // We now first determine what quadrant of the square the camera is looking at,
        // and based on the relative angle with the vertex, what edge of the square.
        val intersects: Intersection
        val direction = cast_ray - camera
        val squareCenter = Vec2d(cast_ray.x.toInt() + 0.5, cast_ray.y.toInt() + 0.5)
        if(camera.x < squareCenter.x) {
            // left half of square
            intersects = if(camera.y < squareCenter.y) {
                val vertexAngle = ((squareCenter + Vec2d(-0.5, -0.5)) - camera).angle()
                if (direction.angle() < vertexAngle) Intersection.Bottom else Intersection.Left
            } else {
                val vertexAngle = ((squareCenter + Vec2d(-0.5, 0.5)) - camera).angle()
                if (direction.angle() < vertexAngle) Intersection.Left else Intersection.Top
            }
        } else {
            // right half of square (need to flip some X's because of angle sign issue)
            if(camera.y < squareCenter.y) {
                val vertex = ((squareCenter + Vec2d(0.5, -0.5)) - camera)
                vertex.x = -vertex.x
                val posDir = Vec2d(-direction.x, direction.y)
                intersects = if(posDir.angle() < vertex.angle()) Intersection.Bottom else Intersection.Right
            } else {
                val vertex = ((squareCenter + Vec2d(0.5, 0.5)) - camera)
                vertex.x = -vertex.x
                val posDir = Vec2d(-direction.x, direction.y)
                intersects = if(posDir.angle() < vertex.angle()) Intersection.Right else Intersection.Top
            }
        }
        // now calculate the exact x (and y) coordinates of the intersection with the square's edge
        when (intersects) {
            Intersection.Top -> {
                val iy = squareCenter.y + 0.5
                val ix = if (direction.y == 0.0) 0.0 else camera.x + (iy - camera.y) * direction.x / direction.y
                return Pair(-ix, Vec2d(ix, iy))
            }
            Intersection.Bottom -> {
                val iy = squareCenter.y - 0.5
                val ix = if (direction.y == 0.0) 0.0 else camera.x + (iy - camera.y) * direction.x / direction.y
                return Pair(ix, Vec2d(ix, iy))
            }
            Intersection.Left -> {
                val ix = squareCenter.x - 0.5
                val iy = if (direction.x == 0.0) 0.0 else camera.y + (ix - camera.x) * direction.y / direction.x
                return Pair(-iy, Vec2d(ix, iy))
            }
            Intersection.Right -> {
                val ix = squareCenter.x + 0.5
                val iy = if (direction.x == 0.0) 0.0 else camera.y + (ix - camera.x) * direction.y / direction.x
                return Pair(iy, Vec2d(ix, iy))
            }
        }
    }

    private fun mapSquare(x: Double, y: Double): Int {
        val mx = x.toInt()
        val my = y.toInt()
        if (mx in 0..map.width && my in 0..map.height)
            return map.getWall(mx, my)
        return 255
    }

    private fun drawColumn(x: Int, ceiling: Int, distance: Double, texture: Texture, tx: Double) {
        val startY = max(0, ceiling)
        val numPixels = pixheight - 2 * startY
        val wallHeight = pixheight - 2 * ceiling
        val brightness = brightness(distance)      // the whole column has the same brightness value
        for (y in startY until startY + numPixels)
            setPixel(x, y, distance, brightness, texture.sample(tx, (y - ceiling) fdiv wallHeight))
    }

    private fun drawBlackColumn(x: Int, ceiling: Int, distance: Double) {
        val startY = max(0, ceiling)
        val numPixels = pixheight - 2 * startY
        for (y in startY until startY + numPixels)
            setPixel(x, y, distance, 1.0, Color.BLACK.rgb)
    }

    private fun drawFloorAndCeiling(ceilingSizes: IntArray, screenDistance: Double) {
        val mcs = ceilingSizes.max()
        if (mcs == null || mcs <= 0)
            return
        val maxHeightPossible = (pixheight * (1.0 - screenDistance / BLACK_DISTANCE) / 2.0).toInt()
        val ceilingTex = textures.getValue("ceiling")
        val floorTex = textures.getValue("floor")
        for (y in 0 until min(mcs, maxHeightPossible)) {
            val sy = 0.5 - (y fdiv pixheight)
            val groundDistance = 0.01 + 0.5 * screenDistance / sy    // how far, horizontally over the ground, is this away from us?
            // the 0.01 is there to adjust for a tiny perspective issue that I can't explain mathematically,
            // but it's there visually; the floor texture edges don't quite line up with the walls somehow, without it.
            val brightness = brightness(groundDistance)
            for ((x, h) in ceilingSizes.withIndex()) {
                if (y < h && groundDistance<zbuffer[x][y]) {
                    val cameraPlaneRay = cameraPlane * (((x fdiv pixwidth) - 0.5) * 2.0)
                    val ray = playerPosition + (playerDirection + cameraPlaneRay) * groundDistance
                    // we use the fact that the ceiling and floor are mirrored
                    setPixel(x, y, groundDistance, brightness, ceilingTex.sample(ray.x, -ray.y))
                    setPixel(x, pixheight - y - 1, groundDistance, brightness, floorTex.sample(ray.x, -ray.y))
                }
            }
        }
    }

    private fun drawSprites(d_screen: Double) {
        map.sprites.forEach {
            val (mx, my) = it.key
            val mc = it.value
            val spritePos = Vec2d(mx + 0.5, my + 0.5)
            val spriteVec = spritePos - playerPosition
            val spriteDirection = spriteVec.angle()
            val spriteDistance = spriteVec.magnitude()
            var spriteViewAngle = playerDirection.angle() - spriteDirection
            if(spriteViewAngle < -PI)
                spriteViewAngle += 2.0*PI
            else if(spriteViewAngle > PI)
                spriteViewAngle -= 2.0*PI
            if(spriteDistance < BLACK_DISTANCE && abs(spriteViewAngle) < HVOF/2.0) {
                val spriteSize: Double
                val texture: Texture
                when (mc) {
                    'g' -> {
                        texture = textures.getValue("creature-gargoyle")
                        spriteSize = 0.8
                    }
                    'h' -> {
                        texture = textures.getValue("creature-hero")
                        spriteSize = 0.7
                    }
                    't' -> {
                        texture = textures.getValue("treasure")
                        spriteSize = 0.6
                    }
                    else -> throw NoSuchElementException("unknown sprite: $mc")
                }
                val middlePixelColumn = ((0.5*(spriteViewAngle/(HVOF/2.0))+0.5) * pixwidth).toInt()
                val spritePerpendicularDistance = spriteDistance * cos(spriteViewAngle)
                var ceilingAboveSpriteSquare = (pixheight * (1.0 - d_screen / spritePerpendicularDistance) / 2.0).toInt()
                if(ceilingAboveSpriteSquare >= 0) {
                    val brightness = brightness(spritePerpendicularDistance)
                    var pixelHeight = pixheight - ceilingAboveSpriteSquare*2
                    val y_offset = ((1.0-spriteSize) * pixelHeight).toInt()
                    ceilingAboveSpriteSquare += y_offset
                    pixelHeight = (spriteSize * pixelHeight).toInt()
                    val pixelWidth = pixelHeight
                    for(y in 0 until pixelHeight) {
                        for(x in max(0, middlePixelColumn - pixelWidth/2)
                                until min(pixwidth, middlePixelColumn + pixelWidth/2)) {
                            val tc = texture.sample(((x-middlePixelColumn) fdiv pixelWidth) - 0.5, y fdiv pixelHeight)
                            if((tc ushr 24) > 200)   // consider alpha channel
                                setPixel(x, y + ceilingAboveSpriteSquare, spritePerpendicularDistance, brightness, tc)
                        }
                    }
                }
            }
        }
    }

    private fun brightness(distance: Double) = max(0.0, 1.0 - distance / BLACK_DISTANCE)

    /**
     * Sets a pixel on the screen (if it is visible) and adjusts its z-buffer value.
     * The pixel's brightness is adjusted as well.
     * If argb is None, the pixel is transparent instead of having a color.
     */
    private fun setPixel(x: Int, y: Int, z: Double, brightness: Double, argb: Int?) {
        if (argb!=null && z < zbuffer[x][y]) {
            zbuffer[x][y] = z
            if (z > 0 && brightness != 1.0) {
                image.setRGB(x, y, colorBrightness(argb, brightness))
            } else {
                image.setRGB(x, y, argb)
            }

            // note: slightly faster may be to directly operate on the pixel buffer;
            // add as a property on this class: val pixels = (image.raster.dataBuffer as DataBufferInt).data
            // then here: pixels[x+y*pixwidth] = argb     instead of the setRGB()
        }
    }

    /**
     * adjust brightness of the color. brightness 0=pitch black, 1=normal
     * while theoretically it 's more accurate to adjust the luminosity (by doing rgb->hls->rgb),
     * it's almost as good and a lot faster to just scale the r,g,b values themselves.
     */
    private fun colorBrightness(argb: Int, brightness: Double): Int {
        val alpha = argb and 0xff000000.toInt()
        val red = (argb shr 16 and 255) * brightness
        val green = (argb shr 8 and 255) * brightness
        val blue = (argb and 255) * brightness
        return alpha or (red.toInt() shl 16) or (green.toInt() shl 8) or (blue.toInt())
    }

    private fun clearZbuffer() {
        for (x in 0 until pixwidth) {
            for (y in 0 until pixheight) {
                zbuffer[x][y] = Double.POSITIVE_INFINITY
            }
        }
    }

    private fun screenDistance() = 0.5 / (tan(HVOF / 2.0) * pixheight / pixwidth)

    fun rotatePlayer(angle: Double) {
        val newAngle = playerDirection.angle() + angle
        rotatePlayerTo(newAngle)
    }

    fun rotatePlayerTo(angle: Double) {
        playerDirection = Vec2d.fromAngle(angle)
        cameraPlane = Vec2d.fromAngle(angle - PI / 2.0) * tan(HVOF / 2.0)
    }

    fun setFov(fov: Double) {
        HVOF = fov
        rotatePlayer(0.0)
    }

    fun movePlayerForwardOrBack(amount: Double) {
        val newpos = playerPosition + playerDirection.normalized() * amount
        movePlayer(newpos.x, newpos.y)
    }

    private fun movePlayer(x: Double, y: Double) {
        if(mapSquare(x, y) == 0) {
            playerPosition = Vec2d(x, y)
            // stay a certain minimum distance from the walls
            if(mapSquare(x + 0.1, y)>0)
                playerPosition.x = x.toInt() + 0.9
            if(mapSquare(x - 0.1, y)>0)
                playerPosition.x = x.toInt() + 0.1
            if(mapSquare(x, y + 0.1)>0)
                playerPosition.y = y.toInt() + 0.9
            if(mapSquare(x, y - 0.1)>0)
                playerPosition.y = y.toInt() + 0.1
        }
    }

    fun movePlayerLeftOrRight(amount: Double) {
        val dn = playerDirection.normalized()
        val newpos = playerPosition + Vec2d(dn.y, -dn.x) * amount
        movePlayer(newpos.x, newpos.y)
    }
}
