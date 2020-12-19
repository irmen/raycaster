package net.razorvine.raycaster

import java.awt.Color
import java.awt.image.BufferedImage
import java.awt.image.DataBufferInt
import java.lang.Math.toRadians
import java.util.*
import java.util.concurrent.Callable
import java.util.concurrent.Executors
import kotlin.NoSuchElementException
import kotlin.math.*
import kotlin.system.measureTimeMillis


infix fun Int.fdiv(i: Int): Double = this / i.toDouble()


class RenderTimes(val wallsMs: Long, val ceilingAndFloorMs: Long, val spritesMs: Long)


class RaycasterEngine(private val pixwidth: Int, private val pixheight: Int, image: BufferedImage) {
    var HVOF = toRadians(80.0)
    var BLACK_DISTANCE = 4.5
    val USE_MULTITHREADED_RENDERING = true

    // instead of drawing pixels on the image using setRGB, we manipulate the pixel buffer directly:
    private val pixels: IntArray = (image.raster.dataBuffer as DataBufferInt).data

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
    private val zbuffer = DoubleArray(pixwidth * pixheight)
    private val textures = mapOf(
            "test" to Texture.fromFile("resources/textures/test.png"),
            "floor" to Texture.fromFile("resources/textures/floor.png"),
            "ceiling" to Texture.fromFile("resources/textures/ceiling.png"),
            "wall-bricks" to Texture.fromFile("resources/textures/wall-bricks.png"),
            "wall-stone" to Texture.fromFile("resources/textures/wall-stone.png"),
            "creature-gargoyle" to Texture.fromFile("resources/textures/gargoyle.png"),
            "creature-hero" to Texture.fromFile("resources/textures/legohero.png"),
            "treasure" to Texture.fromFile("resources/textures/treasure.png")
    )
    private val wallTextures = listOf(textures["test"], textures["wall-bricks"], textures["wall-stone"])

    private var durationWallsMs: Long = 0
    private var durationCeilingFloorMs: Long = 0
    private var durationSpritesMs: Long = 0

    val renderTimes: RenderTimes
        get() = RenderTimes(durationWallsMs, durationCeilingFloorMs, durationSpritesMs)

    private val numRenderThreads = max(1, Runtime.getRuntime().availableProcessors() / 2)
    private val renderThreadpool = Executors.newFixedThreadPool(numRenderThreads)

    fun tick(timer: Long) {
        frame++
        Arrays.fill(zbuffer, Double.POSITIVE_INFINITY)      // clear the z-buffer
        val scrDist = screenDistance()

        durationWallsMs = measureTimeMillis {
            // Cast a ray per pixel column on the screen!
            // (we end up redrawing all pixels of the screen, so no explicit clear is needed)
            // Chunks of columns can be calculated in different threads.
            val workers = (0 until pixwidth).chunked(pixwidth / numRenderThreads + 1).map { columns ->
                Callable {
                    for (x in columns) {
                        val castResult = castRayDDA(x)
                        if (castResult.distance > 0) {
                            val ceilingSize = (pixheight * (1.0 - scrDist / castResult.distance) / 2.0).toInt()
                            ceilingSizes[x] = ceilingSize
                            if (castResult.squareContents > 0)
                                drawColumn(x, ceilingSize, castResult.distance,
                                        wallTextures[castResult.squareContents]!!, castResult.textureX)
                            else
                                drawBlackColumn(x, ceilingSize, castResult.distance)
                        } else
                            ceilingSizes[x] = 0
                    }
                }
            }

            if(USE_MULTITHREADED_RENDERING)
                renderThreadpool.invokeAll(workers)
            else
                workers.forEach { it.call() }
        }

        durationCeilingFloorMs = measureTimeMillis {
            drawFloorAndCeiling(ceilingSizes, scrDist)
        }

        durationSpritesMs = measureTimeMillis {
            drawSprites(scrDist)
        }
    }

    private class RayCastResult(val squareContents: Int, val distance: Double, val textureX: Double)

    private fun castRayDDA(pixelX: Int): RayCastResult {
        // from: https://lodev.org/cgtutor/raycasting.html

        // calculate ray position and direction
        val cameraX = 2.0 * pixelX / pixwidth - 1.0   // x-coordinate in camera space
        val ray = playerDirection + cameraPlane * cameraX

        // which box of the map we're in
        var mapX = playerPosition.x.toInt()
        var mapY = playerPosition.y.toInt()

        // length of ray from one x or y-side to next x or y-side
        val deltaDistX = abs(1.0 / ray.x)
        val deltaDistY = abs(1.0 / ray.y)

        var side = false  // was a NS or a EW wall hit?
        // calculate step and initial sideDist
        // stepX,Y = what direction to step in x or y-direction (either +1 or -1)
        // sideDistX,Y = length of ray from current position to next x or y-side
        val stepX: Int
        val stepY: Int
        var sideDistX: Double
        var sideDistY: Double
        if(ray.x < 0) {
            stepX = -1
            sideDistX = (playerPosition.x - mapX) * deltaDistX
        } else {
            stepX = 1
            sideDistX = (mapX + 1.0 - playerPosition.x) * deltaDistX
        }

        if(ray.y < 0) {
            stepY = -1
            sideDistY = (playerPosition.y - mapY) * deltaDistY
        } else {
            stepY = 1
            sideDistY = (mapY + 1.0 - playerPosition.y) * deltaDistY
        }

        // perform DDA
        var wall = 0
        while(wall==0) {
            // jump to next map square, OR in x-direction, OR in y-direction, until we hit a wall
            if(sideDistX < sideDistY) {
                sideDistX += deltaDistX
                mapX += stepX
                side = false
            } else {
                sideDistY += deltaDistY
                mapY += stepY
                side = true
            }
            wall = map.getWall(mapX, mapY)
        }

        // Calculate distance of perpendicular ray (Euclidean distance will give fisheye effect!)
        val distance =
                if(side) (mapY - playerPosition.y + (1 - stepY) / 2) / ray.y
                else     (mapX - playerPosition.x + (1 - stepX) / 2) / ray.x

        return if(0 < distance && distance < BLACK_DISTANCE) {
            // calculate texture X of wall (0.0 - 1.0)
            val wallTexX =
                    if(side) playerPosition.x + distance * ray.x
                    else playerPosition.y + distance * ray.y
            // wall_tex_x -= floor(wall_tex_x)
            RayCastResult(wall, distance, wallTexX)
        } else {
            RayCastResult(-1, BLACK_DISTANCE, 0.0)
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
        // if we wanted, a simple form of "sunlight" can be added here so that not all walls have the same brightness:
        // if(side==Intersection.Top || side==Intersection.Right)  // make the sun 'shine' from bottom left
        //    brightness *= 0.75
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
        // the horizontal spans are processed with multiple concurrent threads
        // (this part of the screen drawing is the most cpu intensive)

        val mcs = ceilingSizes.maxOrNull()
        if (mcs == null || mcs <= 0)
            return
        val maxHeightPossible = (pixheight * (1.0 - screenDistance / BLACK_DISTANCE) / 2.0).toInt()

        val maxY = min(mcs, maxHeightPossible)

        if(USE_MULTITHREADED_RENDERING) {
            val workers = (0 until maxY).map { y ->
                Callable {
                    drawFloorCeilingSingleRow(y, screenDistance, ceilingSizes)
                }
            }
            renderThreadpool.invokeAll(workers)
        }
        else {
            for(y in 0 until maxY) {
                drawFloorCeilingSingleRow(y, screenDistance, ceilingSizes)
            }
        }
    }

    private fun drawFloorCeilingSingleRow(y: Int, screenDistance: Double, ceilingSizes: IntArray) {
        val ceilingTex = textures.getValue("ceiling")
        val floorTex = textures.getValue("floor")
        val sy = 0.5 - (y fdiv pixheight)
        val groundDistance = 0.5 * screenDistance / sy    // how far, horizontally over the ground, is this away from us?
        val brightness = brightness(groundDistance)
        for (x in 0 until pixwidth) {
            if (y < ceilingSizes[x] && groundDistance < zbuffer[x + y * pixwidth]) {
                val cameraPlaneRay = cameraPlane * (((x fdiv pixwidth) - 0.5) * 2.0)
                val ray = playerPosition + (playerDirection + cameraPlaneRay) * groundDistance
                // we use the fact that the ceiling and floor are mirrored
                setPixel(x, y, groundDistance, brightness, ceilingTex.sample(ray.x, ray.y))
                setPixel(x, pixheight - y - 1, groundDistance, brightness, floorTex.sample(ray.x, ray.y))
            }
        }
    }

    private fun drawSprites(d_screen: Double) {
        // every sprite is drawn as its own render worker
        if(USE_MULTITHREADED_RENDERING) {
            val workers = map.sprites.map { Callable { drawSprite(it, d_screen) } }
            renderThreadpool.invokeAll(workers)
        }
        else
            map.sprites.forEach { drawSprite(it, d_screen) }
    }

    private fun getSpriteTexture(spritetype: Char): Pair<Texture, Double> {
        return when (spritetype) {
            'g' -> Pair(textures.getValue("creature-gargoyle"), 0.8)
            'h' -> Pair(textures.getValue("creature-hero"), 0.7)
            't' -> Pair(textures.getValue("treasure"), 0.6)
            else -> throw NoSuchElementException("unknown sprite: $spritetype")
        }
    }

    private fun drawSprite(sprite: Map.Entry<Pair<Int, Int>, Char>, d_screen: Double) {
        val (mx, my) = sprite.key
        val mc = sprite.value
        val spritePos = Vec2d(mx + 0.5, my + 0.5)
        val spriteVec = spritePos - playerPosition
        val spriteDirection = spriteVec.angle()
        val spriteDistance = spriteVec.magnitude()
        var spriteViewAngle = playerDirection.angle() - spriteDirection
        if (spriteViewAngle < -PI)
            spriteViewAngle += 2.0 * PI
        else if (spriteViewAngle > PI)
            spriteViewAngle -= 2.0 * PI
        if (spriteDistance < BLACK_DISTANCE && abs(spriteViewAngle) < HVOF / 2.0) {
            val (texture, spriteSize) = getSpriteTexture(mc)
            val middlePixelColumn = ((0.5 * (spriteViewAngle / (HVOF / 2.0)) + 0.5) * pixwidth).toInt()
            val spritePerpendicularDistance = spriteDistance * cos(spriteViewAngle)
            if(spritePerpendicularDistance < 0.2)
                return
            val ceilingAboveSpriteSquare = (pixheight * (1.0 - d_screen / spritePerpendicularDistance) / 2.0).toInt()
            val brightness = brightness(spritePerpendicularDistance)
            var pixelHeight = pixheight - ceilingAboveSpriteSquare * 2
            var yOffset = ((1.0 - spriteSize) * pixelHeight).toInt() + ceilingAboveSpriteSquare
            val texYOffset = if(yOffset < 0) abs(yOffset) else 0
            yOffset = max(0, yOffset)
            pixelHeight = (spriteSize * pixelHeight).toInt()
            val pixelWidth = pixelHeight
            for (y in 0 until pixelHeight) {
                for (x in max(0, middlePixelColumn - pixelWidth / 2)
                        until min(pixwidth, middlePixelColumn + pixelWidth / 2)) {
                    val tc = texture.sample(((x - middlePixelColumn) fdiv pixelWidth) - 0.5, (y+texYOffset) fdiv pixelHeight)
                    if ((tc ushr 24) > 200)   // consider alpha channel
                        setPixel(x, y + yOffset, spritePerpendicularDistance, brightness, tc)
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
        val pixelOffset = x + y * pixwidth
        if (argb != null && z < zbuffer[pixelOffset]) {
            zbuffer[pixelOffset] = z
            if (z > 0 && brightness != 1.0) {
                pixels[pixelOffset] = colorBrightness(argb, brightness)
                //image.setRGB(x, y, colorBrightness(argb, brightness))
            } else {
                pixels[pixelOffset] = argb
                //image.setRGB(x, y, argb)
            }
        }
    }

    /**
     * adjust brightness of the color. brightness 0=pitch black, 1=normal
     * while theoretically it 's more accurate to adjust the luminosity (by doing rgb->hls->rgb),
     * it's almost as good and a lot faster to just scale the r,g,b values themselves.
     */
    private fun colorBrightness(argb: Int, brightness: Double): Int {
        val alpha = argb and -16777216
        val bri = (brightness * 256).toInt()
        val red = (argb shr 16 and 255) * bri
        val green = (argb shr 8 and 255) * bri
        val blue = (argb and 255) * bri
        return alpha or (red and 0x0000ff00 shl 8) or (green and 0x0000ff00) or (blue shr 8)
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
        if (mapSquare(x, y) == 0) {
            playerPosition = Vec2d(x, y)
            // stay a certain minimum distance from the walls
            if (mapSquare(x + 0.1, y) > 0)
                playerPosition.x = x.toInt() + 0.9
            if (mapSquare(x - 0.1, y) > 0)
                playerPosition.x = x.toInt() + 0.1
            if (mapSquare(x, y + 0.1) > 0)
                playerPosition.y = y.toInt() + 0.9
            if (mapSquare(x, y - 0.1) > 0)
                playerPosition.y = y.toInt() + 0.1
        }
    }

    fun movePlayerLeftOrRight(amount: Double) {
        val dn = playerDirection.normalized()
        val newpos = playerPosition + Vec2d(dn.y, -dn.x) * amount
        movePlayer(newpos.x, newpos.y)
    }
}
