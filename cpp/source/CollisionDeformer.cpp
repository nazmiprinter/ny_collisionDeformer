#include "CollisionDeformer.h"

#include <maya/MFnCompoundAttribute.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MFnTypedAttribute.h>
#include <maya/MRampAttribute.h>
#include <maya/MFnMesh.h>
#include <maya/MBoundingBox.h>
#include <maya/MPointArray.h>
#include <maya/MFloatVectorArray.h>
#include <maya/MFloatPointArray.h>
#include <maya/MItGeometry.h>
#include <maya/MMatrix.h>
#include <maya/MItMeshVertex.h>
#include <algorithm>
#include <iterator>


static const MTypeId TYPE_ID = MTypeId(0x0007f7c6);
static const MString TYPE_NAME = "nyCollisionDeformer";

MTypeId CollisionDeformerNode::GetTypeId()
{
	return(TYPE_ID);
}

MString CollisionDeformerNode::GetTypeName()
{
	return(TYPE_NAME);
}

MObject CollisionDeformerNode::colliderList;
MObject CollisionDeformerNode::boundingBoxMin;
MObject CollisionDeformerNode::boundingBoxMax;
MObject CollisionDeformerNode::boundingBoxComp;
MObject CollisionDeformerNode::bulgeRamp;
MObject CollisionDeformerNode::bulgeDistance;
MObject CollisionDeformerNode::bulgeStrength;
MObject CollisionDeformerNode::smooth;

CollisionDeformerNode::CollisionDeformerNode() :
	MPxDeformerNode(){}

CollisionDeformerNode::~CollisionDeformerNode(){}

void* CollisionDeformerNode::Creator()
{
	return(new CollisionDeformerNode());
}

MStatus CollisionDeformerNode::Initialize()
{
	//collider array
	MFnTypedAttribute typedAttr;
	colliderList = typedAttr.create("colliderList", "collist", MFnData::kMesh);
	typedAttr.setArray(true);
	typedAttr.setReadable(false);
	typedAttr.setDisconnectBehavior(MFnAttribute::kNothing);
	addAttribute(colliderList);

	//bounding box array
	//min
	MFnNumericAttribute numAttrMin;
	boundingBoxMin = numAttrMin.createPoint("boundingBoxMin", "bboxmin");
	numAttrMin.setReadable(false);
	numAttrMin.setDisconnectBehavior(MFnAttribute::kNothing);
	addAttribute(boundingBoxMin);

	//max
	MFnNumericAttribute numAttrMax;
	boundingBoxMax = numAttrMax.createPoint("boundingBoxMax", "bboxmax");
	numAttrMax.setReadable(false);
	numAttrMax.setDisconnectBehavior(MFnNumericAttribute::kNothing);
	addAttribute(boundingBoxMax);

	//comp
	MFnCompoundAttribute compAttr;
	boundingBoxComp = compAttr.create("boundingBoxList", "bboxlist");
	addAttribute(boundingBoxComp);
	compAttr.addChild(boundingBoxMin);
	compAttr.addChild(boundingBoxMax);
	compAttr.setArray(true);
	compAttr.setReadable(false);
	compAttr.setDisconnectBehavior(MFnNumericAttribute::kNothing);

	//smooth
	MFnNumericAttribute numAttrSmt;
	smooth = numAttrSmt.create("smoothIterations", "smt", MFnNumericData::kInt);
	numAttrSmt.setMin(0.0);
	numAttrSmt.setMax(5.0);
	numAttrSmt.setKeyable(true);
	addAttribute(smooth);

	//bulge distance
	MFnNumericAttribute numAttrBulDist;
	bulgeDistance = numAttrBulDist.create("bulgeDistance", "buldist", MFnNumericData::kFloat);
	numAttrBulDist.setMin(0.0f);
	numAttrBulDist.setKeyable(true);
	addAttribute(bulgeDistance);

	//bulge strength
	MFnNumericAttribute numAttrBulStr;
	bulgeStrength = numAttrBulStr.create("bulgeStrength", "bulstr", MFnNumericData::kFloat);
	numAttrBulStr.setMin(0.0f);
	numAttrBulStr.setMax(10.0f);
	numAttrBulStr.setKeyable(true);
	addAttribute(bulgeStrength);

	//bulge ramp
	MRampAttribute rampAttr;
	bulgeRamp = rampAttr.createCurveRamp("bulgeRamp", "bulcrv");
	addAttribute(bulgeRamp);

	//connections
	attributeAffects(colliderList, outputGeom);
	attributeAffects(boundingBoxMin, outputGeom);
	attributeAffects(boundingBoxMax, outputGeom);
	attributeAffects(boundingBoxComp, outputGeom);
	attributeAffects(smooth, outputGeom);
	attributeAffects(bulgeDistance, outputGeom);
	attributeAffects(bulgeStrength, outputGeom);
	attributeAffects(bulgeRamp, outputGeom);

	return(MS::kSuccess);
}

MStatus CollisionDeformerNode::deform(MDataBlock& dataBlock,
										MItGeometry& geoIter,
										const MMatrix& matrix,
										unsigned int geoIndex)
{
	// initial ramp setup
	MObject thisMO = thisMObject();
	MRampAttribute bulgeHandle(thisMO, bulgeRamp);
	
	if (CollisionDeformerNode::firstTime == 1)
	{
		MFloatArray bulgePosArray;
		MFloatArray bulgeValArray;
		MIntArray bulgeInterpArray;

		bulgePosArray.append(0.00f);
		bulgePosArray.append(0.2500f);
		bulgePosArray.append(1.00f);

		bulgeValArray.append(0.00f);
		bulgeValArray.append(0.900f);
		bulgeValArray.append(0.00f);

		bulgeInterpArray.append(MRampAttribute::kSpline);
		bulgeInterpArray.append(MRampAttribute::kSpline);
		bulgeInterpArray.append(MRampAttribute::kSpline);

		bulgeHandle.addEntries(bulgePosArray, bulgeValArray, bulgeInterpArray);

		CollisionDeformerNode::firstTime = 0;
	}

	float envelopeValue = dataBlock.inputValue(envelope).asFloat();
	if (envelopeValue == 0)
	{
		return(MS::kSuccess);
	}

	//get input geom
	MArrayDataHandle inputHandle = dataBlock.outputArrayValue(input);
	inputHandle.jumpToElement(geoIndex);
	MDataHandle inputElementHandle = inputHandle.outputValue();
	MObject inputGeomObj = inputElementHandle.child(inputGeom).asMesh();
	MFnMesh defMeshFn(inputGeomObj);

	//variables
	double maxDistance = 0.0f;
	float weightVal = 0.0f;
	double angle = 0.0f;
	double distance = 0.0f;
	int curVtx = 0;
	float bulgeValue = 0.0f;
	MBoundingBox colliderBBox;
	MIntArray collidingList;
	MPoint closePoint;
	MVector closeNormal;
	MFloatVectorArray normals;
	defMeshFn.getVertexNormals(false, normals);
	MPointArray pointList;
	defMeshFn.getPoints(pointList);
	int pointLen = pointList.length();
	MPointArray endPointList;
	endPointList.setLength(pointLen);
	MIntArray colliderIndexList;
	MPoint worldPoint;
	MPoint localPoint;
	MFloatPoint raySource;
	MFloatVector normal;
	MFloatVector rayDir;
	bool hit;
	MVector delta;
	MPoint endPoint;
	MIntArray colliderIndices;

	//allIntersections flags
	MMeshIsectAccelParams accelParams;
	accelParams = defMeshFn.autoUniformGridParams();
	bool sortHits = false;
	float tolerance = 0.0001f;
	MFloatPointArray hitPoints;
	MFloatArray hitRayParams;
	MIntArray hitFaces;
	MIntArray hitTriangles;
	MFloatArray hitBary1;
	MFloatArray hitBary2;

	//custom attribute values
	int smoothValue = dataBlock.inputValue(CollisionDeformerNode::smooth).asInt();
	float bulgeStrengthValue = dataBlock.inputValue(CollisionDeformerNode::bulgeStrength).asFloat();
	float bulgeDistanceValue = dataBlock.inputValue(CollisionDeformerNode::bulgeDistance).asFloat();
	
	//custom input handles
	MArrayDataHandle colliderListHandle = dataBlock.inputArrayValue(CollisionDeformerNode::colliderList);
	MArrayDataHandle boundingBoxCompHandle = dataBlock.inputArrayValue(CollisionDeformerNode::boundingBoxComp);

	//finding collider plugs
	MFnDependencyNode thisNode(thisMObject());
	MPlug colliderListPlug = thisNode.findPlug(colliderList, true);
	unsigned int elementCount = colliderListHandle.elementCount();

	//return if nothing is connected
	if (colliderListHandle.elementCount() < 1)
	{
		return(MS::kSuccess);
	}

	if (boundingBoxCompHandle.elementCount() < 1)
	{
		return(MS::kSuccess);
	}
	
	//finding plugs with connection
	for (unsigned int i = 0; i < elementCount; i++)
	{
		colliderListHandle.jumpToElement(i);
		unsigned int elementIndex = colliderListHandle.elementIndex();
		if (colliderListPlug.elementByLogicalIndex(elementIndex).isConnected())
			colliderIndices.append((int)elementIndex);
	}

	//deformation loop with colliders
	for (int i : colliderIndices)
	{
		colliderListHandle.jumpToElement(i);
		MFnMesh colMeshFn = colliderListHandle.inputValue().asMesh();
		boundingBoxCompHandle.jumpToElement(i);
		MDataHandle toChild;
		toChild = boundingBoxCompHandle.inputValue();
		MFloatVector boundingBoxMinValue = toChild.child(CollisionDeformerNode::boundingBoxMin).asFloat3();
		MFloatVector boundingBoxMaxValue = toChild.child(CollisionDeformerNode::boundingBoxMax).asFloat3();
		MPoint colbboxmin(boundingBoxMinValue);
		MPoint colbboxmax(boundingBoxMaxValue);
		colliderBBox.expand(colbboxmin);
		colliderBBox.expand(colbboxmax);

		//direct deformation
		while(!geoIter.isDone())
		{
			curVtx = geoIter.index();
			localPoint = geoIter.position();
			weightVal = weightValue(dataBlock, geoIndex, curVtx);
			if (weightVal == 0)
			{
				geoIter.next();
			}
			else
				worldPoint = localPoint * matrix;
				if (colliderBBox.contains(worldPoint))
				{
					//intersection check with ray casting
					raySource = MFloatPoint(worldPoint[0], worldPoint[1], worldPoint[2], 1.0);
					normal = normals[curVtx];
					rayDir = MFloatVector(normal[0], normal[1], normal[2]);
					hit = colMeshFn.allIntersections(raySource, rayDir, NULL, NULL, false, MSpace::kWorld, 99999, false, &accelParams, false,
													hitPoints, &hitRayParams, &hitFaces, &hitTriangles, &hitBary1, &hitBary2, 0.000001f);
					if (hit)
					{
						colMeshFn.getClosestPointAndNormal(worldPoint, closePoint, closeNormal, MSpace::kWorld, NULL, NULL);
						delta = worldPoint - closePoint;
						//collision check with dot product
						angle = delta * closeNormal;
						if (angle < 0)
						{
							distance = worldPoint.distanceTo(closePoint);
							if (distance > maxDistance)
							{
								maxDistance = distance;
							}
							endPoint = worldPoint - delta * weightVal * envelopeValue;
							endPoint *= matrix.inverse();
							endPointList.set(endPoint, curVtx);
							collidingList.append(curVtx);
						}
						else
						{
							endPointList.set(localPoint, curVtx);
						}
					}
					else
					{
						endPointList.set(localPoint, curVtx);
					}
				}
				else
				{
					endPointList.set(localPoint, curVtx);
				}
				geoIter.next();
		}

		geoIter.setAllPositions(endPointList);

		geoIter.reset();

		//indirect deformation
		if (maxDistance != 0)
			if (bulgeDistanceValue != 0)
				if (bulgeStrengthValue != 0)
					while (!geoIter.isDone())
					{
						localPoint = geoIter.position();
						curVtx = geoIter.index();
						bool exists = std::find(std::begin(collidingList), std::end(collidingList), curVtx) != std::end(collidingList);
						if (!exists)
						{
							weightVal = weightValue(dataBlock, geoIndex, curVtx);
							if (weightVal == 0)
							{
								geoIter.next();
							}
							else
							{
								worldPoint = localPoint * matrix;
								colMeshFn.getClosestPoint(worldPoint, closePoint, MSpace::kWorld, NULL, NULL);
								distance = worldPoint.distanceTo(closePoint);
								if (distance < bulgeDistanceValue)
								{
									MVector normal = normals[curVtx];
									float normalizedDistance = distance / bulgeDistanceValue;
									float reversedNormalize = (1.0f - normalizedDistance) / (1.0f - 0.0f);
									bulgeHandle.getValueAtPosition(normalizedDistance, bulgeValue);
									endPoint = worldPoint + normal * maxDistance * reversedNormalize * bulgeValue * bulgeStrengthValue * weightVal * envelopeValue;
									endPoint *= matrix.inverse();
									endPointList.set(endPoint, curVtx);
									collidingList.append(curVtx);
								}
								else
								{
									endPointList.set(localPoint, curVtx);
								}
							}
						}
						geoIter.next();	
					}

		geoIter.setAllPositions(endPointList);

		geoIter.reset();

	}
	
	//post-deformation smoothing
	if (!smoothValue == 0)
	{
		MItMeshVertex smoothIterator(inputGeomObj);
		MIntArray adjacents;
		MPoint adjPoint;
		MPoint avgPos;
		MVector offset;
		int prevIndex;

		for (int i = 0; i < smoothValue; i++)
		{
			while (!geoIter.isDone())
			{
				localPoint = geoIter.position();
				curVtx = geoIter.index();
				bool exists = std::find(std::begin(collidingList), std::end(collidingList), curVtx) != std::end(collidingList);
				if (!exists)
				{
					endPointList.set(localPoint, curVtx);
				}
				else
				{
					smoothIterator.setIndex(curVtx, prevIndex);
					smoothIterator.getConnectedVertices(adjacents);
					unsigned int adjLen = adjacents.length();
					MPoint avgPoint;

					for (unsigned int i: adjacents)
					{
						defMeshFn.getPoint(i, adjPoint);
						avgPoint += adjPoint;
					}

					avgPos = avgPoint / adjLen;
					offset = localPoint - avgPos;

					endPoint = localPoint - offset * 0.5 * envelopeValue;
					endPointList.set(endPoint, curVtx);
				}
				geoIter.next();
			}

		geoIter.setAllPositions(endPointList);

		geoIter.reset();

		}
	
	}

	return(MS::kSuccess);
}