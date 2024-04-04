####################################################################################################
# Shader IO
#
# Purpose: To export and import shaders as separate files and
#          apply them to objects in the current scene.
#
# Dependencies:
#               maya.cmds
#
#
# Author: Eric Hug
# Updated: 4/01/2024
#
#
####################################################################################################
# IMPORT
# built-in python libraries
import os
import json
import logging
from importlib import reload

# 3rd-party
from maya import cmds


####################################################################################################
# VARIABLES
LOG = logging.getLogger(__name__)


####################################################################################################
# FUNCTIONS
def validate_file_path(file_path=""):
    '''Confirm file exists'''
    return_path = file_path
    if "\\" in return_path:
            return_path = return_path.replace("\\", "/")
            return_path = return_path.replace("//", "/")
    if os.path.exists(return_path):
        return return_path
    else:
        LOG.error("File path not found. \nUsed path: {}".format(return_path))

def export_shaders(full_export_path="", selection_type="mesh"):
    '''Export Shaders as separate maya binary file
        Parameters:
                full_export_path: full file path.
                selection_type: Type of objects selected for context when building data for export.
                                valid values: "meshes" "shadingEngine"
    '''
    shaders_dict = {}
    selection = cmds.ls(selection=True)
    if len(selection) < 1:
        LOG.error("Cannot export because nothing is selected.")
    if selection_type == "mesh":
        meshes = []
        # filter out selected objects that aren't meshes
        for each in selection:
            if cmds.listRelatives(each, shapes=True):
                meshes.extend(cmds.listRelatives(each, shapes=True))
        if len(meshes) < 1:
            LOG.error("No Meshes found in selection")
        # Build shader dictionary
        for each in meshes:
            shading_engine = cmds.listConnections(each, 
                                                type='shadingEngine', 
                                                destination=True)[0]
            if shading_engine in shaders_dict.keys():
                continue
            else:
                shaders_dict[shading_engine] = build_shader_dict(shading_engine=shading_engine)

    elif selection_type == "shadingEngine":
        shading_engines = []
        # filter out selected objects that aren't meshes
        for each in selection:
            if cmds.ls(each, showType=True)[-1] == "shadingEngine":
                shading_engines.append(each)
        if len(shading_engines) < 1:
            LOG.error("No Meshes found in selection")
        # Build shader dictionary
        for each in shading_engines:
            if each in shaders_dict.keys():
                continue
            else:
                shaders_dict[each] = build_shader_dict(shading_engine=each)
                shaders_dict[each]["meshes"] = []
    # Export to JSON file
    with open(full_export_path, "w") as json_file:
        json.dump(shaders_dict, json_file,
                  indent=4,
                  sort_keys=True)
    LOG.info("Shaders Successfully Exported.")

def import_shaders(importPath="", shader_conflicts="rename"):
    '''Import Shaders from json file.
        Parameters:
            importPath: full path to file
            shader_conflicts: How to handle existing shaders before importing. 
                              Accepted values: 
                                  "skip"   : Skips creating shaders if shader name already exists in scene.
                                  "rename" : Creates a new shader with different name from json file (DEFAULT)
                                  "cancel" : Only used in UI to abort import
                                  "replace": Deletes existing shader with same name and creates new one from json.
    '''
    # Get json data
    with open(importPath) as json_file:
            json_data = json.load(json_file)
    shaders_dict = json_data

    # Shader Conflict Options
    if shader_conflicts == "skip":
        skip_list = []
        for shading_engine, shader_network in shaders_dict.items():
            if cmds.objExists(shading_engine):
                skip_list.append(shading_engine)
        for each in skip_list:
            del(shaders_dict[each])
    elif shader_conflicts == "replace":
        for shading_engine, shader_network in shaders_dict.items():
            if cmds.objExists(shading_engine):
                all_related_nodes = get_src_nodes(shading_engine)
                for each in all_related_nodes:
                    if each in cmds.ls(defaultNodes=True):
                        pass
                    else:
                        if cmds.objExists(each):
                            cmds.delete(each)
    elif shader_conflicts == "rename":
        pass
    elif shader_conflicts == "cancel":
        LOG.error("Shader IO Import cancelled")
        return
    else:
        LOG.error("No argument set for parameter: \"shader_conflicts\"")
    
    # Create shader networks
    for shading_engine, shader_network in shaders_dict.items():
        # Create Base Material nodes: material and shadingEngine
        material_name = cmds.shadingNode(shader_network["base_material"]["type"],
                                         name = shader_network["base_material"]["name"], 
                                         asShader=True)
        shader_set = cmds.sets(name=shading_engine, 
                               renderable=True, 
                               noSurfaceShader=True, 
                               empty=True)
        
        if shading_engine != shader_set:
            # print(shader_network["connections"])
            for each in shader_network["connections"]:
                index_num = shader_network["connections"].index(each)
                for attr in each:
                    num = each.index(attr)
                    if attr.startswith(shading_engine+"."):
                        shaders_dict[shading_engine]["connections"][index_num][num] = attr.replace(shading_engine, shader_set)
                        each[num] = attr.replace(shading_engine, shader_set)
            
        if shader_network["base_material"]["name"] != material_name:
            for each in shader_network["connections"]:
                index_num = shader_network["connections"].index(each)
                for attr in each:
                    num = each.index(attr)
                    if attr.startswith(shader_network["base_material"]["name"]+"."):
                        shaders_dict[shading_engine]["connections"][index_num][num] = attr.replace(shader_network["base_material"]["name"], material_name)
            shader_network["nodes"][material_name] = shader_network["nodes"][shader_network["base_material"]["name"]]
            del(shader_network["nodes"][shader_network["base_material"]["name"]])

        # Create Nodes in the network
        for node_name, settings in shader_network["nodes"].items():
            if node_name != material_name:
                new_node = str(cmds.createNode(settings["node_type"], name=node_name))
                if node_name != new_node:
                    for each in shader_network["connections"]:
                        index_num = shader_network["connections"].index(each)
                        for attr in each:
                            num = each.index(attr)
                            if attr.startswith(node_name+"."):
                                shaders_dict[shading_engine]["connections"][index_num][num] = attr.replace(node_name, new_node)
                                print(shaders_dict[shading_engine]["connections"][index_num][num])
                    node_name = new_node
            # Set the attribute values
            for key, val in settings["Attributes"].items():
                set_attr("{}.{}".format(node_name, key), val=val)
        # Connect Attributes together
        for each in shader_network["connections"]:
            cmds.connectAttr(each[0], each[1])
        # Apply Shader to existing meshes
        if len(shader_network["meshes"]) > 0:
            for each in shader_network["meshes"]:
                if cmds.objExists(each):
                    cmds.sets(each, 
                              edit=True, 
                              forceElement=shader_set)
    LOG.info("Shaders successfully imported")

def get_src_nodes(node_name="", node_list=[]):
    '''Get all nodes that are part of the shadingEngine's graph
        Parameters:
                    node_name: Name of shadingEngine node.
                    node_list: DO NOT TOUCH. 
                               List of nodes that will be developed and returned by this recursive function.'''
    src_nodes = cmds.listConnections(node_name, 
                                     source=True, 
                                     destination=False, 
                                     shapes=True)
    remove_shapes = []
    if src_nodes:
        for each in src_nodes:
            if cmds.ls(each, showType=True)[-1] == "mesh":
                remove_shapes.append(each)
        for each in remove_shapes:
            if each in src_nodes:
                src_nodes.remove(each)
    if src_nodes:
        for each in src_nodes:
            if cmds.ls(each, showType=True)[-1] == "mesh":
                continue
            if each not in node_list:
                node_list.append(each)
        for each in src_nodes:
            node_list = get_src_nodes(node_name=each, 
                                      node_list=node_list)
    return node_list
    
    
def build_shader_dict(shading_engine=""):
    '''Creates a dictionary for the specified shadingEngine node that represents the shader's network
        Parameters:
                    shading_engine: shadingEngine node that represents the material
    '''
    filter_list = ["float3", "float2", "double2", "double3"]
    shader_dict = {"base_material":{"name":"",
                                    "type":""
                                    },
                   "nodes":{},
                   "connections":[],
                   "meshes":[]
                   }
    # Base Material Data (the shadingEngine and material nodes)
    # (materials such as: "blinn", "lambert", "aiStandardSurface")
    material_name = cmds.listConnections("{}.surfaceShader".format(shading_engine), destination=False)[0]
    material_type = cmds.ls(material_name, showType=True)[1]
    shader_dict["base_material"]["name"] = material_name
    shader_dict["base_material"]["type"] = material_type

    # Getting mesh shapes and mesh faces for shader_dict
    cmds.hyperShade(objects=material_name)
    meshes_with_material = cmds.ls(selection=True)
    cmds.select(deselect=True)
    for each in meshes_with_material:
        if each in meshes_with_material:
            shader_dict["meshes"].append(each)
        elif cmds.listRelatives(each, parent=True)[0] in meshes_with_material:
            shader_dict["meshes"].append(each)
    
    # shadingEngine Node's Connections
    src = cmds.listConnections(shading_engine, connections=True, plugs=True, destination=False, shapes=False)
    dest = cmds.listConnections(shading_engine, connections=True, plugs=True, source=False, shapes=False)
    for each in src:
        if "dagSetMembers" in each: # skips Connected Meshes
            continue
        if each.split(".")[0] == shading_engine:
            connection_data = cmds.listConnections(each, connections=True, plugs=True, source=True)
            connection_data = confirm_attr_order(connected_attributes=connection_data)
            shader_dict["connections"].append(connection_data)
    
    # Get nodes which are part of specified Shading Network
    shader_graph_nodes = get_src_nodes(node_name=shading_engine, node_list=[])
    for each in shader_graph_nodes:
        # Filter meshes, surfaces and curves
        if cmds.ls(each, showType=True)[-1] == "transform":
            if len(cmds.listRelatives(each, shapes=True)): # skip meshes, surfaces and curves
                continue
        elif each in cmds.ls(defaultNodes=True): # skip nodes found in scene by default
            continue
        else:
            shader_dict["nodes"][each] = {"node_type"  : cmds.ls(each, showType=True)[-1], 
                                          "Attributes" : {}}
        # Get Attributes of each node in the Shading Network
        shader_attrs = cmds.listAttr(each, visible=True, write=True, output=False, inUse=True)
        skip_attributes = []
        for attr in shader_attrs:
            if cmds.attributeQuery(attr, node=each, exists=True):
                full_attr = "{}.{}".format(each, attr)
                # Check if attribute is connected to another, 
                # Else add settings to node's attribute data
                if cmds.listConnections(full_attr, connections=True, plugs=True, source=True, destination=False):
                    connection_data = cmds.listConnections(full_attr, connections=True, plugs=True, source=True, destination=False)
                    connection_data = confirm_attr_order(connected_attributes=connection_data)
                    child_attributes = cmds.attributeQuery(attr, node=each, listChildren=True)
                    if child_attributes:
                        for child in child_attributes:
                            skip_attributes.append(child)
                    if connection_data not in shader_dict["connections"]:
                        shader_dict["connections"].append(connection_data)
                else:
                    if attr not in skip_attributes:
                        if cmds.getAttr(full_attr, type=True) not in filter_list:
                            attr_val = cmds.getAttr(full_attr)
                            if isinstance(attr_val, list):
                                if not any(cmds.getAttr(full_attr)):
                                    pass
                                else:
                                    val = flatten_list(matrix=cmds.getAttr(full_attr))
                                    shader_dict["nodes"][each]["Attributes"][attr] = val
                            else:
                                shader_dict["nodes"][each]["Attributes"][attr] = cmds.getAttr(full_attr)
                    
    return shader_dict

def confirm_attr_order(connected_attributes=[]):
    '''Returns two attributes in the order of "from attribute 1" to "to attribute 2"
        Parameters:
            connected_attributes: two attributes that are connected together.
    '''
    attr_1 = connected_attributes[0]
    attr_2 = connected_attributes[1]
    if cmds.listConnections(attr_1, plugs=True, destination=False):
        if attr_2 in cmds.listConnections(attr_1, plugs=True, destination=False):
            return [attr_2, attr_1]
        else:
            return [attr_1, attr_2]
    else:
        return [attr_1, attr_2]

def set_attr(full_name="", val=None):
    '''Function for setting attribute to specified val while compensating for 
       different flags required in cmds.setAttr() for different attribute types.
        Parameters:
                    full_name: "object.attribute"
                    val:        Value for specified attribute
    '''
    type_filter = ["float", "int", "double", "bool", "enum", "short", "long", "list"]
    attr_type = cmds.getAttr(full_name, type=True)
    if val != cmds.getAttr(full_name):
        if attr_type in type_filter:
            cmds.setAttr(full_name, val)
        else:
            cmds.setAttr(full_name, val, type=attr_type)

def flatten_list(matrix=[]):
    '''Flatten a list with nested lists/tuples into a one-dimensional list. 
       Do not use with dictionaries.
        Parameters:
                    matrix: A list with nested lists or tuples.
                            ex. [[1.0,2.3], [4, (), "string_val"]]
    '''
    new_list=[]
    for each in matrix:
        if isinstance(each, (tuple, list)):
            new_list.extend(each)
        else:
            new_list.append(each)

    return new_list