package net.razorvine.raycaster

import java.awt.*
import java.awt.event.KeyEvent
import java.awt.event.MouseEvent
import java.awt.image.BufferedImage
import javax.swing.JFrame
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.event.MouseInputAdapter
import kotlin.math.PI
import kotlin.math.max
import kotlin.math.min


class RaycasterGui {
    companion object {
        const val PIXEL_WIDTH = 800
        const val PIXEL_HEIGHT = 480
        const val PIXEL_SCALE = 2
    }

    private val image = BufferedImage(PIXEL_WIDTH, PIXEL_HEIGHT, BufferedImage.TYPE_INT_RGB).also {it.accelerationPriority=1.0f}
    private val engine = RaycasterEngine(PIXEL_WIDTH, PIXEL_HEIGHT, image)
    private val minimap = MinimapCanvas(engine.map, 3)
    private val window = Window("Kotlin Raycaster", minimap, image, engine)
    private val desiredRefreshRate: Int by lazy {
        var defaultRefreshRate = GraphicsEnvironment.getLocalGraphicsEnvironment().defaultScreenDevice.displayMode.refreshRate
        if(defaultRefreshRate==0)
            defaultRefreshRate = GraphicsEnvironment.getLocalGraphicsEnvironment().screenDevices.map { it.displayMode.refreshRate }.first { it>0 }
        max(30, min(150, defaultRefreshRate))
    }

    init {
        val gameThread = Thread {
            val timeEpoch = System.currentTimeMillis()
            var lastTime = timeEpoch
            var frame = 0L
            while(true) {
                val curTime = System.currentTimeMillis()
                if((curTime-lastTime) >= (1000/desiredRefreshRate)) {
                    frame++
                    lastTime = curTime
                    tick(curTime-timeEpoch, frame)
                }
                Thread.sleep(1)
            }
        }
        gameThread.start()
    }

    private class PixelCanvas(private val image: BufferedImage) : JPanel() {
        init {
            size = Dimension(PIXEL_WIDTH * PIXEL_SCALE, PIXEL_HEIGHT * PIXEL_SCALE)
            preferredSize = Dimension(PIXEL_WIDTH * PIXEL_SCALE, PIXEL_HEIGHT * PIXEL_SCALE)
        }

        override fun paint(graphics: Graphics?) {
            val gfx2d = graphics as Graphics2D
            gfx2d.background = Color.PINK
            gfx2d.color = Color.GREEN
            gfx2d.drawImage(image, 0, 0, PIXEL_WIDTH * PIXEL_SCALE, PIXEL_HEIGHT * PIXEL_SCALE, this)
        }
    }


    private class MinimapCanvas(private val map: WorldMap, var viewDistance: Int) : JPanel() {

        companion object {
            const val SCALE = 20
            val squareColors = mapOf(
                    0 to Color.BLACK,
                    1 to Color.BLUE,
                    2 to Color.RED,
                    3 to Color.GREEN,
                    4 to Color.MAGENTA,
                    5 to Color.YELLOW,
                    6 to Color.PINK,
                    7 to Color.ORANGE,
                    8 to Color.CYAN,
                    9 to Color.WHITE
            )
        }

        private var playerLocation = Vec2d(1.5, 1.5)
        private var playerDirection = Vec2d(0, 1)
        private var cameraPlane = Vec2d(1, 0)
        private val scrWidth = map.width * SCALE
        private val scrHeight = map.height * SCALE

        init {
            preferredSize = Dimension(scrWidth, scrHeight)
        }

        override fun paint(g: Graphics) {
            val g2 = g as Graphics2D

            // note that the Y axis of the canvas is inverted!
            // draw the map.
            g2.background = Color.BLACK
            g2.color = Color.YELLOW
            g2.clearRect(0, 0, width, height)
            for (x in 0 until map.width) {
                for (y in 0 until map.height) {
                    val wall = map.getWall(x, map.height - y - 1)
                    g2.color = squareColors[wall]
                    g2.fillRect(x * SCALE, y * SCALE, SCALE - 1, SCALE - 1)
                    if (Pair(x, map.height - y - 1) in map.sprites) {
                        g2.color = Color.ORANGE
                        g2.fillOval(x * SCALE + SCALE / 4, y * SCALE + SCALE / 4, SCALE / 2, SCALE / 2)
                    }
                }
            }

            // draw the camera view triangle
            val scrLocation = playerLocation * SCALE
            g2.color = Color.LIGHT_GRAY
            g2.fillOval(scrLocation.x.toInt() - SCALE / 4, scrHeight - scrLocation.y.toInt() - SCALE / 4, SCALE / 2, SCALE / 2)
            val angle = playerLocation + playerDirection * viewDistance
            val scrAngle = angle * SCALE
            g2.color = Color.DARK_GRAY
            g2.drawLine(scrLocation.x.toInt(), scrHeight - scrLocation.y.toInt(), scrAngle.x.toInt(), scrHeight - scrAngle.y.toInt())
            val poly = Polygon()
            for (vertex in listOf(
                    playerLocation,
                    playerLocation + (playerDirection + cameraPlane) * viewDistance,
                    playerLocation + (playerDirection - cameraPlane) * viewDistance)) {
                val s = vertex * SCALE
                poly.addPoint(s.x.toInt(), scrHeight - s.y.toInt())
            }
            g2.color = Color.GRAY
            g2.drawPolygon(poly)
        }

        fun movePlayer(location: Vec2d, direction: Vec2d, camera_plane: Vec2d) {
            this.playerLocation = location
            this.playerDirection = direction
            this.cameraPlane = camera_plane
        }
    }


    private class Window(title: String, val minimap: MinimapCanvas, image: BufferedImage, val engine: RaycasterEngine) : JFrame(title) {
        private val canvas = PixelCanvas(image)
        private val fpsLabel = JLabel("frame counter here").also { it.foreground = Color.GRAY; it.font=Font("Monospaced", Font.PLAIN, 12) }

        init {
            layout = BorderLayout(0, 0)
            defaultCloseOperation = EXIT_ON_CLOSE
            add(canvas, BorderLayout.CENTER)
            val bottomframe = JPanel().also {it.background=Color.BLACK}
            bottomframe.add(minimap)
            bottomframe.add(JLabel("<html>Controls:<br>w,s,a,d - movement<br>q,e - rotation<br>mouse - rotation<br>left button - move (fine)</html>").also{ it.foreground=Color.LIGHT_GRAY})
            bottomframe.add(fpsLabel)
            add(bottomframe, BorderLayout.PAGE_END)
            minimap.movePlayer(engine.playerPosition, engine.playerDirection, engine.cameraPlane)
            pack()
            setLocationRelativeTo(null)
            isVisible = true

            addMouseMotionListener(MouseListener(this))
            addMouseListener(MouseListener(this))
            addKeyListener(KeyListener(this))
        }

        fun updateGraphics(timer: Long, frame: Long, renderTimes: RenderTimes) {
            if(timer>0) {
                // calc and show fps
                val fps = frame.toDouble() / timer * 1000.0
                fpsLabel.text = "<html>average fps:  ${fps.toInt()}<br><br>" +
                        "&nbsp;  walls:  ${renderTimes.wallsMs} ms<br>" +
                        "&nbsp;  ceiling&floor:  ${renderTimes.ceilingAndFloorMs} ms<br>" +
                        "&nbsp;  sprites:  ${renderTimes.spritesMs} ms</html>"
            }
            canvas.repaint()
            minimap.repaint()
            // Toolkit.getDefaultToolkit().sync()
        }

        var mouseButtonDown = false
        var keysPressed = mutableSetOf<Char>()

        class KeyListener(val parent: Window) : java.awt.event.KeyListener {
            override fun keyTyped(e: KeyEvent) {}

            override fun keyPressed(e: KeyEvent) {
                parent.keysPressed.add(e.keyChar)
            }

            override fun keyReleased(e: KeyEvent) {
                parent.keysPressed.remove(e.keyChar)
            }
        }


        private class MouseListener(val parent: Window) : MouseInputAdapter() {
            override fun mouseDragged(e: MouseEvent) = parent.mousePos(e.x, e.y, e.xOnScreen, e.yOnScreen)
            override fun mouseMoved(e: MouseEvent) = parent.mousePos(e.x, e.y, e.xOnScreen, e.yOnScreen)
            override fun mousePressed(e: MouseEvent) {
                parent.mouseButtonDown = true
            }
            override fun mouseReleased(e: MouseEvent) {
                parent.mouseButtonDown = false
            }
        }

        fun mousePos(mouseX: Int, mouseY: Int, absx: Int, absy: Int) {
            val x = mouseX - width/2
            engine.rotatePlayerTo(PI / 2.0 + 2.0 * PI * -x / 1200.0)
        }

    }


    private fun tick(timer: Long, frame: Long) {
        // process inputs
        if(window.mouseButtonDown)
            engine.movePlayerForwardOrBack(0.01)
        if('w' in window.keysPressed)
            engine.movePlayerForwardOrBack(0.03)
        if('s' in window.keysPressed)
            engine.movePlayerForwardOrBack(-0.03)
        if('a' in window.keysPressed)
            engine.movePlayerLeftOrRight(-0.03)
        if('d' in window.keysPressed)
            engine.movePlayerLeftOrRight(0.03)
        if('q' in window.keysPressed)
            engine.rotatePlayer(PI/120.0)
        if('e' in window.keysPressed)
            engine.rotatePlayer(-PI/120.0)

        engine.tick(timer)
        minimap.movePlayer(engine.playerPosition, engine.playerDirection, engine.cameraPlane)
        window.updateGraphics(timer, frame, engine.renderTimes)
    }

}
