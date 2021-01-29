# ny_collisionDeformer
Collision Deformer for Maya

Supports multi-collider. Added bulging effect and post-deformation smoothing. 

INSTALL:
Copy the ny_collisionDeformer.py to your "maya/plug-ins" folder and make sure it's loaded on Plug-in Manager.

HOW TO USE:
For the initial setup, FIRST select the collider object, THEN select the object that is going to deform and run the MEL command:
nyCollision_create()

To add and remove collider from the deformer, use the same selection order and use MEL commands below respectively:

nyCollision_add()

nyCollision_remove()
