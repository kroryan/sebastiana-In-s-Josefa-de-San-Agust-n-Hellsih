# Step 3: bind the textured mesh to Marta's native 68-joint skeleton.
#
# Marta's bones are moved/turned onto the joints of the source rig, the mesh is
# skinned with the source weights (renamed to Marta's bones), and then the
# skeleton is returned to Marta's native rest pose, carrying the mesh into
# Marta's bind space. Head and hat are split into a rigid Head-only part.
import bpy, os, sys, json, math
import numpy as np
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
BUILD, SKELETON = args[0], args[1]
OUT = os.path.join(BUILD, 'marta'); os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(BUILD, 'prepared.blend'))
mesh = bpy.data.objects['SebastianaBody']
J = {k: {'head': Vector(v['head']), 'tail': Vector(v['tail'])} for k, v in
     json.load(open(os.path.join(BUILD, 'source_joints.json'))).items()}

# --- Marta skeleton (same conversion as the Sebastiana build) -----------------
native = json.load(open(SKELETON))
C = Matrix(((-1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
ad = bpy.data.armatures.new('MartaSkeleton'); arm = bpy.data.objects.new('Armature', ad)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in native['bones']:
    b = ad.edit_bones.new(n['name']); b.length = .05
    W = Matrix(n['world']); R = C @ W.to_3x3().to_4x4() @ C.inverted(); R.translation = C.to_3x3() @ W.translation
    b.matrix = R
    if n['parent']: b.parent = ad.edit_bones[n['parent']]
bpy.ops.object.mode_set(mode='OBJECT')
original = {b.name: b.matrix_local.copy() for b in ad.bones}
origlen = {b.name: b.length for b in ad.bones}

# A model whose shoulders sit more than 4 cm away from Marta's is scaled as a
# whole to her shoulder height: proportions stay intact, nothing is stretched
# or squashed. Smaller differences are absorbed by the upper-body lift below.
src_shoulder = (J['LeftArm']['head'].z + J['RightArm']['head'].z) / 2
marta_shoulder = (original['LeftArm'].translation.z + original['RightArm'].translation.z) / 2
SCALE = marta_shoulder / src_shoulder if abs(src_shoulder - marta_shoulder) > .04 else 1.
if SCALE != 1.:
    mesh.data.transform(Matrix.Scale(SCALE, 4))
    for k in J: J[k] = {'head': J[k]['head'] * SCALE, 'tail': J[k]['tail'] * SCALE}
print('MODEL_SCALE', round(SCALE, 4), flush=True)

# The elbow is placed along the arm at Marta's own upper-arm/forearm split, so
# both segments stretch evenly (AI source rigs can misplace it).
for s in ('Left', 'Right'):
    a, hnd = J[s + 'Arm']['head'], J[s + 'Hand']['head']
    ma, mf, mh = original[s + 'Arm'].translation, original[s + 'ForeArm'].translation, original[s + 'Hand'].translation
    k = (mf - ma).length / ((mf - ma).length + (mh - mf).length)
    J[s + 'ForeArm'] = {'head': a.lerp(hnd, k), 'tail': hnd}
    print('ELBOW_MOVED', s, round(k, 3), flush=True)
# --- Fit Marta's joints to the source rig ------------------------------------
bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones
def H(n): return eb[n].head.copy()
def apply(n, M):
    for q in [eb[n]] + list(eb[n].children_recursive): q.matrix = M @ q.matrix
def move(n, target): apply(n, Matrix.Translation(Vector(target) - H(n)))
def turn(n, child, target):
    h = H(n); r = (H(child) - h).normalized().rotation_difference((Vector(target) - h).normalized())
    apply(n, Matrix.Translation(h) @ r.to_matrix().to_4x4() @ Matrix.Translation(-h))
def frame(d, l):
    d = d.normalized(); l = (l - d * l.dot(d)).normalized(); return Matrix((d, l, d.cross(l))).transposed()
def align_frame(n, d1, l1, d2, l2):
    h = H(n); R = frame(d2, l2) @ frame(d1, l1).transposed()
    apply(n, Matrix.Translation(h) @ R.to_4x4() @ Matrix.Translation(-h))

# The trunk keeps Marta's joint layout, but the whole upper block (chest,
# shoulders, neck, head) is lifted to the model's shoulder height. Marta's head
# sits ~5 cm higher above her shoulders than these models; fitting only the
# shoulders pulled them down and stretched the neck. The height difference is
# shared between the Hips-Spine and Spine-Spine1 spans of the torso instead.
lift_collar = ((J['LeftShoulder']['head'].z + J['RightShoulder']['head'].z) / 2 -
               (H('LeftShoulder').z + H('RightShoulder').z) / 2)
lift_arm = ((J['LeftArm']['head'].z + J['RightArm']['head'].z) / 2 -
            (H('LeftArm').z + H('RightArm').z) / 2)
# The lift can be measured at the collarbone roots or at the arm joints. Aligned
# at the collar, any difference in shoulder slope from Marta lifts the shoulders
# up around the face (seen in game on Juan Latino); aligned at the arm joints the
# neck and collar keep a natural look, so that is used here (LIFT_MIX 0).
LIFT_MIX = float(os.environ.get('LIFT_MIX', '0'))
lift = lift_arm + (lift_collar - lift_arm) * LIFT_MIX
print('LIFT collar', round(lift_collar, 4), 'arm', round(lift_arm, 4), flush=True)
move('Spine', H('Spine') + Vector((0, 0, lift / 2)))
move('Spine1', H('Spine1') + Vector((0, 0, lift / 2)))
print('UPPER_BODY_LIFT', round(lift, 4), flush=True)
for s in ('Left', 'Right'):
    move(s + 'Shoulder', J[s + 'Shoulder']['head']); turn(s + 'Shoulder', s + 'Arm', J[s + 'Arm']['head'])
    move(s + 'Arm', J[s + 'Arm']['head']); turn(s + 'Arm', s + 'ForeArm', J[s + 'ForeArm']['head'])
    move(s + 'ForeArm', J[s + 'ForeArm']['head']); turn(s + 'ForeArm', s + 'Hand', J[s + 'Hand']['head'])
    move(s + 'Hand', J[s + 'Hand']['head'])
    hn = s + 'Hand'
    align_frame(hn, H(hn + 'Middle1') - H(hn), H(hn + 'Index1') - H(hn + 'Pinky1'),
                J[hn + 'Middle1']['head'] - J[hn]['head'], J[hn + 'Index1']['head'] - J[hn + 'Pinky1']['head'])
    for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        for k in (1, 2, 3):
            n = f'{hn}{f}{k}'; tgt = J[f'{hn}{f}{k+1}']['head'] if k < 3 else J[n]['tail']
            move(n, J[n]['head']); turn(n, f'{hn}{f}{k+1}', tgt)
    move(s + 'UpLeg', J[s + 'UpLeg']['head']); turn(s + 'UpLeg', s + 'Leg', J[s + 'Leg']['head'])
    move(s + 'Leg', J[s + 'Leg']['head']); turn(s + 'Leg', s + 'Foot', J[s + 'Foot']['head'])
    move(s + 'Foot', J[s + 'Foot']['head']); turn(s + 'Foot', s + 'ToeBase', J[s + 'ToeBase']['head'])
    move(s + 'ToeBase', J[s + 'ToeBase']['head']); turn(s + 'ToeBase', s + 'ToeBase_END', J[s + 'ToeBase']['tail'])
fit_head = {b.name: b.head.copy() for b in ad.edit_bones}
for _n in ('Hips', 'Spine', 'Spine1', 'Neck', 'Head', 'LeftShoulder', 'LeftArm'): print('JOINT', _n, 'fit', [round(x, 3) for x in fit_head[_n]], 'native', [round(x, 3) for x in original[_n].translation], flush=True)
bpy.ops.object.mode_set(mode='OBJECT')

# --- Weights: source names -> Marta names ------------------------------------
RENAME = {'Spine1': 'Spine', 'Spine2': 'Spine1'}
bone_names = {b.name for b in ad.bones}
names = [g.name for g in mesh.vertex_groups]
per_vertex = []
for v in mesh.data.vertices:
    w = {}
    for g in v.groups:
        n = RENAME.get(names[g.group], names[g.group])
        if n not in bone_names: raise RuntimeError('Unmapped bone ' + n)
        w[n] = w.get(n, 0) + g.weight
    per_vertex.append(w)
V0 = np.array([tuple(v.co) for v in mesh.data.vertices])
if not mesh.vertex_groups:
    # No source weights: bone heat on the fitted skeleton (heat_weights.py).
    exec(compile(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'heat_weights.py')).read(),
                 'heat_weights.py', 'exec'))

# Fingers rebuilt from the geometry. The AI source model has five long fingers
# (plus the thumb) fused together past the knuckles; the extra one, between the
# middle and ring fingers, was weighted to Middle2 and Ring3 at once, so it would
# stay half straight when the hand grips the sword. Every finger vertex now
# follows its two nearest finger chains (index, middle, ring, little finger),
# blended by distance, and within each chain the phalanx given by its position
# along the finger, with soft blends at the joints. The extra finger therefore
# curls exactly like the average of its neighbours. Thumb and palm keep their
# source weights.
FINGERS = ('Index', 'Middle', 'Ring', 'Pinky')
JOINT_BLEND = .008
def _closest_on_chain(p, pts):
    best = None
    for k in range(len(pts) - 1):
        a, b = pts[k], pts[k + 1]; ab = b - a; L = ab.length
        t = max(0., min(1., (p - a).dot(ab) / (L * L))) if L > 1e-9 else 0.
        q = a + ab * t; d = (p - q).length
        if best is None or d < best[0]: best = (d, k, t, L)
    return best
fingers_fixed = 0
for side in ('Left', 'Right'):
    hb = side + 'Hand'
    chains = {}
    for f in FINGERS:
        pts = [J[hb + f + str(k)]['head'] for k in (1, 2, 3)] + [J[hb + f + '3']['tail']]
        chains[f] = [Vector(p) for p in pts]
    finger_bones = {hb + f + str(k) for f in FINGERS for k in (1, 2, 3)}
    for i, v in enumerate(mesh.data.vertices):
        w = per_vertex[i]
        F = sum(x for n, x in w.items() if n in finger_bones)
        if F < .05: continue
        hits = sorted(((_closest_on_chain(v.co, pts), f) for f, pts in chains.items()), key=lambda h: h[0][0])[:2]
        (d1, k1, t1, L1), f1 = hits[0]; (d2, k2, t2, L2), f2 = hits[1]
        a1, a2 = 1. / max(d1, 1e-4) ** 2, 1. / max(d2, 1e-4) ** 2
        share = {f1: a1 / (a1 + a2), f2: a2 / (a1 + a2)}
        new = {n: x for n, x in w.items() if n not in finger_bones}
        tot_rest = sum(new.values()); new = {n: x * (1 - F) / tot_rest for n, x in new.items()} if tot_rest > 0 else {}
        for (d, k, t, L), f in hits:
            # Phalanx of segment k (0..2), blended over JOINT_BLEND across each joint.
            s = k + t; seg = {}
            for j in range(3):
                lo = j - JOINT_BLEND / max(L, 1e-4); hi = j + 1 + JOINT_BLEND / max(L, 1e-4)
                seg[j] = max(0., min(1., min(s - lo, hi - s) / (2 * JOINT_BLEND / max(L, 1e-4)) + .5)) if j < 2 else max(0., min(1., (s - lo) / (2 * JOINT_BLEND / max(L, 1e-4))))
            st = sum(seg.values()) or 1.
            for j, x in seg.items():
                if x > 0: new[hb + f + str(j + 1)] = new.get(hb + f + str(j + 1), 0) + F * share[f] * x / st
        tot = sum(new.values()); per_vertex[i] = {n: x / tot for n, x in new.items() if x / tot > 1e-4}
        fingers_fixed += 1
print('FINGERS_REBUILT', fingers_fixed, flush=True)

# Waist matched to Felipe II's (the most natural one in game): the lower spine
# takes over from 3 cm above the hip joint (55% under the chest) and the belt band
# below the stiff chest is wide, so the waist bends smoothly over
# Hips -> Spine -> Spine1 instead of creasing under the bodice.
def _sm(x): x = min(1., max(0., x)); return x * x * (3 - 2 * x)
hip_z = (J['LeftUpLeg']['head'].z + J['RightUpLeg']['head'].z) / 2
# The skirt. Below the waist the dress is a shell of its own around the legs
# (the mesh only joins them at the hips), so it can move on its own:
# - it is found geometrically: cutting the mesh lower and lower until the legs
#   come apart from the skirt, the largest piece is the skirt; between that cut
#   and the hip joint, everything farther than 11 cm from both thighs is skirt
#   too (the legs keep their own weights);
# - its weights depend only on position, so the blue overskirt and the red
#   underskirt, which lie close together, always move together and never cross;
# - it hangs from the pelvis at the waist and follows the thighs more and more
#   towards the knees (front more than back), split left/right by angle, so it swings
#   with the legs in lunges without being glued to them.
import collections
_nb = collections.defaultdict(list)
for e in mesh.data.edges:
    a, b = e.vertices; _nb[a].append(b); _nb[b].append(a)
_co = [v.co.copy() for v in mesh.data.vertices]
def _components(zc):
    seen = set(); comps = []
    for s in range(len(_co)):
        if s in seen or _co[s].z >= zc: continue
        st = [s]; seen.add(s); c = []
        while st:
            i = st.pop(); c.append(i)
            for j in _nb[i]:
                if j not in seen and _co[j].z < zc: seen.add(j); st.append(j)
        comps.append(c)
    return sorted(comps, key=len, reverse=True)
cut = hip_z
while cut > .3:
    comps = _components(cut)
    if len(comps) >= 3 and len(comps[1]) > 300 and len(comps[2]) > 300: break
    cut -= .01
def _dist_seg(p, a, b):
    ab = b - a; t = max(0., min(1., (p - a).dot(ab) / ab.length_squared)); return (p - (a + ab * t)).length
_thighs = [(J[s + 'UpLeg']['head'], J[s + 'Leg']['head']) for s in ('Left', 'Right')]
SKIRT = set(comps[0])
for i, p in enumerate(_co):
    if cut <= p.z < hip_z and min(_dist_seg(p, a, b) for a, b in _thighs) > .11 * SCALE:
        SKIRT.add(i)
hem_z = min(_co[i].z for i in SKIRT)
# Only the direction around the body and the height decide the weights (never
# the distance from the legs: the overskirt and the underskirt lie at
# different distances and would then come apart). Left/right is split by the
# angle around the body; the front follows the legs more than the back.
# Above the knees the skirt follows the thighs a little; below them it
# follows the shins: in a lunge or a raised knee the shin stays nearly
# vertical, so the hem moves forward with the knee but keeps hanging down,
# instead of swinging up like a stiff cone around the hip.
SKIRT_FRONT, SKIRT_BACK = .85, .75
SKIRT_THIGH = .6                                      # share of it on the thighs above the knees
_cx = (J['LeftUpLeg']['head'].x + J['RightUpLeg']['head'].x) / 2
_cy = (J['LeftUpLeg']['head'].y + J['RightUpLeg']['head'].y) / 2
knee_z = (J['LeftLeg']['head'].z + J['RightLeg']['head'].z) / 2
for i in SKIRT:
    p = _co[i]
    dx, dy = p.x - _cx, p.y - _cy; r = math.hypot(dx, dy) or 1e-6
    front = _sm((-dy / r + .3) / 1.0)                   # 1 = front of the skirt
    # These bone weights are only the base movement: the cloth simulation in
    # game (Unity Cloth with capsules around thighs and shins) lets the fabric
    # move away from the legs. Left/right is split by the angle around the body,
    # with a wide blend over the front and back. Measured against 2,096 real poses
    # of Marta's animations, this symmetric split leaves the fewest big
    # penetrations for the cloth to fix (Marta steps both ways and kicks high).
    _bw = .75
    side = _sm((dx / r + _bw) / (2 * _bw))                # 1 = left leg
    # From just below the waist seam (which keeps the bodice's pelvis weights so it
    # never opens) the skirt already goes partly with the thighs, so a knee raised
    # high pushes the upper skirt forward instead of coming through it.
    _d = _sm((hip_z - p.z) / max(1e-6, hip_z - knee_z))
    share = (SKIRT_BACK + (SKIRT_FRONT - SKIRT_BACK) * front) * max(_d, .4 * _sm((hip_z - .005 - p.z) / .15))
    _st = float(os.environ.get('SHIN_TOP', '.6'))
    shin = _sm((knee_z + _st - p.z) / _st) * _d         # from high on the thigh down: the knee carries it
    up, low = share * (SKIRT_THIGH * (1 - shin)), share * shin
    w = {'Hips': 1 - up - low}
    for s, k in (('Left', side), ('Right', 1 - side)):
        if up * k > 1e-4: w[s + 'UpLeg'] = up * k
        if low * k > 1e-4: w[s + 'Leg'] = low * k
    per_vertex[i] = w
print('SKIRT', len(SKIRT), 'cut', round(cut, 3), 'hem', round(hem_z, 3), 'legs', [len(c) for c in comps[1:3]], flush=True)

BELT_Z, BELT_BAND = 1.20, .07  # Sebastiana's bodice: stiff above the waist (~1.17 m)
WAIST_LO, WAIST_HI, WAIST_SPINE = hip_z + .03, BELT_Z - BELT_BAND, .55
waist_fixed = 0
for i, v in enumerate(mesh.data.vertices):
    z = v.co.z
    if z <= WAIST_LO or z >= BELT_Z + BELT_BAND: continue
    w = per_vertex[i]
    hs = w.get('Hips', 0) + w.get('Spine', 0)
    if hs < .5: continue
    s = WAIST_SPINE * _sm((z - WAIST_LO) / max(1e-6, WAIST_HI - WAIST_LO))
    if w.get('Spine', 0) >= s * hs: continue
    w['Spine'] = s * hs; w['Hips'] = hs - w['Spine']
    waist_fixed += 1
print('WAIST_SPINE', waist_fixed, 'hip_z', round(hip_z, 3), 'shoulder_z', round(J['LeftArm']['head'].z, 3),
      'neck_z', round(J['Neck']['head'].z, 3), 'knee_z', round(J['LeftLeg']['head'].z, 3), flush=True)
# Arms rebuilt along Marta's bones. The source rig gives the top of the upper
# arm (pauldron, upper cannon) to the clavicle and chest, so with the arms down
# those parts would stay in T-pose and stretch into flaps. Inside the
# arm tube everything past the shoulder joint now belongs to the arm: a short
# blend at the shoulder, the upper arm on Arm, a clean Arm->ForeArm blend at
# the elbow and the forearm on ForeArm. The wrist and hand keep their own
# (correct) source weights.
ARM_TUBE_R, ARM_TUBE_WIDE = .13, .22
TAB_HOLD = float(os.environ.get('TAB_HOLD', '.2'))  # share of the shoulder top kept on the collarbone
SHOULDER_IN, SHOULDER_OUT, ELBOW_HALF, WRIST_IN = .07, .0, .04, .03  # cloth shoulders
def smooth01(x): x = min(1., max(0., x)); return x * x * (3 - 2 * x)
arm_fixed = 0
for side, sg in (('Left', 1), ('Right', -1)):
    js, je, jw = J[side + 'Arm']['head'], J[side + 'ForeArm']['head'], J[side + 'Hand']['head']
    xs, xe, xw = sg * js.x, sg * je.x, sg * jw.x
    for i, v in enumerate(mesh.data.vertices):
        u = sg * v.co.x
        if u < xs - SHOULDER_IN or u > xw - WRIST_IN: continue
        a, b = (js, je) if u < xe else (je, jw)
        f = min(1., max(0., (u - sg * a.x) / max(1e-6, sg * (b.x - a.x))))
        axis = a.lerp(b, f)
        # Near the shoulder the tube stays narrow (the bodice side is right below);
        # past the joint there is no torso, and the puffed sleeves are wide.
        tube = ARM_TUBE_R if u < xs + .02 else ARM_TUBE_WIDE
        if math.hypot(v.co.y - axis.y, v.co.z - axis.z) > tube: continue
        # At the shoulder only the sleeve cap on top of the joint follows the arm; the
        # doublet sides below it stay on the chest (no armpit dent).
        # Cloth: the sleeve root under the joint goes half with the arm (the armour
        # mods keep it on the chest), so a forward arm does not fold over it.
        under = u < xs + .02 and v.co.z < axis.z - .02
        if u < xe:
            t_arm = smooth01((u - (xs - SHOULDER_IN)) / (SHOULDER_IN + SHOULDER_OUT))
            t_fore = smooth01((u - (xe - ELBOW_HALF)) / (2 * ELBOW_HALF))
        else:
            t_arm, t_fore = 1., smooth01((u - (xe - ELBOW_HALF)) / (2 * ELBOW_HALF))
        # Shoulder tabs on top of the joint: above the pivot they swing outward
        # when the arm drops and stuck out as a ledge. Up to 60% of them stays on
        # the collarbone, fading out 10 cm down the arm.
        if u < xs + .10:
            top = smooth01((v.co.z - axis.z - .02) / .04) * (1 - smooth01((u - (xs + .04)) / .06))
            t_arm *= 1 - TAB_HOLD * top
        if under: t_arm *= .5
        rest = {n: x for n, x in per_vertex[i].items() if not n.startswith(side + 'Arm') and not n.startswith(side + 'ForeArm')}
        tot = sum(rest.values())
        rest = {n: x / tot for n, x in rest.items()} if tot > 1e-6 else {side + 'Shoulder': 1.}
        w = {n: x * (1 - t_arm) for n, x in rest.items()}
        w[side + 'Arm'] = t_arm * (1 - t_fore); w[side + 'ForeArm'] = t_arm * t_fore
        per_vertex[i] = {n: x for n, x in w.items() if x > 1e-4}; arm_fixed += 1
print('ARMS_REBUILT', arm_fixed, flush=True)

# Armpits (as on Ana Maria de Soto): the bodice sides under the armpits belong
# to the torso. The arm weight the source rig spilled onto them is handed to the
# chest, fading in over 6 cm below the arm axis, so the arm hangs close to the
# body without a gap. Only the torso side of the shoulder joint is touched; the
# puffed sleeve past the joint keeps following the arm.
# At most half of it: all of it suits arms hanging down, but a forward arm then
# folded over the armpit and stretched the cloth there.
ARMPIT_MAX = .5
armpit_fixed = 0
for side, sg in (('Left', 1), ('Right', -1)):
    js = J[side + 'Arm']['head']; xs = sg * js.x
    for i, v in enumerate(mesh.data.vertices):
        u = sg * v.co.x
        if u < xs - .12 or u > xs: continue
        t = ARMPIT_MAX * smooth01((js.z - .02 - v.co.z) / .06)
        if t <= 0: continue
        w = per_vertex[i]; arm_w = sum(x for n, x in w.items() if n.startswith((side + 'Arm', side + 'ForeArm')))
        if arm_w <= 0: continue
        w = {n: x for n, x in w.items() if not n.startswith((side + 'Arm', side + 'ForeArm'))}
        w['Spine1'] = w.get('Spine1', 0) + arm_w * t
        if arm_w * (1 - t) > 1e-4: w[side + 'Arm'] = arm_w * (1 - t)
        per_vertex[i] = w; armpit_fixed += 1
print('ARMPITS_TO_TORSO', armpit_fixed, flush=True)

# Stiff chest: the bodice above the belt is stiff, so it moves as one piece
# on the chest (Spine1) and only bends at the belt (a wide band, so the coat
# folds instead of tearing). Below the armpits the clavicle and upper-arm
# weights on the front and back of the chest are handed to the chest, fading
# out towards the sleeves; the cloth shoulder caps above keep following the arm.
CORE_X, SIDE_X = .12, .17
ARMPIT_Z = J['LeftArm']['head'].z - .12
neck_z = J['Neck']['head'].z
for i, v in enumerate(mesh.data.vertices):
    co = v.co
    if co.z < BELT_Z - BELT_BAND or co.z > neck_z: continue
    w = per_vertex[i]
    t = min(1., (co.z - (BELT_Z - BELT_BAND)) / (2 * BELT_BAND))
    # Hips and Spine keep their own proportions; only the share t moves to the chest,
    # so the weights stay continuous with the skirt and hips below the band.
    lower = w.get('Hips', 0) + w.get('Spine', 0)
    for n in ('Hips', 'Spine'):
        if n in w: w[n] *= (1 - t)
    w['Spine1'] = w.get('Spine1', 0) + lower * t
    if t >= 1 and co.z < ARMPIT_Z:
        f = min(1., max(0., (SIDE_X - abs(co.x)) / (SIDE_X - CORE_X)))
        if f > 0:
            for n in [n for n in w if n.endswith(('Shoulder', 'Arm')) and not n.endswith('ForeArm')]:
                x = w[n] * f; w[n] -= x; w['Spine1'] += x
    tot = sum(w.values())
    if tot > 0: per_vertex[i] = {n: x / tot for n, x in w.items() if x / tot > 1e-4}
print('STIFF_CHEST belt_z', BELT_Z, flush=True)

# Rigid head: faces fully owned by the head (face, hair, hat).
head_faces = set()
for p in mesh.data.polygons:
    # Long hair: a looser threshold keeps more of the locks in the rigid head.
    if p.center.z > 1.42 and all(per_vertex[i].get('Head', 0) >= .35 for i in p.vertices):
        head_faces.add(p.index)
head_verts = {i for f in head_faces for i in mesh.data.polygons[f].vertices}
body_verts = {i for p in mesh.data.polygons if p.index not in head_faces for i in p.vertices}
seam = head_verts & body_verts
for i in head_verts: per_vertex[i] = {'Head': 1.}

# Hanging hair below the rigid head: diffuse the weights from the head seam
# over ~12 cm of the locks, so a head turn is shared along the hair instead
# of folding it at the seam line.
import heapq
nbr = [[] for _ in mesh.data.vertices]
for e in mesh.data.edges:
    a, b = e.vertices; d = (mesh.data.vertices[a].co - mesh.data.vertices[b].co).length
    nbr[a].append((b, d)); nbr[b].append((a, d))
dist = {i: 0. for i in seam}; heap = [(0., i) for i in seam]
while heap:
    d, i = heapq.heappop(heap)
    if d > dist.get(i, 1e9) or d > .12: continue
    for j, dd in nbr[i]:
        if j in head_verts: continue
        nd = d + dd
        if nd < dist.get(j, 1e9) and nd <= .12:
            dist[j] = nd; heapq.heappush(heap, (nd, j))
band = [i for i in dist if i not in head_verts]
for _ in range(12):
    new = {}
    for i in band:
        acc = {n: x * .4 for n, x in per_vertex[i].items()}; share = .6 / max(1, len(nbr[i]))
        for j, _ in nbr[i]:
            for n, x in per_vertex[j].items(): acc[n] = acc.get(n, 0.) + x * share
        tot = sum(acc.values()); new[i] = {n: x / tot for n, x in acc.items() if x / tot > 1e-4}
    for i, w in new.items(): per_vertex[i] = w
print('HAIR_TRANSITION head_faces', len(head_faces), 'band_vertices', len(band), flush=True)

while mesh.vertex_groups: mesh.vertex_groups.remove(mesh.vertex_groups[0])
groups = {}
for i, w in enumerate(per_vertex):
    top = sorted(((n, x) for n, x in w.items() if x > 1e-4), key=lambda t: -t[1])[:4]
    tot = sum(x for _, x in top)
    if tot <= 0: top, tot = [('Hips', 1.)], 1.
    for n, x in top:
        g = groups.get(n) or mesh.vertex_groups.new(name=n); groups[n] = g
        g.add([i], x / tot, 'REPLACE')

# --- Carry the mesh into Marta's native bind pose ----------------------------
# Limb segments are stretched along their bones while carrying the mesh into
# the target skeleton. The source arms are much shorter than the fighter's bones
# (upper arm ~0.19 vs 0.27 m, forearm ~0.19 vs 0.30 m) and the legs differ too.
# Moving each bone to its target joint without stretching left the whole length
# difference in the blend zones (elbow, wrist, shoulder), which pinched and
# twisted the shoulders and arms in game. Each clavicle, upper arm, forearm, thigh and shin is
# scaled along its own axis from its joint, so every joint lands on the target
# skeleton and the segment between keeps its shape. Linear blend done by hand:
# a stretch along an arbitrary axis is not representable as a pose bone matrix.
mesh.parent = arm
SEGMENTS = [(s + a, s + b) for s in ('Left', 'Right') for a, b in
            (('Shoulder', 'Arm'), ('Arm', 'ForeArm'), ('ForeArm', 'Hand'), ('UpLeg', 'Leg'), ('Leg', 'Foot'))]
stretch = {}
for a, c in SEGMENTS:
    nh = original[a].translation; d = original[c].translation - nh
    r = d.length / max(1e-6, (fit_head[c] - fit_head[a]).length); dn = d.normalized()
    Sm = Matrix.Identity(3) + (r - 1) * Matrix(((dn.x * dn.x, dn.x * dn.y, dn.x * dn.z), (dn.y * dn.x, dn.y * dn.y, dn.y * dn.z), (dn.z * dn.x, dn.z * dn.y, dn.z * dn.z)))
    stretch[a] = Matrix.Translation(nh) @ Sm.to_4x4() @ Matrix.Translation(-nh)
    print('SEGMENT_STRETCH', a, round(r, 3), flush=True)
# The game snaps every skin bone onto the fighter's bone (SetParent with local
# position and rotation reset), so the fighter's joint positions rule. When the
# model's hips sit higher or lower than the fighter's, the hip area had to
# stretch or squash between pelvis and thighs and the arms lost proportion. The lower trunk (Hips and Spine weights) is
# therefore stretched vertically below the chest joint (Spine1), so the mesh hip
# joint lands on the fighter's; the thighs then start right there.
z0 = original['Spine1'].translation.z
mesh_hip = (fit_head['LeftUpLeg'].z + fit_head['RightUpLeg'].z) / 2
native_hip = (original['LeftUpLeg'].translation.z + original['RightUpLeg'].translation.z) / 2
r_trunk = (z0 - native_hip) / max(1e-6, z0 - mesh_hip)
St = Matrix.Translation((0, 0, z0)) @ Matrix.Diagonal((1., 1., r_trunk, 1.)) @ Matrix.Translation((0, 0, -z0))
for n in ('Hips', 'Spine'): stretch[n] = St
print('TRUNK_STRETCH', round(r_trunk, 3), 'mesh_hip', round(mesh_hip, 3), 'native_hip', round(native_hip, 3), flush=True)
Mb = {}
for b in ad.bones:
    M = original[b.name] @ b.matrix_local.inverted()
    Mb[b.name] = stretch[b.name] @ M if b.name in stretch else M
gname = {g.index: g.name for g in mesh.vertex_groups}
coords = []
# The skirt is carried as one piece: scaled vertically about the floor so its
# top meets the fitted waist (the trunk stretch maps the hip joint exactly
# there) and its hem stays at the floor. Carried through its blend of pelvis
# and thigh transforms, the layered skirt would shear apart.
k_skirt = native_hip / mesh_hip
print('SKIRT_CARRY_SCALE', round(k_skirt, 3), flush=True)
for vi, v in enumerate(mesh.data.vertices):
    if vi in SKIRT:
        coords.append(Vector((v.co.x, v.co.y, v.co.z * k_skirt))); continue
    acc = Vector((0., 0., 0.)); tw = 0.
    for g in v.groups:
        acc += g.weight * (Mb[gname[g.group]] @ v.co); tw += g.weight
    coords.append(acc / tw if tw > 0 else v.co.copy())
for v, c in zip(mesh.data.vertices, coords): v.co = c
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
for b in ad.edit_bones: b.matrix = original[b.name]; b.length = origlen[b.name]
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
mod = mesh.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

# --- Materials, split body/head ----------------------------------------------
img = bpy.data.images.load(os.path.join(BUILD, 'Sebastiana_BaseColor.png'))
def material(name):
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    tx = mt.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    bs = mt.node_tree.nodes['Principled BSDF']; bs.inputs['Roughness'].default_value = .85
    mt.node_tree.links.new(tx.outputs['Color'], bs.inputs['Base Color']); return mt
mesh.data.materials.clear()
mesh.data.materials.append(material('SebastianaMaterial')); mesh.data.materials.append(material('HeadMaterial')); mesh.data.materials.append(material('SkirtMaterial'))
# The skirt is its own part: in game it is simulated as cloth (Unity Cloth).
for p in mesh.data.polygons:
    p.material_index = 1 if p.index in head_faces else (2 if all(v in SKIRT for v in p.vertices) else 0)
bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='MATERIAL'); bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.data.objects if o.type == 'MESH']
for o in parts:
    used = {o.data.materials[p.material_index].name for p in o.data.polygons}
    o.name = 'SebastianaHead' if any(n.startswith('HeadMaterial') for n in used) else ('SebastianaSkirt' if any(n.startswith('SkirtMaterial') for n in used) else 'SebastianaBody')
    o.data.name = o.name
    # Separating by material can leave stray vertices without faces in a part.
    import bmesh
    bm = bmesh.new(); bm.from_mesh(o.data)
    stray = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=stray, context='VERTS'); bm.to_mesh(o.data); bm.free()
    print('STRAY_VERTICES_REMOVED', o.name, len(stray), flush=True)
# The cloth solver works on every skirt vertex, so the skirt is lightened to
# about 5,000 vertices (two fighters may wear it at once). Its open edges (the
# waist seam with the bodice and the hems) are protected so the seam stays
# closed; textures and normal map keep the folds' detail.
SKIRT_CLOTH_VERTS = 5000
sk = next(o for o in parts if o.name == 'SebastianaSkirt')
bm = bmesh.new(); bm.from_mesh(sk.data)
edge_verts = {v.index for e in bm.edges if e.is_boundary for v in e.verts}; bm.free()
vg = sk.vertex_groups.new(name='_decimate'); vg.add([v.index for v in sk.data.vertices if v.index not in edge_verts], 1., 'REPLACE')
before = len(sk.data.vertices)
bpy.ops.object.select_all(action='DESELECT'); sk.select_set(True); bpy.context.view_layer.objects.active = sk
d = sk.modifiers.new('ClothBudget', 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = min(1., SKIRT_CLOTH_VERTS / before)
d.vertex_group = '_decimate'; d.vertex_group_factor = 1.
bpy.ops.object.modifier_apply(modifier='ClothBudget')
sk.vertex_groups.remove(sk.vertex_groups['_decimate'])
print('SKIRT_CLOTH_MESH', before, '->', len(sk.data.vertices), 'protected edge verts', len(edge_verts), flush=True)
# --- QA renders ---------------------------------------------------------------
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 1000; sc.render.resolution_y = 1200
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3
def render(n, pos, tgt=(0, 0, 1)):
    cam.location = pos; cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, n + '.png'); bpy.ops.render.render(write_still=True)
render('rest_front', (0, -4, 1)); render('rest_back', (0, 4, 1)); render('rest_side', (4, 0, 1))
def point(n, child, d):
    bpy.context.view_layer.update(); pb = arm.pose.bones[n]; m = pb.matrix; h = m.translation
    v = arm.pose.bones[child].matrix.translation - h
    r = v.normalized().rotation_difference(Vector(d).normalized()).to_matrix().to_4x4()
    pb.matrix = Matrix.Translation(h) @ r @ Matrix.Translation(-h) @ m; bpy.context.view_layer.update()
for s, sg in (('Left', 1), ('Right', -1)):
    point(s + 'Arm', s + 'ForeArm', (sg * .7, 0, .7)); point(s + 'ForeArm', s + 'Hand', (sg * .5, -.3, .7))
render('test_arms_up', (0, -4, 1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
point('RightArm', 'RightForeArm', (-.25, -.7, -.25)); point('RightForeArm', 'RightHand', (.15, -.8, .15))
point('LeftArm', 'LeftForeArm', (.4, .2, -.4))
render('test_guard', (2, -4, 1.1))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
# Fighting twist: spine bent and turned, as in Marta's attacks; checks the back.
for n, e in (('Spine', (12, 18, 6)), ('Spine1', (10, 24, 8))):
    pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = [math.radians(a) for a in e]
point('RightArm', 'RightForeArm', (-.25, -.7, -.25)); point('RightForeArm', 'RightHand', (.15, -.8, .15))
render('test_twist_back', (-1.5, 4, 1.2)); render('test_twist_side', (4, .8, 1.2))
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
# Head turn: checks that the long hair follows smoothly without folding.
for n, e in (('Neck', (8, 20, 4)), ('Head', (12, 30, 8))):
    pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = [math.radians(a) for a in e]
cam.data.ortho_scale = .8
render('test_head_turn_back', (1.2, 3.5, 1.5), (0, 0, 1.45)); render('test_head_turn_side', (3.6, -.6, 1.5), (0, 0, 1.45))
cam.data.ortho_scale = 2.3
for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()
cam.data.ortho_scale = .55; render('head_closeup', (0, -4, 1.62), (0, 0, 1.62)); render('head_side', (4, 0, 1.62), (0, 0, 1.62))

# --- Save and export ------------------------------------------------------------
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'Sebastiana_Marta.blend'))
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
for o in parts: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Skin.fbx'), use_selection=True, object_types={'ARMATURE', 'MESH'},
                         add_leaf_bones=False, bake_anim=False, path_mode='COPY', embed_textures=False,
                         use_mesh_modifiers=False, apply_scale_options='FBX_SCALE_NONE')
report = {'parts': {o.name: {'verts': len(o.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in o.data.polygons)} for o in parts},
          'seam_vertices': len(seam), 'bones': len(ad.bones)}
json.dump(report, open(os.path.join(OUT, 'rig_report.json'), 'w'), indent=1)
print('MARTA_RIG_OK', report, flush=True)
