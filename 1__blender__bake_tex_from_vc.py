#
# /home/luojinhao/blender-2.82-linux64/blender --background --python 1__blender__bake_tex_from_vc.py -- 0 1 0 ply
#

import os
import sys
import bpy
import time
from glob import glob
import numpy as np


# exit('logwell')


# easy to test in blender "Scripting"
if 1:
    index_begin = 0
    index_end = 1
    device = '0'
    mode = 'ply'
else:
    argv = sys.argv
    try:
        index = argv.index("--") + 1
    except ValueError:
        index = len(argv)
    argv = argv[index:]

    index_begin = int(argv[0])
    index_end = int(argv[1]) if int(argv[1]) != -1 else 1E8
    device = str(argv[2]) if len(argv) == 3 else '0'
    mode = argv[3]

prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'CUDA'
prefs.get_devices()
cuda_devices = []
for d in prefs.devices:
    if d.type == 'CUDA':
        d.use = False
        cuda_devices.append(d)
cuda_devices[int(device)].use = True

if mode == 'ply':
    #
    # importing .ply takes a lot of time if the file is too large
    #
    path_meshes = ["data/Mesh_112_11_3.ply", ]
    decimate_ratio = 0.02  # we can extract a certain proportion of the mesh
    mesh_scale = 1, 1, 1


for index in range(index_begin, min(index_end, len(path_meshes))):
    path_mesh = path_meshes[index]
    print(index, path_mesh)

    if mode == 'ply':
        path_mesh_obj = path_mesh.rsplit('/', 1)[0] + '/vc_to_tex/mesh.obj'
        path_mesh_mtl = path_mesh.rsplit('/', 1)[0] + '/vc_to_tex/mesh.mtl'
        path_mesh_tex = path_mesh.rsplit('/', 1)[0] + '/vc_to_tex/tex.jpg'

    # if os.path.exists(path_mesh_tex):
    #     bpy.ops.wm.read_homefile()
    #     continue

    #
    # delete default objects(camera, cube, light)
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)

    #
    # import ply
    #
    bpy.ops.object.select_all(action='DESELECT')

    bpy.ops.import_mesh.ply(filepath=path_mesh)
    obj_mesh = bpy.context.selected_objects[0]
    # obj_mesh.name = 'name_mesh'
    obj_mesh.data.name = 'name_mesh'
    obj_mesh.pass_index = 9

    # bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')  # MEDIAN, BOUNDS

    obj_mesh.scale = mesh_scale
    obj_mesh.rotation_euler[0] = 1.5708  # 90 degree
    bpy.ops.object.shade_smooth()  # shade_flat, shade_smooth

    #
    # set material based vertex color
    #
    bpy.context.view_layer.objects.active = obj_mesh
    mat_default = bpy.data.materials['Material']
    mat_default.use_nodes = True
    node_tree_mat = mat_default.node_tree

    node_VertexColor = node_tree_mat.nodes.new('ShaderNodeVertexColor')
    node_tree_mat.links.new(node_VertexColor.outputs[0], node_tree_mat.nodes["Principled BSDF"].inputs[0])

    node_VertexColor.layer_name = "Col"
    node_tree_mat.nodes["Principled BSDF"].inputs[5].default_value = 0  # specular
    # node_tree_mat.nodes["Principled BSDF"].inputs[7].default_value = 1  # roughness

    obj_mesh.active_material = mat_default

    #
    # add 'Image Texture' node(for bake)
    #
    node_TexImage = node_tree_mat.nodes.new("ShaderNodeTexImage")
    img_tex = bpy.data.images.new('tex', width=1024, height=1024, alpha=False)
    node_TexImage.image = img_tex

    #
    # decimate
    #
    if decimate_ratio != -1:
        bpy.ops.object.modifier_add(type='DECIMATE')
        bpy.context.object.modifiers["Decimate"].ratio = decimate_ratio
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Decimate")

    #
    # render settings
    #
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'

    #
    # set background color
    #
    bpy.context.scene.view_settings.view_transform = 'Standard'
    # bpy.context.scene.world.use_nodes = False
    # bpy.context.scene.world.color = (1, 1, 1)
    bpy.context.scene.world.use_nodes = True
    node_Background = bpy.data.worlds["World"].node_tree.nodes["Background"]
    node_Background.inputs[0].default_value = (1, 1, 1, 1)
    node_Background.inputs[1].default_value = max(1, np.random.normal(2, 1, size=1))

    #
    # uv map
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.select_by_type(type='MESH')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type="FACE")  # VERT, EDGE, FACE
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.03)

    #
    # bake: vertex color to texture
    #
    # https://devtalk.blender.org/t/why-is-texture-baking-so-mind-meltingly-slow/5653/2
    #
    bpy.context.scene.render.tile_x = 2048  # 64
    bpy.context.scene.render.tile_y = 2048
    bpy.context.scene.cycles.samples = 32  # 256

    bpy.ops.object.mode_set(mode='OBJECT')
    # bpy.context.scene.cycles.bake_type = 'DIFFUSE'
    bpy.ops.object.bake(type='COMBINED')

    #
    # export tenture
    #
    # img_tex = bpy.data.images['tex']
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    img_tex.save_render(path_mesh_tex)

    bpy.ops.export_scene.obj(
        filepath=path_mesh_obj, check_existing=True,
        axis_forward='-Z', axis_up='Y', use_materials=True,
        keep_vertex_order=True, global_scale=1.0, path_mode='AUTO'
    )
    os.system("sed -i '$amap_Kd tex.jpg' " + path_mesh_mtl)
    bpy.ops.wm.read_homefile()

