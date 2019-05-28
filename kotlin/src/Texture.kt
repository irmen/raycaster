package net.razorvine.raycaster

import java.awt.Color
import java.awt.image.BufferedImage
import java.io.FileInputStream
import java.io.InputStream
import java.lang.IllegalArgumentException
import javax.imageio.ImageIO


class Texture(private val image: BufferedImage) {
    companion object {
        const val SIZE = 64

        fun fromFile(name: String): Texture {
            val stream = FileInputStream(name)
            stream.use { return fromStream(stream) }
        }

        fun fromStream(stream: InputStream): Texture {
            val image = ImageIO.read(stream)
            val image2 = BufferedImage(image.width, image.height, BufferedImage.TYPE_INT_ARGB)
            image2.graphics.drawImage(image, 0, 0, null)
            return Texture(image2)
        }
    }

    init {
        if (image.width != SIZE || image.height != SIZE)
            throw IllegalArgumentException("texture is not ${SIZE}x$SIZE")
    }

    /**
     * Sample a texture color at the given coordinates, normalized 0.0 ... 0.999999999, wrapping around
     */
    fun sample(x: Double, y: Double): Color {
        var xi = x % 1.0
        if (xi < 0) xi += 1.0
        var yi = y % 1.0
        if (yi < 0) yi += 1.0
        return Color(image.getRGB((SIZE * xi).toInt(), (SIZE * yi).toInt()))
    }

}
