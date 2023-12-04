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
from mathutils import Matrix
from math import radians
from typing import List, Any

def align_to_normal(vec, face):
    return np.matmul(vec, rotation_matrix(face.normal.to_tuple(), vec))

def rotation_matrix(vec1, vec2):
    """ Find the rotation matrix that aligns vec1 to vec2
    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    a, b = (vec1 / np.linalg.norm(vec1)), (vec2 / np.linalg.norm(vec2))
    v = np.cross(a, b)
    c = np.dot(a, b)
    s = np.linalg.norm(v)
    kmat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    rotation_matrix = np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s ** 2))
    return rotation_matrix

def face_center(face):
    center = [0.0, 0.0, 0.0]
    n = 0
    for v in face.verts:
        center[0] += v.co.x
        center[1] += v.co.y
        center[2] += v.co.z
        n += 1
    for c in center:
        c /= n
    return center

def min_center_dist(face):
    center = face_center(face)
    dists = []
    for v in face.verts:
        dist = [v.co.x-center[0], v.co.y-center[1], v.co.z-center[2]]
        dists.append(np.linalg.norm(dist))
    return min(dists)

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
class Dummy(bpy.types.Operator):
    bl_idname = "dum.my"
    bl_label = "Add Category"

    @contextlib.contextmanager
    def get_bmesh(self, context, obj):
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        yield bm
        bm.normal_update()
        bm.to_mesh(obj.data)
        obj.data.update()
        bm.free()

    def execute(self, context):
        for i in range(10):
            optool = bpy.context.scene.op_tool
            with self.get_bmesh(context, context.active_object) as bm:
                #bmesh.ops.translate(bm, vec=self.vec, verts=self.face[0].verts)
                bm.faces.ensure_lookup_table()
                bmesh.ops.translate(bm, vec=[0,0,1], verts=bm.faces[0].verts)
                time.sleep(0.3)
            bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        return {'FINISHED'}
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
        self.diffmax=2
        self.samecount=0
        self.diffcount=self.diffmax-1
        self.currclass = 0
        self.vec = [0.0 ,0.0 ,0.0]
        self.face = 0
        self.defs=[]
        self.mappings = {"Move": self.move_face, "Extrude": self.extrude_face, "Vector Scale": self.vscale_face, "Uniform Scale": self.uscale_face,
                         "Select": self.select_face, "Rotate": self.rotate_face, "Inset": self.inset_face, "Smooth": self.smooth_face_region}

    @contextlib.contextmanager
    def get_bmesh(self, context):
        obj = context.active_object
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        yield bm
        bm.normal_update()
        bm.to_mesh(obj.data)
        obj.data.update()
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
        bm.free()

    def category_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        self, context = osc_arguments[0] 
        i = int(osc_arguments[1])
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
        self, context = osc_arguments[0]  
        self.vec=[self.strength[0]*self.coef*osc_arguments[1], self.strength[1]*self.coef*osc_arguments[2], self.strength[2]*self.coef*osc_arguments[3]]

    def end_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        self, context = osc_arguments[0] 
        bpy.context.scene.op_tool.end = True

    def start_handler(address: str, fixed_argument: List[Any], *osc_arguments: List[Any]) -> None:
        self, context = osc_arguments[0] 
        bpy.context.scene.op_tool.start = True

    async def loop(self, context):
        mytool = context.scene.op_tool
        while not mytool.start:
            print("wait")
            await asyncio.sleep(1)
        mytool.start = False
        while not mytool.end:
            await asyncio.sleep(0.01)
            self.modal(context, None)

    async def init_main(self, context):
        print("initmain")
        self.server = AsyncIOOSCUDPServer((self.ip, self.port), self.dispatcher, asyncio.get_event_loop())
        transport, protocol = await self.server.create_serve_endpoint()  # Create datagram endpoint and start serving
        await self.loop(context)  # Enter main loop of program
        transport.close()  # Clean up serve endpoint

    def map_defs(self):
        for i in categories:
            self.defs.append(self.mappings[i])

    def modal(self, context, event):
        if event is None:
            self.execute(context)
            return {'RUNNING_MODAL'}
        elif event.type in {'ESC', 'DEL'}:
            bpy.context.scene.op_tool.end = False
            #clear function mapping
            self.defs.clear()
            return {'CANCELLED'}
        elif bpy.context.scene.op_tool.end:
            bpy.context.scene.op_tool.end = False
            bpy.ops.object.modifier_add(type='SUBSURF')
            # Access the last added modifier (which is the Subdivision Surface modifier)
            modifier = context.active_object.modifiers[-1]
            # Set the number of subdivisions
            modifier.levels = 3  # Adjust the number of subdivisions as needed
            modifier.render_levels = 3  # Adjust the render subdivisions as needed
            #clear function mapping
            self.defs.clear()
            return {'FINISHED'}
        return {'PASS_THROUGH'}
    
    def invoke(self, context, event):
        #map functions for execution
        context.window_manager.modal_handler_add(self)
        self.numclasses = len(categories)
        self.map_defs()
        print("invoked")
        #Setup OSC server
        self.dispatcher = Dispatcher()
        self.dispatcher.map("/start", self.start_handler, self, context)
        self.dispatcher.map("/wek/outputs", self.category_handler, self, context)
        self.dispatcher.map("/vec", self.vector_handler, self, context)
        self.dispatcher.map("/end", self.end_handler, self, context)
        self.ip = "127.0.0.1"
        self.port = context.scene.panel_tool.osc
        self.face = 0
        self.strength = [5*bpy.context.scene.panel_tool.strength[0], 5*bpy.context.scene.panel_tool.strength[1], 5*bpy.context.scene.panel_tool.strength[2]]
        self.mustrength = np.mean(self.strength)
        self.coef = np.mean([context.active_object.dimensions.x, context.active_object.dimensions.y, context.active_object.dimensions.z])
        self.threshold = bpy.context.scene.panel_tool.threshold*self.coef*np.mean(self.strength)
        with self.get_bmesh(context) as bm:
            self.face = random.randint(0, len(bm.faces)-1)
        #run   
        asyncio.run(self.init_main(context))
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.defs[self.currclass%self.numclasses-1](context)
        return {'RUNNING_MODAL'}
    
    def select_face(self, context):
        optool = bpy.context.scene.op_tool
        with self.get_bmesh(context) as bm:
            origin = face_center(bm.faces[self.face])
            projected = origin + self.vec
            closest = np.linalg.norm(self.vec) #need to change that once I implement strength
            cloi = self.face
            for j in range(len(bm.faces)):
                n = 0
                center = face_center(bm.faces[j])
                dist = [projected[0]-center[0], projected[1]-center[1], projected[2]-center[2]]
                dist = np.linalg.norm(dist)
                if dist < closest:
                    closest = dist
                    cloi = j
            self.face = cloi


    def move_face(self, context):
        optool = bpy.context.scene.op_tool
        with self.get_bmesh(context) as bm:
            bmesh.ops.translate(bm, vec=self.vec, verts=bm.faces[self.face].verts)

    def extrude_face(self, context):
        with self.get_bmesh(context) as bm:
            bmesh.ops.extrude_discrete_faces(bm, faces=[bm.faces[self.face]], use_normal_flip=False, use_select_history=False)
            bm.faces.ensure_lookup_table()
            bmesh.ops.translate(bm, vec=align_to_normal(self.vec, bm.faces[self.face]), verts=bm.faces[self.face].verts)

    def vscale_face(self, context):
        vec = [abs((self.vec[0]+self.threshold)/self.threshold), abs((self.vec[1]+self.threshold)/self.threshold), abs((self.vec[2]+self.threshold)/self.threshold)] #little bit of hard coding, as a treat
        with self.get_bmesh(context) as bm:
            bmesh.ops.scale(bm, vec=vec, verts=bm.faces[self.face].verts)

    def uscale_face(self, context):
        mu = np.mean(self.vec)
        val = abs((mu+self.threshold)/self.threshold)
        vec = [val, val, val]
        with self.get_bmesh(context) as bm:
            bmesh.ops.scale(bm, vec=vec, verts=bm.faces[self.face].verts)

    def rotate_face(self, context):
        with self.get_bmesh(context) as bm:
            center = face_center(bm.faces[self.face])
            norm = np.linalg.norm(self.vec)
            invnorm = 1/norm
            #axis = [self.vec[0]*invnorm, self.vec[1]*invnorm, self.vec[2]*invnorm]
            axis= bm.faces[self.face].normal.normalized()
            degs = radians(norm*180/(1.4142*self.coef*self.mustrength)) #1.4142=sqrt2. Somewhat limits rotation to 180 degs
            rot = Matrix.Rotation(degs, 3, axis)
            bmesh.ops.rotate(bm, cent=center, matrix=rot, verts=bm.faces[self.face].verts)

    def inset_face(self, context):
        with self.get_bmesh(context) as bm:
            norm = np.linalg.norm(self.vec)
            maxdist = min_center_dist(bm.faces[self.face])
            dist = maxdist-maxdist**2/(maxdist+ norm**2-self.threshold**2) #Gives good results, plotted this in desmos to make sure
            outset= norm > self.threshold
            bmesh.ops.inset_region(bm, faces=[bm.faces[self.face]], thickness=dist, use_outset= outset)

    def smooth_face_region(self, context):
        with self.get_bmesh(context) as bm:
            bmesh.ops.smooth_vert(bm, verts=bm.faces[self.face].verts, factor=np.linalg.norm(self.vec))
class PanelProperties(bpy.types.PropertyGroup):
    osc: bpy.props.IntProperty(name= "OSC", default=12000)
    new_cat: bpy.props.StringProperty(name="", default="new_category")
    strength: bpy.props.FloatVectorProperty(name="Strength", description="Strength coefficient for mesh operations (x, y, z)" ,default =[1.0, 1.0, 1.0])
    ops: bpy.props.EnumProperty(name="", description="List of mappable mesh operators", items = operations)
    threshold: bpy.props.FloatProperty(name="Treshold", default=0.1)

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
        row.operator('dum.my', text= "", icon="PAUSE")
        row = self.layout.row()
        row.prop(mytool, "strength")
        row = self.layout.row()
        row.prop(mytool, "threshold")
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

classes = [PanelProperties, OperationProperties, MainPanel, MapPanel, AddCategory, RemoveCategory, MapCategory, Listen, Dummy]
    
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