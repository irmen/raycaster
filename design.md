# Column based Raycaster

This is an attempt at a classic '2d'-ish raycaster, drawing the screen in pixel columns.
Think oldskool original Wolfenstein.

# textures

All textures (walls, ceiling, floors) are squares of 64x64 pixels.
Could be another power of 2, but settled on 64x64 considering the display size and
the number of pixels the engine has to push.
(although Pypy comfortably reaches "playable frame rates"!)


# world coordinate system

The world is an infinite 2d plane (x,y) in *meter* units (or 'squares' if you wish)
(x,y) are coordinates on the ground plane, the fictional z coordinate
is the height above the ground.
It uses the regular mathematical axis orientation so the positive X axis is to the right,
and the positive Y axis is up.  This usually means the (0, 0) word map coordinate
corresponds to the bottom left corner in a minimap display on the screen.
The Z coordinate is not used at all because the raycaster
is only able to draw corridors that all have the same floor level and height.


# camera coordinates and viewing angle

The camera is just a 2d vector, it's viewing direction another 2d vector.
(the length of the viewing direction vector is the camera's focal length)
The 'height' of the camera is simulated in the column rasterizer phase where it
determines the height and position of the walls. Currently, the height of the
camera is exactly in the middle between ceiling and floor.
It is not possible to look up or down: you can only rotate the camera horizontally.
Focal length and FOV can be adjusted to tweak the perspective.
