package net.razorvine.raycaster

import java.awt.image.BufferedImage


class RaycasterEngine(val width: Int, val height: Int, private val image: BufferedImage) {
    var number = 0
    val alpha = 0xff000000.toInt()

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

    var player_position = Vec2d(map.playerStartX, map.playerStartY)

    val textures = mapOf(
        "test" to Texture.fromFile("python/pyraycaster/textures/test.png"),
        "floor" to Texture.fromFile("python/pyraycaster/textures/floor.png"),
        "ceiling" to Texture.fromFile("python/pyraycaster/textures/ceiling.png"),
        "wall-bricks" to Texture.fromFile("python/pyraycaster/textures/wall-bricks.png"),
        "wall-stone" to Texture.fromFile("python/pyraycaster/textures/wall-stone.png"),
        "creature-gargoyle" to Texture.fromFile("python/pyraycaster/textures/gargoyle.png"),
        "creature-hero" to Texture.fromFile("python/pyraycaster/textures/legohero-small.png"),
        "treasure" to Texture.fromFile("python/pyraycaster/textures/treasure.png")
    )


    fun tick() {
        number++
        for (x in 0 until RaycasterGui.PIXEL_WIDTH) {
            for(y in 0 until RaycasterGui.PIXEL_HEIGHT) {
                image.setRGB(x, y, alpha or x*y*number)
            }
        }

        image.graphics.drawImage(textures["creature-gargoyle"]?.image, 0, 0, null)
        image.graphics.drawImage(textures["creature-hero"]?.image, 0, Texture.SIZE, null)
        image.graphics.drawImage(textures["treasure"]?.image, Texture.SIZE, Texture.SIZE, null)
    }

    fun mousePos(x: Int, y: Int, absx: Int, absy: Int) {
        println(" ${x}, ${y}  -   ${absx}, ${absy}")    // TODO
    }

}
