# Verifies that Skin.fbx carries exactly Marta's native skeleton (names,
# hierarchy, rest positions) and that every skin weight targets one of its bones.
import bpy, sys, json
import numpy as np
from mathutils import Matrix
fbx, skel = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx, automatic_bone_orientation=False)
native = json.load(open(skel))['bones']
C = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
bones = {b.name: b for b in arm.data.bones}
errors = []
if set(bones) != {n['name'] for n in native}:
    errors.append('name mismatch: missing %s extra %s' % ({n['name'] for n in native} - set(bones), set(bones) - {n['name'] for n in native}))
maxd = 0.
for n in native:
    b = bones.get(n['name'])
    if not b: continue
    if (b.parent.name if b.parent else None) != (n['parent'] or None) and n['parent']:
        errors.append('parent mismatch ' + n['name'])
    p = (arm.matrix_world @ b.head_local)
    q = C.to_3x3() @ Matrix(n['world']).translation
    maxd = max(maxd, (p - q).length)
for o in bpy.data.objects:
    if o.type == 'MESH':
        bad = [g.name for g in o.vertex_groups if g.name not in bones]
        unweighted = sum(1 for v in o.data.vertices if not v.groups)
        maxinf = max(len(v.groups) for v in o.data.vertices)
        print('MESH', o.name, 'verts', len(o.data.vertices), 'groups', len(o.vertex_groups), 'unknown', bad, 'unweighted', unweighted, 'max influences', maxinf)
        if bad or unweighted: errors.append('bad weights in ' + o.name)
print('BONES', len(bones), 'max joint position error (m)', round(maxd, 6))
if maxd > .001: errors.append('joint positions differ')
print('SKELETON_OK' if not errors else 'SKELETON_FAIL ' + '; '.join(errors))
