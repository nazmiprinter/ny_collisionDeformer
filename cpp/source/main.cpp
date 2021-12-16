#include <maya/MFnPlugin.h>
#include <maya/MPxNode.h>
#include <maya/MGlobal.h>

#include "CollisionDeformer.h"

//AUTHOR = Nazmi Yazici
//EMAIL = nazmiprinter@gmail.com
//WEBSITE = nazmiprinter.com
//DATE = 03 / 12 / 2021


MStatus initializePlugin(MObject pluginObj)
{
	MString procStr = "source nyCollision_procs";
	MGlobal::executeCommand(procStr, false, true);

	MFnPlugin pluginFn(pluginObj, "Nazmi 'printer' Yazici", "1.0.0", "Any");
	pluginFn.registerNode(CollisionDeformerNode::GetTypeName(),
									CollisionDeformerNode::GetTypeId(),
									CollisionDeformerNode::Creator,
									CollisionDeformerNode::Initialize,
									MPxNode::kDeformerNode);

	MString makePaintCmd = "makePaintable -attrType multiFloat -sm deformer nyCollisionDeformer weights;";
	MGlobal::executeCommand(makePaintCmd, true);

	return(MS::kSuccess);
}

MStatus uninitializePlugin(MObject pluginObj)
{
	MFnPlugin pluginFn(pluginObj);
	MString removePaintCmd = "makePaintable nyCollisionDeformer weights -remove;";
	MGlobal::executeCommand(removePaintCmd, true);
	pluginFn.deregisterNode(CollisionDeformerNode::GetTypeId());

	return(MS::kSuccess);
}