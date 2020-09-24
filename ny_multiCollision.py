from maya import OpenMaya as om
from maya import OpenMayaMPx as ommpx
from maya import cmds


class MultiCollision(ommpx.MPxDeformerNode):

    nodeName = "multiCollision"
    nodeTypeId = om.MTypeId(0x0007f7c0)

    def __init__(self):
        super(MultiCollision, self).__init__()

    @classmethod
    def creator(cls):
        return MultiCollision()

    @classmethod
    def initialize(cls):
        #mobjects
        cls.colliderList = om.MObject()
        cls.boundingBoxMin = om.MObject()
        cls.boundingBoxMax = om.MObject()
        cls.boundingBoxComp = om.MObject()
        
        #function sets
        compAttr = om.MFnCompoundAttribute()
        numAttr = om.MFnNumericAttribute()
        typedAttr = om.MFnTypedAttribute()

        #collider array
        cls.colliderList = typedAttr.create("colliderList", "collist", om.MFnData.kMesh)
        typedAttr.setArray(True)
        typedAttr.setReadable(False)
        typedAttr.setDisconnectBehavior(0)
        cls.addAttribute(cls.colliderList)

        #bounding box array
        cls.boundingBoxMin = numAttr.createPoint("boundingBoxMin", "bboxmin")
        cls.addAttribute(cls.boundingBoxMin)

        cls.boundingBoxMax = numAttr.createPoint("boundingBoxMax", "bboxmax")
        cls.addAttribute(cls.boundingBoxMax)

        cls.boundingBoxComp = compAttr.create("boundingBoxList", "bboxlist")
        numAttr.setKeyable(False)
        numAttr.setReadable(False)
        cls.addAttribute(cls.boundingBoxComp)
        compAttr.addChild(cls.boundingBoxMin)
        compAttr.addChild(cls.boundingBoxMax)
        compAttr.setArray(True)
        compAttr.setReadable(False)

        #connections
        outputGeom = ommpx.cvar.MPxGeometryFilter_outputGeom
        cls.attributeAffects(cls.colliderList, outputGeom)
        cls.attributeAffects(cls.boundingBoxMin, outputGeom)
        cls.attributeAffects(cls.boundingBoxMax, outputGeom)
        cls.attributeAffects(cls.boundingBoxComp, outputGeom)

        
    def deform(self, dataBlock, geoIter, matrix, geoIndex):
        #input geo
        inputGet = ommpx.cvar.MPxGeometryFilter_input
        inputHandle = dataBlock.outputArrayValue(inputGet)
        inputHandle.jumpToElement(geoIndex)
        inputElement = inputHandle.outputValue()
        inputGeomGet = ommpx.cvar.MPxGeometryFilter_inputGeom
        inputGeom = inputElement.child(inputGeomGet).asMesh()
        defMeshFN = om.MFnMesh(inputGeom)

        #envelope value
        envelopeValue = dataBlock.inputValue(self.envelope).asFloat()
        if envelopeValue == 0:
            return

        #collider list
        colliderListHandle = dataBlock.inputArrayValue(MultiCollision.colliderList)
        boundingBoxCompHandle = dataBlock.inputArrayValue(MultiCollision.boundingBoxComp)
        if colliderListHandle.elementCount() != boundingBoxCompHandle.elementCount():
            return
        else:
            #for each collider input:
            #1.get collider dagpath
            #2.create collider bounding box
            #3.do the deformation
            
            #getting the dagpath and creating mesh function set
            for cd in range(colliderListHandle.elementCount()):
                thisNode = om.MFnDependencyNode(self.thisMObject())
                colliderListPlug = thisNode.findPlug("colliderList", False)
                colliderIndex = colliderListPlug.connectionByPhysicalIndex(cd)
                colliderSource = colliderIndex.source()
                colliderNode = colliderSource.node()
                colliderDagPath = om.MDagPath()
                om.MDagPath.getAPathTo(colliderNode, colliderDagPath)
                colMeshFN = om.MFnMesh(colliderDagPath)
                #creating the boundingbox
                boundingBoxCompHandle.jumpToElement(cd)
                toChild = boundingBoxCompHandle.inputValue()
                boundingBoxMinHandle = toChild.child(MultiCollision.boundingBoxMin)
                boundingBoxMaxHandle = toChild.child(MultiCollision.boundingBoxMax)
                boundingBoxMinValue = boundingBoxMinHandle.asFloat3()
                boundingBoxMaxValue = boundingBoxMaxHandle.asFloat3()
                colbboxmin = om.MPoint(boundingBoxMinValue[0], boundingBoxMinValue[1], boundingBoxMinValue[2])
                colbboxmax = om.MPoint(boundingBoxMaxValue[0], boundingBoxMaxValue[1], boundingBoxMaxValue[2])
                colliderBBox = om.MBoundingBox(colbboxmin, colbboxmax)

                #allIntersections flags
                faceIDs = None
                triIDs = None
                IDsSorted = False
                space = om.MSpace.kObject
                maxParam = 100000
                testBothMultiDirections = False
                accelParams = defMeshFN.autoUniformGridParams()
                sortHits = False
                hitPoints = om.MFloatPointArray()
                hitRayParams = None
                hitFaces = None
                hitTris = None
                hitBarys1= None
                hitBarys2 = None
                tolerance = 0.0001 

                normals = om.MFloatVectorArray()
                defMeshFN.getVertexNormals(False, normals)

                while not geoIter.isDone():
                    #if weight of the vertex is zero, do not calculate anything
                    weightValue = self.weightValue(dataBlock, geoIndex, geoIter.index())
                    if weightValue == 0:
                        geoIter.next()
                    else:
                        point = geoIter.position(space) * matrix
                        #if the vertex is in the collider, look for an intersection
                        if colliderBBox.contains(point):
                            raySource = om.MFloatPoint(point[0], point[1], point[2], 1.0)
                            normal = normals[geoIter.index()]
                            rayDir = om.MFloatVector(normal[0], normal[1], normal[2])
                            hit = colMeshFN.allIntersections(raySource, rayDir, faceIDs, triIDs, IDsSorted,
                                                om.MSpace.kWorld, maxParam, testBothMultiDirections,
                                                accelParams, sortHits, hitPoints,
                                                hitRayParams, hitFaces, hitTris, hitBarys1,
                                                hitBarys2, tolerance)               
                            if hit:
                                #further check if the intersection is colliding with the object
                                closePoint = om.MPoint()
                                closeNormal = om.MVector()
                                colMeshFN.getClosestPoint(point, closePoint, om.MSpace.kWorld, None)
                                colMeshFN.getClosestNormal(closePoint, closeNormal, om.MSpace.kWorld, None)
                                delta = point - closePoint
                                angle = delta * closeNormal
                                if angle < 0:
                                    #if it's inside the object, apply the delta to the point
                                    endPoint = point - delta * weightValue * envelopeValue
                                    endPoint *= matrix.inverse()
                                    geoIter.setPosition(endPoint)
                        geoIter.next()
                
                geoIter.reset()             

def initializePlugin(plugin):
    vendor = "Nazmi 'printer' Yazici"
    version = "0.6.0"
    pluginFN = ommpx.MFnPlugin(plugin, vendor, version)
    cmds.makePaintable(MultiCollision.nodeName, "weights", attrType="multiFloat", shapeMode="deformer")
    try:
        pluginFN.registerNode(MultiCollision.nodeName,
                                MultiCollision.nodeTypeId,  
                                MultiCollision.creator,
                                MultiCollision.initialize,
                                ommpx.MPxNode.kDeformerNode)
    except:
        om.MGlobal.displayError("Failed to register node:{}".format(MultiCollision.nodeName))

def uninitializePlugin(plugin):
    pluginFN = ommpx.MFnPlugin(plugin)
    cmds.makePaintable(MultiCollision.nodeName, "weights", remove=True)
    try:
        pluginFN.deregisterNode(MultiCollision.nodeTypeId)
    except:
        om.MGlobal.displayError("Failed to deregister node:{}".format(MultiCollision.nodeName))