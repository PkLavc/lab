import bpy
from mathutils import Matrix, Vector
from pathlib import Path

# Builds the runtime model from the supplied Snoop Dogg bundle. The source
# export remains outside the repository; only the compact final GLB is served.
SOURCE = Path(r"C:\tmp\snoop-ripped\Assets")
OUTPUT = Path(__file__).parent / "Smoke-bust.glb"
MESH = SOURCE / "Mesh"

bpy.ops.wm.read_factory_settings(use_empty=True)


def import_gltf(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [obj for obj in bpy.context.scene.objects if obj not in before]


def first_mesh(objects):
    return next(obj for obj in objects if obj.type == "MESH")


def material(name, color, roughness=.62, alpha=1, texture_file=None, tint_texture=False):
    item = bpy.data.materials.new(name)
    item.use_nodes = True
    bsdf = item.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, alpha)
    bsdf.inputs["Roughness"].default_value = roughness
    if texture_file:
        image = bpy.data.images.load(str(SOURCE / texture_file), check_existing=True)
        image.scale(768, 768)
        texture = item.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image = image
        if tint_texture:
            # The Call of Duty files are shader masks. Bake the supplied tint
            # into a compact color image so the portable glTF has the intended
            # skin/leather hue without its proprietary shader.
            pixels = list(image.pixels[:])
            for index in range(0, len(pixels), 4):
                pixels[index] *= color[0]
                pixels[index + 1] *= color[1]
                pixels[index + 2] *= color[2]
            baked = bpy.data.images.new(f"{name} baked", image.size[0], image.size[1], alpha=True)
            baked.pixels.foreach_set(pixels)
            texture.image = baked
        item.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
        item.surface_render_method = 'DITHERED'
    return item


SKIN = material("Smoke skin", (0.32, 0.18, 0.095), .76, texture_file="cm_t_face_00_00_00.png", tint_texture=True)
EYE = material("Smoke eye white", (0.84, 0.72, 0.48), .28)
IRIS = material("Smoke iris", (0.028, 0.012, 0.004), .2)
BEARD = material("Smoke beard", (0.012, 0.006, 0.002), .88, texture_file="beard_dif.png", tint_texture=True)
TEETH = material("Smoke teeth", (0.68, 0.56, 0.37), .44)
JACKET = material("Smoke jacket", (0.020, 0.024, 0.030), .32, texture_file="Jacket_dif2.png", tint_texture=True)
UNDER = material("Smoke shirt", (0.050, 0.038, 0.024), .72, texture_file="Shirt_dif.png", tint_texture=True)
PANTS = material("Smoke pants", (0.010, 0.012, 0.016), .72)
SHOES = material("Smoke shoes", (0.008, 0.007, 0.006), .48)
HAT = material("Smoke hat", (0.018, 0.030, 0.022), .53)
GLASS = material("Smoke glasses", (0.004, 0.006, 0.008), .16, .58)
HAIR = material("Smoke hair", (0.004, 0.002, 0.001), .9)
GOLD = material("Smoke gold", (0.58, 0.30, 0.045), .28)
CIGAR = material("Smoke cigar", (0.14, 0.042, 0.008), .82)
EMBER = material("Smoke ember", (0.9, 0.06, 0.004), .34)
FUR = material("Smoke fur", (0.48, 0.35, 0.16), .93)


def apply_material(obj, item, name):
    obj.name = name
    obj.data.materials.clear()
    obj.data.materials.append(item)
    return obj


def import_body_part(filename, item, name):
    obj = apply_material(first_mesh(import_gltf(MESH / filename)), item, name)
    obj.parent = bpy.data.objects["cm_J_Root"]
    obj.matrix_parent_inverse = obj.parent.matrix_world.inverted()
    return obj


def attach_head_part(filename, target_name, item, name, pivot=None):
    obj = apply_material(first_mesh(import_gltf(MESH / filename)), item, name)
    target = bpy.data.objects[target_name]
    if pivot is not None:
        # Loose facial meshes arrive in head-space. Re-center their vertices at
        # their original game pivot so rotations happen at the eye/jaw itself.
        obj.data.transform(Matrix.Translation(-Vector(pivot)))
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.parent = target
    obj.matrix_parent_inverse.identity()
    return obj


# Full original body rig and complete clothing/shoe geometry.
import_gltf(SOURCE / "snoop_dogg_clothes.glb")
for filename, item, name in [
    ("O_body.glb", SKIN, "Smoke body"),
    ("Outfit_under_u.001.glb", PANTS, "Smoke pants"),
    ("Outfit_under_u.001_0.glb", UNDER, "Smoke shirt"),
    ("Outfit_knife_u.glb", JACKET, "Smoke accessory"),
    ("Outfit_Shoes_u.glb", SHOES, "Smoke shoes"),
    ("snoop_jacket_u.glb", JACKET, "Smoke jacket trim"),
    ("snoop_jacket_u_0.glb", JACKET, "Smoke jacket belt"),
    ("snoop_jacket_u_1.glb", JACKET, "Smoke jacket buckle"),
    ("snoop_jacket_u_2.glb", JACKET, "Smoke jacket"),
]:
    import_body_part(filename, item, name)

# The supplied head bundle is a separate facial hierarchy. It attaches to the
# original full-body head bone, then every visible head part follows it.
head_nodes = import_gltf(SOURCE / "p_cm_head_01.glb")
head_root = next(obj for obj in head_nodes if obj.name == "p_cm_head_01")
head_root.parent = bpy.data.objects["cm_J_Head"]
head_root.matrix_parent_inverse.identity()
head_root.location = (0, 0, 0)
head_root.scale = (1.9, 1.9, 1.9)

attach_head_part("cm_O_head.glb", "cm_J_FaceRoot", SKIN, "Smoke head")
attach_head_part("O_hige00.glb", "cm_J_MouthLow", BEARD, "Smoke beard", (0, -0.1008, -0.0006))
attach_head_part("cm_O_ha.glb", "cm_J_MouthLow", TEETH, "Smoke teeth", (0, -0.1008, -0.0006))


def eye(target_name, side):
    target = bpy.data.objects[target_name]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=.018)
    globe = bpy.context.object
    globe.name = f"Smoke {side} eye"
    globe.data.materials.append(EYE)
    globe.parent = target
    globe.matrix_parent_inverse.identity()
    globe.location = (0, 0, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=.008)
    pupil = bpy.context.object
    pupil.name = f"Smoke {side} pupil"
    pupil.data.materials.append(IRIS)
    pupil.parent = target
    pupil.matrix_parent_inverse.identity()
    pupil.location = (0, -.016, 0)


eye("cm_J_Eye_s_L", "left")
eye("cm_J_Eye_s_R", "right")

# Original Snoop head accessories. Their mesh coordinates are local to the
# named attachment pivots in the supplied facial hierarchy.
attach_head_part("Snoop Dogg_Hat.glb", "N_Head", HAT, "Smoke hat bandana")
attach_head_part("Snoop Dogg_Hat_0.glb", "N_Head", HAT, "Smoke hat")
attach_head_part("Snoop Dogg_Glasses_u.glb", "N_Megane", GLASS, "Smoke glasses")

# The source pack references a base-game hair mesh that is not bundled. A small
# low-poly hair cap supplies that missing visible geometry, parented to the
# exact original head pivot, without adding a heavy external asset.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12)
hair = bpy.context.object
hair.name = "Smoke hair"
hair.scale = (.096, .09, .072)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
hair.location = (0, .012, .095)
hair.data.materials.append(HAIR)
hair.parent = bpy.data.objects["N_Head"]
hair.matrix_parent_inverse.identity()

# Visible braided side strands, also parented to the original head pivot.
for side in (-1, 1):
    for offset in (.055, .078):
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=.009, depth=.14)
        braid = bpy.context.object
        braid.name = "Smoke braid"
        braid.data.materials.append(HAIR)
        braid.parent = bpy.data.objects["N_Head"]
        braid.matrix_parent_inverse.identity()
        braid.location = (side * offset, .018, .042)


def face_box(name, location, scale, item, bevel=0):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.location = location
    obj.data.materials.append(item)
    if bevel:
        modifier = obj.modifiers.new("soft edges", 'BEVEL')
        modifier.width = bevel
        modifier.segments = 3
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.parent = bpy.data.objects["cm_J_FaceRoot"]
    obj.matrix_parent_inverse.identity()
    return obj


# The bundle's glasses material depends on a game shader AssetRipper cannot
# reproduce. Rebuild thin frames/lenses at the original eye plane.
for x in (-.038, .038):
    face_box("Smoke lens", (x, -.132, .081), (.028, .0028, .014), GLASS, .004)
    face_box("Smoke glasses top", (x, -.136, .096), (.030, .003, .002), GOLD, .0015)
    face_box("Smoke glasses bottom", (x, -.136, .066), (.030, .003, .002), GOLD, .0015)
    face_box("Smoke glasses side", (x - .028, -.136, .081), (.002, .003, .017), GOLD, .0015)
    face_box("Smoke glasses side", (x + .028, -.136, .081), (.002, .003, .017), GOLD, .0015)
face_box("Smoke glasses bridge", (0, -.136, .081), (.009, .003, .0025), GOLD, .0015)

# Gold hat band and the characteristic cigar from the supplied presentation.
bpy.ops.mesh.primitive_torus_add(major_radius=.088, minor_radius=.004, major_segments=32, minor_segments=8)
hat_band = bpy.context.object
hat_band.name = "Smoke hat gold band"
hat_band.location = (0, .026, .118)
hat_band.data.materials.append(GOLD)
hat_band.parent = bpy.data.objects["N_Head"]
hat_band.matrix_parent_inverse.identity()

bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.006, depth=.060, rotation=(0, 1.5708, 0))
cigar = bpy.context.object
cigar.name = "Smoke cigar"
cigar.location = (.070, -.135, .011)
cigar.data.materials.append(CIGAR)
cigar.parent = bpy.data.objects["cm_J_MouthMove"]
cigar.matrix_parent_inverse.identity()
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.0064, depth=.006, rotation=(0, 1.5708, 0))
ember = bpy.context.object
ember.name = "Smoke cigar ember"
ember.location = (.104, -.135, .011)
ember.data.materials.append(EMBER)
ember.parent = bpy.data.objects["cm_J_MouthMove"]
ember.matrix_parent_inverse.identity()

for obj in bpy.context.scene.objects:
    if obj.type == "EMPTY":
        obj.empty_display_size = .001

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT), export_format="GLB", use_selection=True,
    export_yup=True, export_materials="EXPORT", export_image_format="AUTO",
    export_cameras=False, export_lights=False, export_animations=False,
    export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
)
print(f"Wrote {OUTPUT}")
