# Bone-heat weights, executed inside step3_rig_marta.py after the skeleton fit
# when the source has no usable skin weights. Bone heat only lets a vertex
# depend on bones it can "see" through the mesh, so the torso side and the
# armpit never follow the arm (no shoulder triangles).
child = {'Hips': 'Spine', 'Spine': 'Spine1', 'Spine1': 'Neck', 'Neck': 'Head'}
for s in ('Left', 'Right'):
    for a, b in (('Shoulder', 'Arm'), ('Arm', 'ForeArm'), ('ForeArm', 'Hand'), ('Hand', 'HandMiddle1'),
                 ('UpLeg', 'Leg'), ('Leg', 'Foot'), ('Foot', 'ToeBase'), ('ToeBase', 'ToeBase_END')):
        child[s + a] = s + b
    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        for k in (1, 2, 3):
            child[f'{s}Hand{f}{k}'] = f'{s}Hand{f}{k + 1}'
HS = 10.
hd = bpy.data.armatures.new('HeatRig'); ho = bpy.data.objects.new('HeatRig', hd)
bpy.context.scene.collection.objects.link(ho)
bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = ho; ho.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in list(child) + ['Head']:
    # Heat is solved at 10x scale: Blender's solver fails on metre-sized characters.
    b = hd.edit_bones.new(n); b.head = ad.bones[n].head_local * HS
    t = (ad.bones[child[n]].head_local if n in child else ad.bones[n].head_local + Vector((0, 0, .18))) * HS
    b.tail = t if (t - b.head).length > .005 * HS else b.head + Vector((0, 0, .02 * HS))
bpy.ops.object.mode_set(mode='OBJECT')
# Bone heat needs a closed surface; generated meshes overlap and are open.
# Solve it on a watertight voxel proxy and copy the weights back by proximity.
hm = mesh.copy(); hm.data = mesh.data.copy(); bpy.context.scene.collection.objects.link(hm)
hm.vertex_groups.clear(); hm.data.transform(Matrix.Scale(HS, 4))
bpy.ops.object.select_all(action='DESELECT'); hm.select_set(True); bpy.context.view_layer.objects.active = hm
rm = hm.modifiers.new('Proxy', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = .008 * HS; rm.adaptivity = 0
bpy.ops.object.modifier_apply(modifier=rm.name)
print('HEAT_PROXY vertices', len(hm.data.vertices), flush=True)
bpy.ops.object.select_all(action='DESELECT'); hm.select_set(True); ho.select_set(True)
bpy.context.view_layer.objects.active = ho
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
hn = [g.name for g in hm.vertex_groups]
from mathutils.kdtree import KDTree
proxy_w = [{hn[g.group]: g.weight for g in v.groups if g.weight > 1e-4} for v in hm.data.vertices]
pkd = KDTree(len(hm.data.vertices))
for v in hm.data.vertices: pkd.insert(v.co, v.index)
pkd.balance()
segs = {n: (np.array(hd.bones[n].head_local) / HS, np.array(hd.bones[n].tail_local) / HS) for n in hd.bones.keys()}
def nearest_bone(p):
    best, bn = 1e9, 'Hips'
    for n, (a, b) in segs.items():
        ab = b - a; t = np.clip((p - a) @ ab / max(ab @ ab, 1e-9), 0, 1); d = np.linalg.norm(p - (a + t * ab))
        if d < best: best, bn = d, n
    return bn
per_vertex, fallback = [], 0
for v in mesh.data.vertices:
    # Blend the 4 nearest proxy vertices for smooth weights on the real mesh.
    w = {}
    near = pkd.find_n(v.co * HS, 4); tot = 0.
    for _, j, d in near:
        k = 1. / (d + .002 * HS); tot += k
        for n, x in proxy_w[j].items(): w[n] = w.get(n, 0.) + x * k
    w = {n: x / tot for n, x in w.items() if x / tot > 1e-4} if tot else {}
    if not w:
        w = {nearest_bone(np.array(v.co)): 1.}; fallback += 1
    per_vertex.append(w)
print('HEAT_WEIGHTS vertices', len(per_vertex), 'fallback', fallback, flush=True)

# --- Clean-up for the torso: the back must not follow the arms or legs ------
# Bone heat can leak arm weights into the back and shoulder blades and leg
# weights above the hips; in a fight the spine then twists unnaturally.
P = np.array([tuple(v.co) for v in mesh.data.vertices])
B = lambda n: np.array(ad.bones[n].head_local)
def seg_dist(p, a, b):
    ab = b - a; t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
hip_z = (B('LeftUpLeg')[2] + B('RightUpLeg')[2]) / 2
chest_z = B('Spine1')[2]
moved_arm = moved_leg = 0
for s in ('Left', 'Right'):
    tip = np.array(hd.bones[s + 'HandMiddle3'].tail_local) / HS
    d_arm = np.minimum.reduce([seg_dist(P, B(s + 'Arm'), B(s + 'ForeArm')),
                               seg_dist(P, B(s + 'ForeArm'), B(s + 'Hand')),
                               seg_dist(P, B(s + 'Hand'), tip)])
    # Full arm influence within ~9 cm of the arm bones, none beyond ~15 cm.
    keep = np.clip((.15 - d_arm) / .06, 0, 1); keep = keep * keep * (3 - 2 * keep)
    for i, w in enumerate(per_vertex):
        removed = 0.
        for n in list(w):
            if n.startswith(s) and ('Arm' in n or 'Hand' in n):
                removed += w[n] * (1 - keep[i]); w[n] *= keep[i]
        if removed > 1e-4:
            moved_arm += 1
            tgt = 'Spine1' if P[i, 2] > chest_z - .05 else 'Spine'
            w[tgt] = w.get(tgt, 0.) + removed
    for i, w in enumerate(per_vertex):
        if P[i, 2] > hip_z + .06:
            removed = sum(w.pop(n) for n in list(w) if n.startswith(s) and ('Leg' in n or 'Foot' in n or 'Toe' in n))
            if removed > 1e-4:
                moved_leg += 1; w['Hips'] = w.get('Hips', 0.) + removed
# Smooth trunk weights between neighbours so spine bends stay continuous.
adj = [[] for _ in range(len(P))]
for e in mesh.data.edges:
    a, b = e.vertices; adj[a].append(b); adj[b].append(a)
TRUNK = {'Hips', 'Spine', 'Spine1', 'Neck'}
trunk = [i for i in range(len(P)) if hip_z - .10 < P[i, 2] < B('Neck')[2] + .02
         and sum(x for n, x in per_vertex[i].items() if n in TRUNK) > .6]
for _ in range(4):
    new = {}
    for i in trunk:
        if not adj[i]: continue
        acc = {n: x * .5 for n, x in per_vertex[i].items()}
        share = .5 / len(adj[i])
        for j in adj[i]:
            for n, x in per_vertex[j].items(): acc[n] = acc.get(n, 0.) + x * share
        new[i] = acc
    for i, acc in new.items():
        tot = sum(acc.values()); per_vertex[i] = {n: x / tot for n, x in acc.items() if x / tot > 1e-4}
print('TORSO_CLEANUP arm_vertices', moved_arm, 'leg_vertices', moved_leg, 'smoothed', len(trunk), flush=True)
bpy.data.objects.remove(hm); bpy.data.objects.remove(ho)
