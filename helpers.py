from maya import cmds

def create_collision():
    selList = cmds.ls(sl=True, ap=True, long=True)
    collider = selList[0]
    deforming = selList[1]
    
    deformer = cmds.deformer(deforming, type="multiCollision")[0]
    colliderShape = cmds.listRelatives(collider, children=True, shapes=True)[0]
    
    cmds.connectAttr(colliderShape + ".worldMesh[0]", deformer + ".colliderList[0]")
    cmds.connectAttr(collider + ".boundingBoxMin", deformer + ".boundingBoxList[0].boundingBoxMin")
    cmds.connectAttr(collider + ".boundingBoxMax", deformer + ".boundingBoxList[0].boundingBoxMax")
    

def add_collider():
    selList = cmds.ls(sl=True, ap=True, long=True)
    collider = selList[0]
    deforming = selList[1]

    colliderShape = cmds.listRelatives(collider, children=True, shapes=True)[0]
    deformingShape = cmds.listRelatives(deforming, children=True, shapes=True)[0]

    deformerNode = cmds.listConnections(deformingShape + ".inMesh", d=False, s=True)[0]
    index = cmds.getAttr(deformerNode + ".boundingBoxList", size=True)

    cmds.connectAttr(colliderShape + ".worldMesh[0]", deformerNode + ".colliderList[{}]".format(index))
    cmds.connectAttr(collider + ".boundingBoxMin", deformerNode + ".boundingBoxList[{}].boundingBoxMin".format(index))
    cmds.connectAttr(collider + ".boundingBoxMax", deformerNode + ".boundingBoxList[{}].boundingBoxMax".format(index))