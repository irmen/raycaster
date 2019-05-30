package net.razorvine.raycaster


class WorldMap(mapdef: List<String>) {
    val width = mapdef[0].length
    val height = mapdef.size
    var playerStartX: Int = 1
    var playerStartY: Int = 1
    val sprites: MutableMap<Pair<Int, Int>, Char> = mutableMapOf()
    private val map: MutableList<IntArray> = mutableListOf()

    init {
        val revmap = mapdef.asReversed()  // flip the Y axis so (0,0) is at bottom left
        revmap.withIndex().forEach {
            for(x in 0 until width) {
                if(it.value[x] == 's') {
                    playerStartX = x
                    playerStartY = it.index
                }
                else if(it.value[x] in "ght") {
                    sprites[Pair(x, it.index)] = it.value[x]
                }
            }
        }
        revmap.forEach {
            map.add( it.map { c->if(c in '0'..'9') c.toByte()-48 else 0 }.toIntArray() )
        }
    }

    /**
     * Get the wall in the world map at integer coordinate (x, y)
     */
    fun getWall(x: Int, y: Int) = map[y][x]
}
