package net.razorvine

import java.awt.image.BufferedImage


class RaycasterEngine(val width: Int, val height: Int, private val image: BufferedImage) {
    var number = 0
    val alpha = 0xff000000.toInt()

    fun tick() {
        number++
        for (x in 0 until RaycasterGui.PIXELWIDTH) {
            for(y in 0 until RaycasterGui.PIXELHEIGHT) {
                image.setRGB(x, y, alpha or x*y*number)
            }
        }
    }

    fun mousePos(x: Int, y: Int, absx: Int, absy: Int) {
        println(" ${x}, ${y}  -   ${absx}, ${absy}")    // TODO
    }

}
