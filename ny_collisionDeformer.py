from maya import OpenMaya as om
from maya import OpenMayaMPx as ommpx
from maya import cmds
from maya.mel import eval as meval

#AUTHOR = Nazmi Yazici
#EMAIL = nazmiprinter@gmail.com
#WEBSITE = vimeo.com/nazmiprinter
#DATE = 23/10/2020

#TODO: Add elasticity

class NyCollisionDeformer(ommpx.MPxDeformerNode):
    NODE_NAME = "nyCollisionDeformer"
    NODE_TYPEID = om.MTypeId(0x0007f7c5)

    def __init__(self):
        super(NyCollisionDeformer, self).__init__()
        self.firstTime = 1

    @classmethod
    def creator(cls):
        return NyCollisionDeformer()

    @classmethod
    def initialize(cls):
        #mobjects
        cls.colliderList = om.MObject()
        cls.boundingBoxMin = om.MObject()
        cls.boundingBoxMax = om.MObject()
        cls.boundingBoxComp = om.MObject()
        cls.bulgeRamp = om.MObject()
        cls.bulgeDistance = om.MObject()
        cls.bulgeStrength = om.MObject()
        cls.smooth = om.MObject()
        #cls.elasticity = om.MObject()
        
        #function sets
        compAttr = om.MFnCompoundAttribute()
        numAttr = om.MFnNumericAttribute()
        typedAttr = om.MFnTypedAttribute()
        #enumAttr = om.MFnEnumAttribute()
        rampAttr = om.MRampAttribute()

        #collider array
        cls.colliderList = typedAttr.create("colliderList", "collist", om.MFnData.kMesh)
        typedAttr.setArray(True)
        typedAttr.setReadable(False)
        typedAttr.setDisconnectBehavior(0)
        cls.addAttribute(cls.colliderList)

        #bounding box array
        cls.boundingBoxMin = numAttr.createPoint("boundingBoxMin", "bboxmin")
        typedAttr.setReadable(False)
        numAttr.setDisconnectBehavior(0)
        cls.addAttribute(cls.boundingBoxMin)

        cls.boundingBoxMax = numAttr.createPoint("boundingBoxMax", "bboxmax")
        typedAttr.setReadable(False)
        numAttr.setDisconnectBehavior(0)
        cls.addAttribute(cls.boundingBoxMax)

        cls.boundingBoxComp = compAttr.create("boundingBoxList", "bboxlist")
        compAttr.setKeyable(False)
        compAttr.setReadable(False)
        compAttr.setDisconnectBehavior(0)
        cls.addAttribute(cls.boundingBoxComp)
        compAttr.addChild(cls.boundingBoxMin)
        compAttr.addChild(cls.boundingBoxMax)
        compAttr.setArray(True)
        compAttr.setReadable(False)
        compAttr.setDisconnectBehavior(0)

        """
        #elasticity
        cls.elasticity = enumAttr.create("elasticity", "elas")
        enumAttr.addField("elastic", 0)
        enumAttr.addField("plastic", 1)
        enumAttr.setKeyable(True)
        cls.addAttribute(cls.elasticity)
        """

        #smooth
        cls.smooth = numAttr.create("smoothIterations", "smt", om.MFnNumericData.kInt)
        numAttr.setMin(0.0)
        numAttr.setMax(5.0)
        numAttr.setKeyable(True)
        cls.addAttribute(cls.smooth)

        #bulge distance
        cls.bulgeDistance = numAttr.create("bulgeDistance", "buldist", om.MFnNumericData.kFloat)
        numAttr.setMin(0.0)
        numAttr.setKeyable(True)
        cls.addAttribute(cls.bulgeDistance)

        #bulge strength
        cls.bulgeStrength = numAttr.create("bulgeStrength", "bulstr", om.MFnNumericData.kFloat, 1.0)
        numAttr.setMin(0.0)
        numAttr.setMax(10.0)
        numAttr.setKeyable(True)
        cls.addAttribute(cls.bulgeStrength)
        
        #bulge ramp
        cls.bulgeRamp = rampAttr.createCurveRamp("bulgeRamp", "bulcrv")
        cls.addAttribute(cls.bulgeRamp)

        #connections
        outputGeom = ommpx.cvar.MPxGeometryFilter_outputGeom
        cls.attributeAffects(cls.colliderList, outputGeom)
        cls.attributeAffects(cls.boundingBoxMin, outputGeom)
        cls.attributeAffects(cls.boundingBoxMax, outputGeom)
        cls.attributeAffects(cls.boundingBoxComp, outputGeom)
        #cls.attributeAffects(cls.elasticity, outputGeom)
        cls.attributeAffects(cls.smooth, outputGeom)
        cls.attributeAffects(cls.bulgeRamp, outputGeom)
        cls.attributeAffects(cls.bulgeDistance, outputGeom)
        cls.attributeAffects(cls.bulgeStrength, outputGeom)

    def deform(self, dataBlock, geoIter, matrix, geoIndex):
        #input geo
        inputGet = ommpx.cvar.MPxGeometryFilter_input
        inputHandle = dataBlock.outputArrayValue(inputGet)
        inputHandle.jumpToElement(geoIndex)
        inputElement = inputHandle.outputValue()
        inputGeomGet = ommpx.cvar.MPxGeometryFilter_inputGeom
        inputGeom = inputElement.child(inputGeomGet).asMesh()
        defMeshFN = om.MFnMesh(inputGeom)
    
        #variables
        thisNode = om.MFnDependencyNode(self.thisMObject())
        thisNodeObj = self.thisMObject()
        maxDistance = 0.0
        colliderBBox = om.MBoundingBox()
        collidingList = om.MIntArray()
        closePoint = om.MPoint()
        closeNormal = om.MVector()
        normals = om.MFloatVectorArray()
        defMeshFN.getVertexNormals(False, normals)
        pointList = om.MPointArray()
        defMeshFN.getPoints(pointList)
        pointLen = pointList.length()
        endPointList = om.MPointArray()
        endPointList.setLength(pointLen)
        colliderIndexList = om.MIntArray()

        #allIntersections flags
        faceIDs = None
        triIDs = None
        IDsSorted = False
        space = om.MSpace.kWorld
        maxParam = 100000
        testBothIndirectDirections = False
        accelParams = defMeshFN.autoUniformGridParams()
        sortHits = False
        hitPoints = om.MFloatPointArray()
        hitRayParams = om.MFloatArray()
        hitFaces = None
        hitTris = None
        hitBarys1= None
        hitBarys2 = None
        tolerance = 0.0001

        #elasticity value
        #elasticityValue = dataBlock.inputValue(NyCollisionDeformer.elasticity).asShort()

        #smooth
        smoothValue = dataBlock.inputValue(NyCollisionDeformer.smooth).asInt()

        #bulge values
        bulgeHandle = om.MRampAttribute(thisNodeObj, NyCollisionDeformer.bulgeRamp)
        bulgeStrengthValue = dataBlock.inputValue(NyCollisionDeformer.bulgeStrength).asFloat()
        bulgeDistanceValue = dataBlock.inputValue(NyCollisionDeformer.bulgeDistance).asFloat()

        bulgeMUtil = om.MScriptUtil()
        bulgeResultMUtil = om.MScriptUtil()
        bulgeValue = bulgeMUtil.asFloatPtr()

        if self.firstTime == 1:
            bulgePosArray = om.MFloatArray()
            bulgeValArray = om.MFloatArray()
            bulgeInterpArray = om.MIntArray()

            bulgePosArray.append(0.000)
            bulgePosArray.append(0.250)
            bulgePosArray.append(1.000)

            bulgeValArray.append(0.000)
            bulgeValArray.append(0.900)
            bulgeValArray.append(0.000)

            bulgeInterpArray.append(om.MRampAttribute.kSpline)
            bulgeInterpArray.append(om.MRampAttribute.kSpline)
            bulgeInterpArray.append(om.MRampAttribute.kSpline)
            bulgeHandle.addEntries(bulgePosArray, bulgeValArray, bulgeInterpArray)

            self.firstTime = 0
        
        #envelope value
        envelopeValue = dataBlock.inputValue(self.envelope).asFloat()
        if envelopeValue == 0:
            return

        #custom inputs
        colliderListHandle = dataBlock.inputArrayValue(NyCollisionDeformer.colliderList)
        boundingBoxCompHandle = dataBlock.inputArrayValue(NyCollisionDeformer.boundingBoxComp)

        if colliderListHandle.elementCount() < 1:
            return

        if boundingBoxCompHandle.elementCount() < 1:
            return
    
        #finding plugs that has connection
        colliderListPlug = thisNode.findPlug("colliderList", False)
        for i in range(colliderListHandle.elementCount()):
            item = colliderListPlug.elementByPhysicalIndex(i)
            index = int(item.name()[-2])
            colliderIndexList.append(index)
        
        #deformation
        for col in range(colliderIndexList.length()):
            colliderListHandle.jumpToElement(colliderIndexList[col])
            colliderInput = colliderListHandle.inputValue().asMesh()
            colMeshFN = om.MFnMesh(colliderInput)
            boundingBoxCompHandle.jumpToElement(colliderIndexList[col])
            toChild = boundingBoxCompHandle.inputValue()
            boundingBoxMinValue = toChild.child(NyCollisionDeformer.boundingBoxMin).asFloat3()
            boundingBoxMaxValue = toChild.child(NyCollisionDeformer.boundingBoxMax).asFloat3()
            colbboxmin = om.MPoint(boundingBoxMinValue[0], boundingBoxMinValue[1], boundingBoxMinValue[2])
            colbboxmax = om.MPoint(boundingBoxMaxValue[0], boundingBoxMaxValue[1], boundingBoxMaxValue[2])
            colliderBBox.expand(colbboxmin)
            colliderBBox.expand(colbboxmax)

            #direct deformation
            while not geoIter.isDone():
                weightValue = self.weightValue(dataBlock, geoIndex, geoIter.index())
                if weightValue == 0:
                    geoIter.next()
                else:
                    point = geoIter.position() * matrix
                    if colliderBBox.contains(point):
                        raySource = om.MFloatPoint(point[0], point[1], point[2], 1.0)
                        normal = normals[geoIter.index()]
                        rayDir = om.MFloatVector(normal[0], normal[1], normal[2])
                        hit = colMeshFN.allIntersections(raySource, rayDir, faceIDs, triIDs, IDsSorted,
                                                        space, maxParam, testBothIndirectDirections,
                                                        accelParams, sortHits, hitPoints,
                                                        hitRayParams, hitFaces, hitTris, hitBarys1,
                                                        hitBarys2, tolerance)               
                        if hit:
                            colMeshFN.getClosestPoint(point, closePoint, space, None)
                            colMeshFN.getClosestNormal(closePoint, closeNormal, space, None)
                            delta = point - closePoint
                            angle = delta * closeNormal
                            if angle < 0:
                                distance = point.distanceTo(closePoint)
                                if distance > maxDistance:
                                    maxDistance = distance
                                endPoint = point - delta * weightValue * envelopeValue
                                endPoint *= matrix.inverse()
                                endPointList.set(endPoint, geoIter.index())
                                collidingList.append(geoIter.index())
                            else:
                                endPointList.set(geoIter.position(), geoIter.index())
                        else:
                            endPointList.set(geoIter.position(), geoIter.index())
                    else:
                        endPointList.set(geoIter.position(), geoIter.index())
                    geoIter.next()
            
            geoIter.reset()
            
            #indirect deformation
            if maxDistance != 0:
                if bulgeDistanceValue != 0:
                    if bulgeStrengthValue != 0:
                        while not geoIter.isDone():
                            if not geoIter.index() in collidingList:
                                weightValue = self.weightValue(dataBlock, geoIndex, geoIter.index())
                                if weightValue == 0:
                                    geoIter.next()
                                else:
                                    point = geoIter.position() * matrix
                                    colMeshFN.getClosestPoint(point, closePoint, space, None)
                                    distance = point.distanceTo(closePoint)
                                    if distance < bulgeDistanceValue:
                                        normal = om.MVector(normals[geoIter.index()][0],
                                                            normals[geoIter.index()][1],
                                                            normals[geoIter.index()][2])
                                        normalizedDistance = float(distance/bulgeDistanceValue)
                                        reversedNormalize = (1 - normalizedDistance) / (1 - 0)
                                        bulgeHandle.getValueAtPosition(normalizedDistance, bulgeValue)
                                        bulgeResult = bulgeResultMUtil.getFloat(bulgeValue)
                                        endPoint = point + normal * maxDistance * reversedNormalize * bulgeResult * bulgeStrengthValue * weightValue * envelopeValue 
                                        endPoint *= matrix.inverse()
                                        endPointList.set(endPoint, geoIter.index())
                                        collidingList.append(geoIter.index())
                                    else:
                                        endPointList.set(geoIter.position(), geoIter.index())
                                        
                            geoIter.next()
                
            geoIter.reset()
        
            geoIter.setAllPositions(endPointList)

        #post deformation smoothing
        if smoothValue == 0:
            return

        smoothIterator = om.MItMeshVertex(inputGeom)
        smoothList = om.MPointArray()
        smoothList.setLength(pointLen)
        adjacents = om.MIntArray()
        adjPoint = om.MPoint()
        avgUtil = om.MScriptUtil()
        avgUtil.createFromInt(0)
        prevIndex = avgUtil.asIntPtr()

        def get_average_point(index):
            smoothIterator.setIndex(index, prevIndex)
            smoothIterator.getConnectedVertices(adjacents)
            avgPoint = om.MPoint()
            for adj in range(adjacents.length()):
                defMeshFN.getPoint(adjacents[adj], adjPoint)
                avgPoint += om.MVector(adjPoint)
             
            avgPos = avgPoint / adjacents.length()
            return avgPos

        for smoothIt in range(smoothValue):
            while not geoIter.isDone():
                if geoIter.index() not in collidingList:
                    smoothList.set(geoIter.position(), geoIter.index())
                else:
                    point = geoIter.position()
                    averagePoint = get_average_point(geoIter.index())
                    offset = point - averagePoint
                    endPoint = point - offset * 0.5 * envelopeValue
                    smoothList.set(endPoint, geoIter.index())
      
                geoIter.next()
            
            geoIter.reset()

            geoIter.setAllPositions(smoothList)


      
def initializePlugin(plugin):
    vendor = "Nazmi 'printer' Yazici"
    version = "0.9.0"
    pluginFN = ommpx.MFnPlugin(plugin, vendor, version)
    cmds.makePaintable(NyCollisionDeformer.NODE_NAME, "weights", attrType="multiFloat", shapeMode="deformer")
    try:
        pluginFN.registerNode(NyCollisionDeformer.NODE_NAME,
                                NyCollisionDeformer.NODE_TYPEID,  
                                NyCollisionDeformer.creator,
                                NyCollisionDeformer.initialize,
                                ommpx.MPxNode.kDeformerNode)
    except:
        om.MGlobal.displayError("Failed to register node:{}".format(NyCollisionDeformer.NODE_NAME))

def uninitializePlugin(plugin):
    pluginFN = ommpx.MFnPlugin(plugin)
    cmds.makePaintable(NyCollisionDeformer.NODE_NAME, "weights", remove=True)
    try:
        pluginFN.deregisterNode(NyCollisionDeformer.NODE_TYPEID)
    except:
        om.MGlobal.displayError("Failed to deregister node:{}".format(NyCollisionDeformer.NODE_NAME))


#mel procedures
mel = '''
//custom attribute editor
global proc AEnyCollisionDeformerTemplate( string $NODE_NAME )
{
    editorTemplate -beginScrollLayout;

        editorTemplate -beginLayout "Deformer Settings" -collapse 0;
        editorTemplate -addControl "envelope";
        editorTemplate -addSeparator;
        editorTemplate -addSeparator;
        editorTemplate -addSeparator;
        //editorTemplate -addControl "elasticity";
        editorTemplate -addControl "smoothIterations";
        editorTemplate -endLayout;

        editorTemplate -beginLayout "Bulge Settings" -collapse 0;
        editorTemplate -addControl "bulgeDistance";
        editorTemplate -addControl "bulgeStrength";    
        AEaddRampControl( $NODE_NAME + ".bulgeRamp" );
        AEdependNodeTemplate $NODE_NAME;
        editorTemplate -endLayout;
    
    editorTemplate -addExtraControls;
    editorTemplate -endScrollLayout;
}

//initial deformer setup
global proc nyCollision_create()
{
	string $selList[] = `ls -sl -ap -long`;
	if (size($selList)==2)
	{
		string $collider = $selList[0];
		string $deforming = $selList[1];
        
		string $colliderShape[] = `listRelatives -s $collider`;
		string $deformer[] = `deformer -typ "nyCollisionDeformer" $deforming`;
        
		connectAttr -f ($colliderShape[0] + ".worldMesh[0]") ($deformer[0] + ".colliderList[0]");
		connectAttr -f ($collider + ".boundingBoxMin") ($deformer[0] + ".boundingBoxList[0].boundingBoxMin");
        connectAttr -f ($collider + ".boundingBoxMax") ($deformer[0] + ".boundingBoxList[0].boundingBoxMax");
	}
	else
	{
		error "Please select collider, then deforming object only to create the deformer.";
	}
}

//adding collider to the deformer
global proc nyCollision_add()
{
	string $selList[] = `ls -sl -ap -long`;
	if (size($selList)==2)
	{
		string $collider = $selList[0];
		string $deforming = $selList[1];
        
		string $colliderShape[] = `listRelatives -s -children $collider`;
		string $deformingShape[] = `listRelatives -s -children $deforming`;
        
        string $deformerNode[] = `listConnections -d false -s true ($deformingShape[0] + ".inMesh")`;
        int $multiIndex[] = `getAttr -mi ($deformerNode[0] + ".colliderList")`;
        int $multiSize = `size $multiIndex`;
        int $lastItem = $multiIndex[$multiSize -1];
        int $finalIndex = $lastItem + 1;
        
		connectAttr ($colliderShape[0] + ".worldMesh[0]") ($deformerNode[0] + ".colliderList[" + $finalIndex + "]");
		connectAttr ($collider + ".boundingBoxMin") ($deformerNode[0] + ".boundingBoxList[" + $finalIndex + "].boundingBoxMin");
        connectAttr ($collider + ".boundingBoxMax") ($deformerNode[0] + ".boundingBoxList[" + $finalIndex + "].boundingBoxMax");
	}
	else
	{
		error "Please select collider, then deforming object only to add another collider.";
	}
}

//removing collider from the deformer
global proc nyCollision_remove()
{
	string $selList[] = `ls -sl -ap -long`;
	if (size($selList)==2)
	{
		string $collider = $selList[0];
		string $deforming = $selList[1];
        
		string $colliderShape[] = `listRelatives -s -children $collider`;

        string $colliderMinConn[] = `listConnections -p true -d true -s false ($collider + ".boundingBoxMin")`;
        string $colliderMaxConn[] = `listConnections -p true -d true -s false ($collider + ".boundingBoxMax")`;
        string $colliderShapeConn[] = `listConnections -p true -d true -s false ($colliderShape[0] + ".worldMesh[0]")`;
        
		disconnectAttr ($colliderShape[0] + ".worldMesh[0]") ($colliderShapeConn);
		disconnectAttr ($collider + ".boundingBoxMin") ($colliderMinConn);
        disconnectAttr ($collider + ".boundingBoxMax") ($colliderMaxConn);
	}
	else
	{
		error "Please select collider, then deforming object only to remove collider.";
	}
}
'''
meval(mel)