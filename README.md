# ny_collisionDeformer
## Collision Deformer for Autodesk Maya

![Maya Python API_ Collision Deformer-low](https://user-images.githubusercontent.com/41262770/115991413-f2c96e80-a5d0-11eb-91d1-992245264da6.gif)

https://vimeo.com/506137334

**FEATURES**: Multi-collider. Bulging effect. Post-deformation smoothing. Weight paintable.

**INSTALL**: PYTHON: Copy the "ny_collisionDeformer.py" to your "maya/plug-ins" folder and make sure it's loaded on Plug-in Manager.

CPP: Copy the "nyCollisionDeformer.mll" to your "plug-ins" folder and "nyCollision_procs.mel" to your "scripts" folder.

**HOW TO USE**: For the initial setup, first select the collider object, then select the object that is going to deform and run the MEL command:
`nyCollision_create()`

To add and remove collider from the deformer, use same selection order and execute the MEL commands below respectively:

`nyCollision_add()`

`nyCollision_remove()`
