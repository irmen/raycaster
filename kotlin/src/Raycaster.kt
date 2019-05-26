package net.razorvine

import java.awt.*
import java.awt.event.KeyEvent
import java.awt.event.MouseEvent
import java.awt.event.MouseMotionListener
import java.awt.image.BufferedImage
import java.util.*
import javax.swing.JFrame
import javax.swing.JLabel
import javax.swing.JPanel


class RaycasterGui {

    companion object {
        const val PIXELWIDTH = 320
        const val PIXELHEIGHT = 200
        const val PIXEL_SCALE = 4
    }

    init {
        val image = BufferedImage(PIXELWIDTH, PIXELHEIGHT, BufferedImage.TYPE_INT_ARGB)
        val engine = RaycasterEngine(PIXELWIDTH, PIXELHEIGHT, image)
        val window = Window("Kotlin Raycaster", image, engine)
        Timer("draw timer", true).scheduleAtFixedRate(DrawTask(window, engine), 10, 1000 / 60)
    }

    private class PixelCanvas(private val image: BufferedImage) : JPanel(true) {
        init {
            size = Dimension(PIXELWIDTH* PIXEL_SCALE, PIXELHEIGHT* PIXEL_SCALE)
            preferredSize = Dimension(PIXELWIDTH* PIXEL_SCALE, PIXELHEIGHT* PIXEL_SCALE)
        }

        override fun paint(graphics: Graphics?) {
            val gfx2d = graphics as Graphics2D
            gfx2d.background = Color.PINK
            gfx2d.color = Color.GREEN
            gfx2d.drawImage(image, 0, 0, PIXELWIDTH* PIXEL_SCALE, PIXELHEIGHT* PIXEL_SCALE, this)
        }
    }

    private class Window(title: String, image: BufferedImage, engine: RaycasterEngine) : JFrame(title) {
        private var frame = 0
        private val canvas = PixelCanvas(image)
        private val label = JLabel()

        init {
            layout = BorderLayout(0, 0)
            defaultCloseOperation = EXIT_ON_CLOSE
            add(label, BorderLayout.PAGE_START)
            add(canvas, BorderLayout.CENTER)
            pack()
            setLocationRelativeTo(null)
            isVisible = true

            addMouseMotionListener(MouseListener(engine))
            addKeyListener(KeyListener(engine))
        }

        fun nextFrame() {
            frame++
            label.text = "frame $frame"
            canvas.repaint()
            Toolkit.getDefaultToolkit().sync()
        }

        class KeyListener(val engine: RaycasterEngine) : java.awt.event.KeyListener {
            override fun keyTyped(e: KeyEvent) {}

            override fun keyPressed(e: KeyEvent) {
                println("pressed: $e")  // TODO
            }

            override fun keyReleased(e: KeyEvent) {
                println("released: $e") // TODO
            }
        }

        class MouseListener(val engine: RaycasterEngine) : MouseMotionListener {
            override fun mouseDragged(e: MouseEvent) = engine.mousePos(e.x, e.y, e.xOnScreen, e.yOnScreen)
            override fun mouseMoved(e: MouseEvent) = engine.mousePos(e.x, e.y, e.xOnScreen, e.yOnScreen)
        }
    }

    private class DrawTask(private val window: Window, private val engine: RaycasterEngine) : TimerTask() {
        override fun run() {
            engine.tick()
            window.nextFrame()
        }
    }
}

fun main() {
    javax.swing.SwingUtilities.invokeLater {
        RaycasterGui()
    }
}
