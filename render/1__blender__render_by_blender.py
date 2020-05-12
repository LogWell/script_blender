# /home/luojinhao/blender-2.82-linux64/blender --background --python 1__blender__render_by_blender.py -- 0 1 0 tex


import os
import sys
from glob import glob
import numpy as np
import bpy


# exit('+++++ exit by logwell -----')


if 0:
    index_begin = 0
    index_end = 1
    device = '0'
    mode = 'tex'
else:
    argv = sys.argv
    try:
        index = argv.index("--") + 1
    except ValueError:
        index = len(argv)
    argv = argv[index:]
    index_begin = int(argv[0])  # 0
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

#
# gather objs
#
if mode == 'tex':
    path_meshes = ['mesh.obj']  # with texture
if mode == 'vc':
    path_meshes = ['mesh.ply']  # only vertex color

#
# env texture
#
path_hdris = sorted(glob('data/script_blender/hdri/hdr_2k/*'))

#
# objects
#
for n_mesh in range(index_begin, min(index_end, len(path_meshes))):
    # np.random.seed(n_mesh)

    path_mesh = path_meshes[n_mesh]
    info_random_hdri = np.random.choice(path_hdris)
    path_hdri = info_random_hdri

    #
    # delete all
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=True)

    #
    # import mesh
    #
    # with tex
    if mode == 'tex':
        path_base = '/home/ljh/Downloads/temp'
        bpy.ops.object.select_all(action='DESELECT')

        bpy.ops.import_scene.obj(filepath=path_mesh, split_mode='OFF')  # , axis_forward='X', axis_up='Y')
        obj_mesh = bpy.context.selected_objects[0]
        # obj_mesh.name = 'name_mesh'
        obj_mesh.data.name = 'name_mesh'
        obj_mesh.pass_index = 9

        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')  # MEDIAN, BOUNDS
        obj_mesh.scale = 0.001, 0.001, 0.001
        bpy.ops.object.shade_smooth()

    # only vertex color
    if mode == 'vc':
        path_base = '/home/ljh/Downloads/temp'
        bpy.ops.object.select_all(action='DESELECT')

        bpy.ops.import_mesh.ply(filepath=path_mesh)
        obj_mesh = bpy.context.selected_objects[0]
        # obj_mesh.name = 'name_mesh'
        obj_mesh.data.name = 'name_mesh'
        obj_mesh.pass_index = 9

        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='BOUNDS')  # MEDIAN, BOUNDS

        obj_mesh.scale = 0.001, 0.001, 0.001
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
    # Camera
    #
    bpy.ops.object.camera_add(
        enter_editmode=False, align='VIEW',
        location=(0, -3, 0),  # info_random_camera,
        rotation=(np.pi / 2, 0, 0)
    )
    bpy.context.scene.camera = bpy.context.object

    object_camera = bpy.data.objects['Camera']
    object_camera.data.lens_unit = 'FOV'
    object_camera.data.angle = np.pi / 4.
    object_camera.data.clip_start = 0.01
    object_camera.data.clip_end = 10000

    object_camera.data.sensor_fit = 'HORIZONTAL'  # 'AUTO', 'VERTICAL'
    object_camera.data.sensor_width = 36
    object_camera.data.sensor_height = 36

    #
    # render settings
    #
    bpy.context.scene.render.resolution_x = 512
    bpy.context.scene.render.resolution_y = 512
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'

    bpy.context.scene.render.film_transparent = False
    # bpy.context.scene.view_layers["View Layer"].cycles.use_denoising = True  # too slow
    # bpy.context.scene.view_layers["View Layer"].cycles.denoising_strength = 1
    # bpy.context.scene.view_layers["View Layer"].cycles.denoising_feature_strength = 0.3
    bpy.context.scene.view_layers["View Layer"].use_pass_object_index = True
    bpy.context.scene.view_layers["View Layer"].use_pass_normal = True

    #
    # set background color
    #
    bpy.context.scene.view_settings.view_transform = 'Standard'
    bpy.context.scene.world.use_nodes = False
    bpy.context.scene.world.color = (1, 1, 1)  #  (0, 0, 0), (1, 1, 1)

    #
    # environment texture: https://docs.blender.org/api/current/bpy.types.html
    #
    if 1:
        bpy.context.scene.world.use_nodes = True
        node_tree_world = bpy.context.scene.world.node_tree
        # query info: node_tree_world.nodes.items()

        node_TexCoord = node_tree_world.nodes.new('ShaderNodeTexCoord')
        node_Mapping = node_tree_world.nodes.new('ShaderNodeMapping')
        node_TexEnvironment = node_tree_world.nodes.new('ShaderNodeTexEnvironment')

        node_tree_world.links.new(node_TexCoord.outputs[0], node_Mapping.inputs[0])
        node_tree_world.links.new(node_Mapping.outputs[0], node_TexEnvironment.inputs[0])
        node_tree_world.links.new(node_TexEnvironment.outputs[0], node_tree_world.nodes["Background"].inputs[0])
        node_tree_world.links.new(
            node_tree_world.nodes["Background"].outputs[0], node_tree_world.nodes["World Output"].inputs[0]
        )

        # https://www.desmos.com/calculator/0x3rpqtgrx
        info_random_rx = np.random.normal(np.radians(-7.5), np.radians(1.2), size=1)
        info_random_rz = np.random.uniform(0, 2 * np.pi, size=1)
        node_Mapping.inputs[2].default_value[0] = info_random_rx
        node_Mapping.inputs[2].default_value[2] = info_random_rz
        node_TexEnvironment.image = bpy.data.images.load(path_hdri)

    #
    # compositor
    #
    if 1:
        bpy.context.scene.use_nodes = True
        node_tree = bpy.context.scene.node_tree
        for n in node_tree.nodes:
            node_tree.nodes.remove(n)
        # https://docs.blender.org/api/current/bpy.types.html
        node_RLayers = node_tree.nodes.new('CompositorNodeRLayers')

        #
        # mask
        #
        if 1:
            node_IDMask = node_tree.nodes.new('CompositorNodeIDMask')
            node_IDMask.index = 9  # object_mesh.pass_index = 9
            node_IDMask.use_antialiasing = True

            node_OutputFile_img_m = node_tree.nodes.new('CompositorNodeOutputFile')
            node_OutputFile_img_m.base_path = path_base
            node_OutputFile_img_m.file_slots['Image'].path = 'blender_m_##'
            node_OutputFile_img_m.format.file_format = 'PNG'
            node_OutputFile_img_m.format.color_mode = 'BW'  # 'RGBA'
            node_OutputFile_img_m.format.compression = 20

            node_tree.links.new(node_RLayers.outputs['IndexOB'], node_IDMask.inputs[0])
            node_tree.links.new(node_IDMask.outputs[0], node_OutputFile_img_m.inputs[0])
        #
        # alpha
        #
        if 0:
            # bpy.context.scene.render.film_transparent = True
            node_OutputFile_img_ma = node_tree.nodes.new('CompositorNodeOutputFile')
            node_OutputFile_img_ma.base_path = path_base
            node_OutputFile_img_ma.file_slots['Image'].path = 'blender_ma_##'
            node_OutputFile_img_ma.format.file_format = 'PNG'
            node_OutputFile_img_ma.format.color_mode = 'RGBA'
            node_OutputFile_img_ma.format.compression = 20

            node_tree.links.new(node_RLayers.outputs['Alpha'], node_OutputFile_img_ma.inputs[0])
        #
        # normal
        #
        if 0:
            node_OutputFile_img_n = node_tree.nodes.new('CompositorNodeOutputFile')
            node_OutputFile_img_n.base_path = path_base
            node_OutputFile_img_n.file_slots['Image'].path = 'blender_n_##'
            node_OutputFile_img_n.format.file_format = 'OPEN_EXR'
            node_OutputFile_img_n.format.color_mode = 'RGB'
            node_tree.links.new(node_RLayers.outputs['Normal'], node_OutputFile_img_n.inputs[0])

            # True Normal: https://blender.stackexchange.com/a/21199
            # Texture Coord & Geometry

            # https://blender.stackexchange.com/a/14063
            # node_MULTIPLY = node_tree.nodes.new("CompositorNodeMixRGB")
            # node_MULTIPLY.blend_type = 'MULTIPLY'
            # node_MULTIPLY.inputs[2].default_value = 0.5, 0.5, 0.5, 1
            #
            # node_ADD = node_tree.nodes.new("CompositorNodeMixRGB")
            # node_ADD.blend_type = 'ADD'
            # node_ADD.inputs[2].default_value = 0.5, 0.5, 0.5, 1
            #
            # node_Invert = node_tree.nodes.new("CompositorNodeInvert")
            #
            # node_tree.links.new(node_RLayers.outputs['Normal'], node_MULTIPLY.inputs[1])
            # node_tree.links.new(node_MULTIPLY.outputs[0], node_ADD.inputs[1])
            # node_tree.links.new(node_ADD.outputs[0], node_Invert.inputs[1])
            # node_tree.links.new(node_Invert.outputs[0], node_OutputFile_img_n.inputs[0])

        #
        # depth
        # https://blender.stackexchange.com/questions/130970/cycles-generates-distorted-depth
        #
        if 1:
            node_OutputFile_img_d = node_tree.nodes.new('CompositorNodeOutputFile')
            node_OutputFile_img_d.base_path = path_base
            node_OutputFile_img_d.file_slots['Image'].path = 'blender_d_##'
            node_OutputFile_img_d.format.file_format = 'OPEN_EXR'
            node_OutputFile_img_d.format.color_mode = 'RGB'
            node_tree.links.new(node_RLayers.outputs['Depth'], node_OutputFile_img_d.inputs[0])

        #
        # color
        #
        if 1:
            # in compositor
            if 1:
                node_OutputFile_img_c = node_tree.nodes.new('CompositorNodeOutputFile')
                node_OutputFile_img_c.base_path = path_base
                node_OutputFile_img_c.file_slots['Image'].path = 'blender_c_##'
                node_OutputFile_img_c.format.file_format = 'JPEG'  # 'PNG'
                node_OutputFile_img_c.format.color_mode = 'RGB'
                node_OutputFile_img_c.format.compression = 20
                node_tree.links.new(node_RLayers.outputs['Image'], node_OutputFile_img_c.inputs[0])
            #
            # in default, or generate /tmp/.png
            # if true, will overwrite next render result
            #
            if 0:
                bpy.context.scene.render.image_settings.file_format = 'PNG'
                bpy.context.scene.render.image_settings.color_mode = 'RGB'  # RGBA
                bpy.context.scene.render.image_settings.compression = 20
                bpy.context.scene.render.filepath = path_base + '/blender_c_01.png'

            # convert background to white/black
            if 1:
                node_OutputFile_img_cw1 = node_tree.nodes.new('CompositorNodeOutputFile')
                node_OutputFile_img_cw1.base_path = path_base
                node_OutputFile_img_cw1.file_slots['Image'].path = 'blender_cw_##'
                node_OutputFile_img_cw1.format.file_format = 'PNG'
                node_OutputFile_img_cw1.format.color_mode = 'RGB'

                node_Math = node_tree.nodes.new('CompositorNodeMath')
                node_Math.operation = 'SUBTRACT'
                node_Math.inputs[0].default_value = 1

                node_SetAlpha = node_tree.nodes.new('CompositorNodeSetAlpha')
                node_SetAlpha.inputs[0].default_value = (1, 1, 1, 1)

                node_AlphaOver = node_tree.nodes.new('CompositorNodeAlphaOver')
                node_AlphaOver.use_premultiply = True

                node_tree.links.new(node_IDMask.outputs[0], node_Math.inputs[1])
                node_tree.links.new(node_Math.outputs[0], node_SetAlpha.inputs[1])
                node_tree.links.new(node_RLayers.outputs['Image'], node_AlphaOver.inputs[1])
                node_tree.links.new(node_SetAlpha.outputs[0], node_AlphaOver.inputs[2])
                node_tree.links.new(node_AlphaOver.outputs[0], node_OutputFile_img_cw1.inputs[0])

    bpy.ops.render.render(write_still=True)
    np.savez(
        path_base + '/info_random.npz',
        info_random_hdri=info_random_hdri,
        info_random_rx=info_random_rx,
        info_random_rz=info_random_rz,
    )

    #
    # compositor for normal
    #
    if 1:
        bpy.context.scene.use_nodes = True
        node_tree = bpy.context.scene.node_tree
        for n in node_tree.nodes:
            node_tree.nodes.remove(n)
        node_RLayers = node_tree.nodes.new('CompositorNodeRLayers')

        #
        # normal
        #
        node_IDMask = node_tree.nodes.new('CompositorNodeIDMask')
        node_IDMask.index = 9  # object_mesh.pass_index = 9
        node_IDMask.use_antialiasing = True
        node_tree.links.new(node_RLayers.outputs['IndexOB'], node_IDMask.inputs[0])

        node_OutputFile_img_cw2 = node_tree.nodes.new('CompositorNodeOutputFile')
        node_OutputFile_img_cw2.base_path = path_base
        node_OutputFile_img_cw2.file_slots['Image'].path = 'blender_n_##'
        node_OutputFile_img_cw2.format.file_format = 'OPEN_EXR'
        # node_OutputFile_img_cw2.format.file_format = 'PNG'
        node_OutputFile_img_cw2.format.color_mode = 'RGB'

        node_Math = node_tree.nodes.new('CompositorNodeMath')
        node_Math.operation = 'SUBTRACT'
        node_Math.inputs[0].default_value = 1

        node_SetAlpha = node_tree.nodes.new('CompositorNodeSetAlpha')
        node_SetAlpha.inputs[0].default_value = (1, 1, 1, 1)

        node_AlphaOver = node_tree.nodes.new('CompositorNodeAlphaOver')
        node_AlphaOver.use_premultiply = True

        node_tree.links.new(node_IDMask.outputs[0], node_Math.inputs[1])
        node_tree.links.new(node_Math.outputs[0], node_SetAlpha.inputs[1])
        node_tree.links.new(node_RLayers.outputs['Image'], node_AlphaOver.inputs[1])
        node_tree.links.new(node_SetAlpha.outputs[0], node_AlphaOver.inputs[2])
        node_tree.links.new(node_AlphaOver.outputs[0], node_OutputFile_img_cw2.inputs[0])

    #
    # shader for normal rendering: https://blender.stackexchange.com/a/157279
    #
    if 1:
        # bpy.ops.material.new()
        # mat_normal = bpy.data.materials['Material.001']
        mat_normal = bpy.data.materials['Material']
        mat_normal.name = "mat_normal"
        obj_mesh.active_material = mat_normal

        mat_normal.use_nodes = True
        node_tree_object = mat_normal.node_tree
        for n in node_tree_object.nodes:
            node_tree_object.nodes.remove(n)

        node_tree_object__Geometry = node_tree_object.nodes.new("ShaderNodeNewGeometry")

        node_tree_object__VectorTransform = node_tree_object.nodes.new("ShaderNodeVectorTransform")
        node_tree_object__VectorTransform.vector_type = 'VECTOR'  # 'NORMAL'
        node_tree_object__VectorTransform.convert_from = 'WORLD'
        node_tree_object__VectorTransform.convert_to = 'CAMERA'

        node_tree_object__SeparateXYZ = node_tree_object.nodes.new("ShaderNodeSeparateXYZ")

        node_tree_object__M0 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__M0.operation = 'MULTIPLY'
        node_tree_object__M0.inputs[1].default_value = 0.5
        node_tree_object__M1 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__M1.operation = 'MULTIPLY'
        node_tree_object__M1.inputs[1].default_value = 0.5
        node_tree_object__M2 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__M2.operation = 'MULTIPLY'
        node_tree_object__M2.inputs[1].default_value = -0.5  # -----+++++----- #

        node_tree_object__A0 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__A0.operation = 'ADD'
        node_tree_object__A0.inputs[1].default_value = 0.5
        node_tree_object__A1 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__A1.operation = 'ADD'
        node_tree_object__A1.inputs[1].default_value = 0.5
        node_tree_object__A2 = node_tree_object.nodes.new("ShaderNodeMath")
        node_tree_object__A2.operation = 'ADD'
        node_tree_object__A2.inputs[1].default_value = 0.5

        node_tree_object__CombineXYZ = node_tree_object.nodes.new("ShaderNodeCombineXYZ")
        node_tree_object__LightPath = node_tree_object.nodes.new("ShaderNodeLightPath")
        node_tree_object__BsdfTransparent = node_tree_object.nodes.new("ShaderNodeBsdfTransparent")
        node_tree_object__Emission = node_tree_object.nodes.new("ShaderNodeEmission")
        node_tree_object__MixShader = node_tree_object.nodes.new("ShaderNodeMixShader")
        node_tree_object__OutputMaterial = node_tree_object.nodes.new("ShaderNodeOutputMaterial")

        node_tree_object.links.new(node_tree_object__Geometry.outputs['Normal'],
                                   node_tree_object__VectorTransform.inputs[0])
        node_tree_object.links.new(node_tree_object__VectorTransform.outputs[0],
                                   node_tree_object__SeparateXYZ.inputs[0])

        node_tree_object.links.new(node_tree_object__SeparateXYZ.outputs[0], node_tree_object__M0.inputs[0])
        node_tree_object.links.new(node_tree_object__SeparateXYZ.outputs[1], node_tree_object__M1.inputs[0])
        node_tree_object.links.new(node_tree_object__SeparateXYZ.outputs[2], node_tree_object__M2.inputs[0])
        node_tree_object.links.new(node_tree_object__M0.outputs[0], node_tree_object__A0.inputs[0])
        node_tree_object.links.new(node_tree_object__M1.outputs[0], node_tree_object__A1.inputs[0])
        node_tree_object.links.new(node_tree_object__M2.outputs[0], node_tree_object__A2.inputs[0])
        node_tree_object.links.new(node_tree_object__A0.outputs[0], node_tree_object__CombineXYZ.inputs[0])
        node_tree_object.links.new(node_tree_object__A1.outputs[0], node_tree_object__CombineXYZ.inputs[1])
        node_tree_object.links.new(node_tree_object__A2.outputs[0], node_tree_object__CombineXYZ.inputs[2])

        node_tree_object.links.new(node_tree_object__CombineXYZ.outputs[0], node_tree_object__Emission.inputs[0])
        node_tree_object.links.new(node_tree_object__LightPath.outputs[0], node_tree_object__MixShader.inputs[0])
        node_tree_object.links.new(node_tree_object__BsdfTransparent.outputs[0],
                                   node_tree_object__MixShader.inputs[1])
        node_tree_object.links.new(node_tree_object__Emission.outputs[0], node_tree_object__MixShader.inputs[2])
        node_tree_object.links.new(node_tree_object__MixShader.outputs[0],
                                   node_tree_object__OutputMaterial.inputs[0])

    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.read_homefile()