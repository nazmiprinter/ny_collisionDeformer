#pragma once

#include <maya/MPxDeformerNode.h>

class CollisionDeformerNode : public MPxDeformerNode
{
public:
	CollisionDeformerNode();
	virtual ~CollisionDeformerNode() override;
	virtual MStatus deform(MDataBlock& dataBlock,
							MItGeometry& geoIter,
							const MMatrix& matrix,
							unsigned int geoIndex) override;
	int firstTime = 1;
	static void* Creator();
	static MStatus Initialize();
	static MTypeId GetTypeId();
	static MString GetTypeName();
private:
	static MObject colliderList;
	static MObject boundingBoxMin;
	static MObject boundingBoxMax;
	static MObject boundingBoxComp;
	static MObject bulgeRamp;
	static MObject bulgeDistance;
	static MObject bulgeStrength;
	static MObject smooth;
};