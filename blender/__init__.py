#This file holds everything
import bpy
from bpy.types import Context
import pythonosc

categories = []
operations = [("Move", "Move", "Move selected face along vector projected onto face normal"),("Uniform Scale", "Uniform Scale", "Uniformly scale selected face"),
             ("Vector Scale", "Vector Scale", "Scale according to vector"),("Rotate", "Rotate", "Rotate face along vector"),
             ("Extrude", "Extrude", "Extrude face along vector projected to face normal."),("Shrink/Fatten", "Shrink/Fatten", "Shrink/fatten face (shrink if val<0, fatten if val>0)"),
             ("Push/Pull", "Push/Pull", "Push/Pull selected face's vertices (push if val>0, pull if val<0)"),("Inset", "Inset", "Inset selected face"),
             ("Select", "Select", "Select face closest to vector using current selected face as origin"),("Randomize", "Randomize", "Translate vertice coordinates along random vectors"),
             ("Shear", "Shear", "Shear face along direction most similar to vector"), ("Smooth", "Smooth", "Smooth angles between selected and neighbouring faces")]

def generate_categories(self, context):
    enum = []    
    for i in range(len(categories)):
        enum.append((str(i), str(i), "", i))
    return enum

bl_info = {
    "name": "Terpsichore",
    "author": "Thomas Peschlow",
    "version": (0, 0),
    "blender": (3, 50, 1),
    "location": "View3D > Toolbar > Terpsichore",
    "Description": "Machine learning interface for movement-object translation.",
    "warning": "",
    "wiki_url": "",
    "category": "Edit Mesh",
}

class add_category(bpy.types.Operator):
    bl_idname = "add.category"
    bl_label = "Add Category"

    def execute(self, context):
        mytool = context.scene.panel_tool
        categories.append(mytool.ops)
        return{'FINISHED'}

class remove_category(bpy.types.Operator):
    bl_idname = "remove.category"
    bl_label = "Remove Category"

    def execute(self, context):
        mytool = context.scene.panel_tool
        categories.pop()
        return{'FINISHED'}
    
class map_category(bpy.types.Operator):
    bl_idname = "map.category"
    bl_label= "Map category to operation"

    def execute(self, context):
        cat = context.scene.catenum
        op = context.scene.panel_tool.ops
        categories[int(cat)] = op
        return{'FINISHED'}

class PanelProperties(bpy.types.PropertyGroup):
    osc: bpy.props.IntProperty(name= "OSC", default=6449)
    new_cat: bpy.props.StringProperty(name="", default="new_category")
    ops: bpy.props.EnumProperty(name="", description="List of mappable mesh operators", items = operations)

class MainPanel(bpy.types.Panel):
    #Panel variables
    bl_label = "Terpsichore v0.0"
    bl_idname = "Terp_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = "Terp"

    #Panel layout
    def draw(self, context: Context):
        obj = context.object
        layout = self.layout
        scene = context.scene
        mytool = scene.panel_tool

        row = self.layout.row()
        row.operator('mesh.primitive_cube_add', text= "Listen", icon="ARMATURE_DATA")
        row.prop(mytool, "osc")
        row.operator('mesh.primitive_cube_add', text= "", icon="PAUSE")
        row = self.layout.row()
        if(obj!=None):
            row.label(text='Object: '+obj.name, icon='CUBE')
        else:
            row.label(text='Select an object', icon='CUBE')
        row = self.layout.row()
        if(obj!=None and obj.vertex_groups.active!=None):
            row.label(text='Vertex Group: '+obj.vertex_groups.active.name, icon='MESH_DATA')
        else:
            row.label(text='Create a Vertex Group', icon='MESH_DATA')

class MapPanel(bpy.types.Panel):

    #Panel variables
    bl_label = "Mapping"
    bl_idname = "Map_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = "Terp"

    #Panel layout
    def draw(self, context: Context):
        obj = context.object
        scene=context.scene
        mytool = scene.panel_tool

        layout = self.layout
        row = self.layout.row()
        row.label(text=f"{len(categories)} categories")
        row.operator('add.category', text="", icon="ADD")
        row.operator('remove.category', text="", icon="REMOVE")
        row = self.layout.row()
        row.label(text="Map a category to an operation:")
        row = self.layout.row()
        row.prop(context.scene, "catenum", text="")
        row.prop(mytool, "ops")
        row.operator('map.category', text= "Map", icon="UV_SYNC_SELECT")
        if len(categories)==0:
            row = self.layout.row()
            row.label(text="Add categories to map them.")
        else:
            box=layout.box()
            split=box.split(factor=0.4)
            l=split.column()
            split =split.split(factor=0.2)
            m=split.column()
            m.alignment='CENTER'
            split =split.split()
            r=split.column()
            r.alignment='RIGHT'
            for i in range(len(categories)):
                l.label(text=str(i))
                m.label(text="", icon='ARROW_LEFTRIGHT')
                r.label(text=categories[i])

classes = [PanelProperties, MainPanel, MapPanel, add_category, remove_category, map_category]
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.panel_tool = bpy.props.PointerProperty(type= PanelProperties)
    bpy.types.Scene.catenum = bpy.props.EnumProperty(items=generate_categories, name="Categories")

def unregister():
    for cls in classes:
           bpy.utils.unregister_class(cls)
    del bpy.types.Scene.panel_tool

if __name__ == "__main__":
    register()