# Sebastiana Inés Josefa de San Agustín: exclusive custom skin for Marta (Hellish Quart)

A fan-made skin that works only for Marta. It runs on Marta's native 68-joint skeleton (Mafra5/Marfa), with her original moves and rapier. Sebastiana Inés Josefa de San Agustín, an Indigenous noblewoman of 18th-century New Spain, wears a blue brocade gown with a lace-trimmed bodice, lace sleeve ruffles, a blue overskirt draped over a red floral underskirt, a pearl necklace with a cross, and a braided diadem with red flowers.

- **A skirt simulated as real cloth.** Below the waist the dress is a separate shell around the legs. It is its own part with Unity's Cloth component, set up with the damping, gravity, friction and solver rate of Marta's own dress (`ClothDress`):
  - it is found geometrically (cutting the mesh lower and lower until the legs come apart from it) and lightened to about 5,000 vertices for the simulation, with the waist seam and hems protected;
  - its bone weights give the base movement (a wide left/right split, from just below the waist going more and more with the thighs and then the shins); the cloth may leave that base by up to 35 cm, already 12 cm below the waist seam, which never moves;
  - capsules around both thighs and shins push the fabric away, so the legs stay inside it. They are triggers on the Ignore Raycast layer: Unity Cloth still collides with them (tested), and they take no part in the fight's physics;
  - while binding it is carried as one piece, scaled from the waist to the floor, so the hips can be fitted to Marta's without shearing the layered skirt.
- **Soft waist, stiff bodice.** The bodice above the waist moves as one piece (Spine1); the waist blends Hips → Spine → Spine1 as on the Felipe II skin.
- **Relaxed shoulders and clean armpits.** The upper body is aligned at the arm joints, so the shoulders stay low and the neck shows. Under the armpit the cloth is shared half and half between arm and torso: the arms hang close to the body without the sleeve folding over the armpit when the sword arm goes forward.
- **Limbs and hips fitted to Marta's skeleton.** The game snaps every skin bone onto Marta's bone, so her joint positions rule. The model is scaled to Marta's shoulder height (x0.952); each collarbone, upper arm and forearm (x1.52), thigh (x0.91) and shin (x0.92) is stretched evenly along its own bone while binding, the elbow is placed at Marta's own upper-arm/forearm split, and the lower trunk is fitted so the hip joint lands on Marta's.
- **Rigid head and hair.** Face, braids, diadem and flowers form one rigid part on the head bone.
- **No ghost body when hit.** Marta's 17 wound overlay meshes (`DecalBloody`, `DecalSpine1`, ...) are shaped like her own body. The visibility controller keeps them hidden under the skin, together with her stock face.
- **Sharp textures within the game budget.** The 1M-triangle source is reduced to 80k triangles after welding its UV seams; each part stays under the 65k vertices the game's wound decal builder supports.
- **Fingers weighted from the geometry.** Every finger vertex follows its two nearest finger chains, blended by distance, so the hand closes cleanly on the grip.

## Known issue: extreme leg poses

Marta's animations were made for her knee-length dress. The floor-length skirt is simulated as cloth and pushed by the legs, so in normal stances, footwork, lunges and dodges the legs stay inside it. When a knee rises almost to waist height, the thigh can still show above the skirt for a moment, and where the overskirt and underskirt cross, small gaps can appear between the two layers.
## Release

The zip contains only the four bundles (`skin_marta_sebastiana`, `pic_marta_sebastiana` and their `.manifest` files) and `README.txt`. There are no scripts. Install by copying the four files into `Hellish Quart_Data/StreamingAssets/`. `README.txt` also documents the optional manual first-person (FPP) adjustment for Marta's skin loader (4 bytes of `resources.assets`, game version of November 2026).

## Layout

- `model/Sebastiana_Marta.blend`: the fitted result on Marta's skeleton, editable in Blender 5.3.
- `model/references/`: the four reference views.
- `model/selector_portrait.png`: the selector picture (the supplied period portrait, with the magazine caption removed and upscaled 3x).
- `model/Sebastiana_source.glb` is not in the repository because of its size (96 MB). Place it there to rebuild from scratch.
- `blender_work/`:
  - `step1_prepare.py` welds, decimates and cleans the source, transfers its rig weights and exports the textures;
  - `step3_rig_marta.py` places the elbow, fits Marta's limbs and hands, finds and weights the skirt, rebuilds the waist, arm, shoulder and armpit weights, stretches the limb segments and fits the hips while carrying the mesh into Marta's bind pose, and splits off the rigid head, with QA renders;
  - `verify_skeleton.py` checks the 68 bones and the weights.
- `unity_project/`: Unity 2019.4.0f1 project (menu **Sebastiana → Construir mod**).
- `release/README.txt`: the English text shipped in the zip.

## Rebuild

Copy `Hellish Quart_Data/Managed/PlayMaker.dll` from your own installation to `unity_project/Assets/Plugins/`, then run from the repository folder (absolute paths, so Blender writes into this folder):

```powershell
$blender="C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
$root=(Get-Location).Path
$skel="$root\unity_project\Assets\SebastianaMod\Editor\MartaSkeleton.json"
& $blender -b --factory-startup -P blender_work\step1_prepare.py -- "$root\model\Sebastiana_source.glb" "$root\model\Sebastiana_source.glb" "$root\build"
& $blender -b --factory-startup -P blender_work\step3_rig_marta.py -- "$root\build" $skel
& $blender -b --factory-startup -P blender_work\verify_skeleton.py -- "$root\build\marta\Skin.fbx" $skel
.\build.ps1
```

`build.ps1` is a developer build script and is never part of the release. It runs the Unity batch build, copies the four bundles into `release/` and creates `Sebastiana_Marta.zip`.
