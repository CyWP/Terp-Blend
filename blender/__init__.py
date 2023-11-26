#This file holds everything
import bpy
import bmesh
from bpy.types import Context, Event
from pythonosc.osc_server import AsyncIOOSCUDPServer
from pythonosc.dispatcher import Dispatcher
import asyncio
import random
import numpy as np
import contextlib
import time
from typing import List, Any

def align_to_normal(vec, face):
    return np.matmul(vec, rotation_matrix(face.normal, vec))

def rotation_matrix(vec1, vec2):
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = (vec1 / np.linalg.norm(vec1)).reshape(3), (vec2 / np.linalg.norm(vec2)).reshape(3)
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
    return rotation_matrix
    

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
class Listen(bpy.types.Operator):
    bl_idname = "listen.osc"
    bl_label = "Start Listening OSC"

    def __init__(self):
        self.diffreset=5
        self.diffmax=3
        self.samecount=0
        self.diffcount=self.diffmax-1
        self.currclass = 0
        self.vec = [0.0 ,0.0 ,0.0]
        self.face = []
        self.defs=[]
        self.mappings = {"Move": self.move_face, "Extrude": self.extrude_face, "Vector Scale": self.vscale_face}

    @contextlib.contextmanager
    def get_bmesh(self, obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        yield bm
        bm.normal_update()
        bm.to_mesh(obj.data)
        obj.data.update()
        bpy.context.view_layer.depsgraph.update()
        bm.free()

    def category_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        print(osc_arguments[1])
        self, context = osc_arguments[0] 
        i = int(osc_arguments[1]-1)
        if i==self.currclass:
            self.samecount+=1
            if self.samecount==self.diffreset:
                self.diffcount=0
        else:
            self.diffcount += 1
            if self.diffcount==self.diffmax:
                self.diffcount=0
                self.samecount=0
                self.currclass=i

    def vector_handler(address: str, fixed_argument: List[Any],*osc_arguments: List[Any]) -> None:
        print(osc_arguments[1])
        self, context = osc_arguments[0]  
        self.vec=[osc_arguments[1], osc_arguments[2], osc_arguments[3]]

    def end_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        self, context = osc_arguments[0] 
        bpy.context.scene.op_tool.end = True

    def start_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        self, context = osc_arguments[0] 
        bpy.context.scene.op_tool.start = True

    async def loop(self, context):
        mytool = context.scene.op_tool
        while not mytool.start:
            await asyncio.sleep(1)
        mytool.start = False
        while not mytool.end:
            self.modal(context)

    async def init_main(ip, port, dispatcher, self, context):
        print("initmain")
        server = AsyncIOOSCUDPServer((ip, port), dispatcher, asyncio.get_event_loop())
        transport, protocol = await server.create_serve_endpoint()  # Create datagram endpoint and start serving
        await self.loop(context)  # Enter main loop of program
        transport.close()  # Clean up serve endpoint

    def map_defs(self):
        for i in categories:
            self.defs.append(self.mappings[i])

    def modal(self, context, event):
        print(event.type)
        if event.type in {'ESC', 'DEL'}:
            bpy.context.scene.op_tool.end = False
            #clear function mapping
            self.defs.clear()
            return {'CANCELLED'}
        elif bpy.context.scene.op_tool.end:
            bpy.context.scene.op_tool.end = False
            #clear function mapping
            self.defs.clear()
            print('MODAL')
            return {'FINISHED'}
        elif event.type =='MOUSEMOVE':
            #await asyncio.sleep(0.1)
            self.execute(context)
            time.sleep(0.1)
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        #map functions for execution
        context.window_manager.modal_handler_add(self)
        self.map_defs()
        print("invoked")
        #Setup OSC server
        dispatcher = Dispatcher()
        dispatcher.map("/start", self.start_handler, self, context)
        dispatcher.map("/wek/outputs", self.category_handler, self, context)
        dispatcher.map("/vec", self.vector_handler, self, context)
        dispatcher.map("/end", self.end_handler, self, context)
        ip = "127.0.0.1"
        port = context.scene.panel_tool.osc
        self.face.clear()
        with self.get_bmesh(context.active_object) as bm:
            rand = random.randint(0, len(bm.faces)-1)
            bm.faces.ensure_lookup_table()
            self.face.append(bm.faces[rand])
        #run   
        asyncio.run(self.init_main(port, dispatcher, self, context))
        '''self.server = AsyncIOOSCUDPServer((ip, port), dispatcher, asyncio.get_event_loop())
        self.server.serve()'''
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.defs[self.currclass](context)
        return {'RUNNING_MODAL'}
    
    def move_face(self, context):
        optool = bpy.context.scene.op_tool
        print("move")
        with self.get_bmesh(context.active_object) as bm:
            #bmesh.ops.translate(bm, vec=self.vec, verts=self.face[0].verts)
            bm.faces.ensure_lookup_table()
            bmesh.ops.translate(bm, vec=self.vec, verts=bm.faces[0].verts)
            '''bm.normal_update()
            bm.to_mesh(context.active_object.data)
            context.active_object.data.update()
            bm.free()'''

    def extrude_face(self, context):
        print("extrude")
        with self.get_bmesh(context.active_object) as bm:
            bmesh.ops.extrude_discrete_faces(bm, faces=self.face, use_normal_flip=False, use_select_history=False)
            bmesh.ops.translate(bm, vec=self.vec, verts=self.face[0].verts)

    def vscale_face(self, context):
        print("vscale")
        with self.get_bmesh(context.active_object) as bm:
            bmesh.ops.scale(bm, vec=self.vec, verts=self.face[0].verts)

class PanelProperties(bpy.types.PropertyGroup):
    osc: bpy.props.IntProperty(name= "OSC", default=12000)
    new_cat: bpy.props.StringProperty(name="", default="new_category")
    ops: bpy.props.EnumProperty(name="", description="List of mappable mesh operators", items = operations)

class OperationProperties(bpy.types.PropertyGroup):
    start :bpy.props.BoolProperty(name="", default=False)
    end: bpy.props.BoolProperty(name="", default=False)
    vec: bpy.props.FloatVectorProperty(name="", default=[0.0, 0.0, 0.0])
    currentcat: bpy.props.IntProperty(name="", default=0)

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

classes = [PanelProperties, OperationProperties, MainPanel, MapPanel, AddCategory, RemoveCategory, MapCategory, Listen]
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.panel_tool = bpy.props.PointerProperty(type= PanelProperties)
    bpy.types.Scene.op_tool = bpy.props.PointerProperty(type=OperationProperties)
    bpy.types.Scene.catenum = bpy.props.EnumProperty(items=generate_categories, name="Categories")

def unregister():
    for cls in classes:
           bpy.utils.unregister_class(cls)
    del bpy.types.Scene.panel_tool

if __name__ == "__main__":
    register()