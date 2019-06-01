package net.razorvine.raycaster

import java.awt.image.BufferedImage
import java.awt.image.DataBufferInt
import java.io.FileInputStream
import java.io.InputStream
import java.lang.IllegalArgumentException
import javax.imageio.ImageIO


class Texture(image: BufferedImage) {
    companion object {
        const val SIZE = 64         // must be a power of 2 because of efficient coordinate wrapping

        fun fromFile(name: String): Texture {
            val stream = FileInputStream(name)
            stream.use { return fromStream(stream) }
        }

        fun fromStream(stream: InputStream): Texture {
            val image = ImageIO.read(stream)
            val image2 = BufferedImage(image.width, image.height, BufferedImage.TYPE_INT_ARGB).also {it.accelerationPriority=0.9f}
            image2.graphics.drawImage(image, 0, 0, null)
            return Texture(image2)
        }
    }

    private val pixels: IntArray

    init {
        if (image.width != SIZE || image.height != SIZE)
            throw IllegalArgumentException("texture is not ${SIZE}x$SIZE")

        // instead of drawing pixels on the image using setRGB, we manipulate the pixel buffer directly:
        pixels = (image.raster.dataBuffer as DataBufferInt).data
    }

    /**
     * Sample a texture color at the given coordinates, normalized 0.0 ... 0.999999999, wrapping around
     */
    fun sample(x: Double, y: Double): Int {
        val xi = (x*SIZE).toInt() and (SIZE-1)
        val yi = (y*SIZE).toInt() and (SIZE-1)
        return pixels[xi + yi*SIZE]
    }

}
