import bpy
from mathutils import Matrix, Vector
from pathlib import Path

# Produces the small runtime-only Snoop bust. Source assets are exported with
# AssetRipper into C:\tmp and remain outside the Lab repository.
SOURCE = Path(r"C:\tmp\snoop-ripped\Assets")
OUTPUT = Path(__file__).parent / "Smoke-bust.glb"

bpy.ops.wm.read_factory_settings(use_empty=True)


def import_gltf(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def first_mesh(objects):
    return next(obj for obj in objects if obj.type == "MESH")


def configure_material(obj, name, texture, color, roughness=0.62, use_texture=False):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    if use_texture and texture.exists():
        image = bpy.data.images.load(str(texture), check_existing=True)
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = image
        material.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.clear()
    obj.data.materials.append(material)


def attach(mesh, target_name, pivot=None):
    target = bpy.data.objects.get(target_name)
    if target is None:
        raise RuntimeError(f"Missing rig node: {target_name}")
    if pivot is None:
        mesh.parent = target
        mesh.matrix_parent_inverse = target.matrix_world.inverted()
        return
    # AssetRipper's loose mesh has vertices already in global character space.
    # Shift them around their actual pivot before parenting so eye/jaw rotations
    # use the original game's pivot rather than the scene origin.
    mesh.data.transform(Matrix.Translation(-Vector(pivot)))
    mesh.location = (0, 0, 0)
    mesh.rotation_euler = (0, 0, 0)
    mesh.parent = target
    mesh.matrix_parent_inverse.identity()


# Facial hierarchy, including the original eye/mouth pivots.
import_gltf(SOURCE / "p_cm_head_01.glb")

head = first_mesh(import_gltf(SOURCE / "Mesh" / "cm_O_head.glb"))
configure_material(head, "Smoke skin", SOURCE / "cm_t_face_00_00_00.png", (0.12, 0.047, 0.018), 0.76)
attach(head, "cm_J_FaceRoot")

left_eye = first_mesh(import_gltf(SOURCE / "Mesh" / "cm_O_eye_L.glb"))
right_eye = first_mesh(import_gltf(SOURCE / "Mesh" / "cm_O_eye_R.glb"))
for eye in (left_eye, right_eye):
    configure_material(eye, "Smoke eyes", SOURCE / "cm_t_eyewhite_01.png", (0.48, 0.20, 0.055), 0.34)
attach(left_eye, "cm_J_Eye_s_L", (0.0359, -0.0804, 0.0802))
attach(right_eye, "cm_J_Eye_s_R", (-0.0359, -0.0804, 0.0802))

beard = first_mesh(import_gltf(SOURCE / "Mesh" / "O_hige00.glb"))
configure_material(beard, "Smoke beard", SOURCE / "beard_dif.png", (0.007, 0.004, 0.002), 0.82)
attach(beard, "cm_J_MouthLow", (0, -0.1008, -0.0006))

teeth = first_mesh(import_gltf(SOURCE / "Mesh" / "cm_O_ha.glb"))
configure_material(teeth, "Smoke teeth", SOURCE / "Snoop_teeth_dif.png", (0.66, 0.53, 0.33), 0.48)
attach(teeth, "cm_J_MouthLow", (0, -0.1008, -0.0006))


for obj in bpy.context.scene.objects:
    if obj.type == "EMPTY":
        obj.empty_display_size = 0.001

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT),
    export_format="GLB",
    use_selection=True,
    export_yup=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_cameras=False,
    export_lights=False,
    export_animations=False,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
)
print(f"Wrote {OUTPUT}")
