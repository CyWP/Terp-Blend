#This file holds everything
import bpy
import bmesh
from bpy.types import Context
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio
import time

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

class AddCategory(bpy.types.Operator):
    bl_idname = "add.category"
    bl_label = "Add Category"

    def execute(self, context):
        mytool = context.scene.panel_tool
        categories.append(mytool.ops)
        return{'FINISHED'}

class RemoveCategory(bpy.types.Operator):
    bl_idname = "remove.category"
    bl_label = "Remove Category"

    def execute(self, context):
        mytool = context.scene.panel_tool
        categories.pop()
        return{'FINISHED'}
    
class MapCategory(bpy.types.Operator):
    bl_idname = "map.category"
    bl_label= "Map category to operation"

    def execute(self, context):
        cat = context.scene.catenum
        op = context.scene.panel_tool.ops
        categories[int(cat)] = op
        return{'FINISHED'}

def category_handler(address, *args):
    print(f"{address}: {args}")
    
def vector_handler(address, *args):
    print(f"{address}: {args}")

def end_handler(address, *args):
    bpy.context.scene.panel_tool.end = True
class Listen(bpy.types.Operator):
    bl_idname = "listen.osc"
    bl_label = "Start Listening OSC"

    async def loop(self, context):
        while not context.scene.panel_tool.end:
            await asyncio.sleep(1)

    async def init_main(ip, port, dispatcher, self, context):
        server = AsyncIOOSCUDPServer((ip, port), dispatcher, asyncio.get_event_loop())
        transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
        await Listen.loop(self, context)  # Enter main loop of program
        transport.close()  # Clean up serve endpoint

    def execute(self, context):
        dispatcher = Dispatcher()
        dispatcher.map("/wek/outputs", category_handler)
        dispatcher.map("/vec", vector_handler)
        dispatcher.map("/end", end_handler)
        ip = "127.0.0.1"
        port = context.scene.panel_tool.osc
        asyncio.run(Listen.init_main(ip, port, dispatcher, self, context))
        bpy.context.scene.panel_tool.end = False
        return{'FINISHED'}

class PanelProperties(bpy.types.PropertyGroup):
    osc: bpy.props.IntProperty(name= "OSC", default=12000)
    new_cat: bpy.props.StringProperty(name="", default="new_category")
    ops: bpy.props.EnumProperty(name="", description="List of mappable mesh operators", items = operations)
    end: bpy.props.BoolProperty(name="", default=False)
    vec: bpy.props.FloatVectorProperty(name="", default=[0.0, 0.0, 0.0])
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
        row.operator('listen.osc', text= "Listen", icon="ARMATURE_DATA")
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

classes = [PanelProperties, MainPanel, MapPanel, AddCategory, RemoveCategory, MapCategory, Listen]
    
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