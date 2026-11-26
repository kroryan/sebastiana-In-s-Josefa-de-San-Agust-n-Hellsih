using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;

public static class SebastianaFinalBuild {
 [Serializable] class NativeBone { public string name; public string parent; public Vector3 position; public Quaternion rotation; public Vector3 scale; }
 [Serializable] class NativeSkeleton { public string character; public NativeBone[] bones; }
 [Serializable] class PreviewMesh { public Vector3[] vertices; public int[] triangles; }
 static GameObject MakeMartaSkeleton() {
  var data=JsonUtility.FromJson<NativeSkeleton>(File.ReadAllText(D+"Editor/MartaSkeleton.json"));
  var go=new GameObject("Skin");var map=new Dictionary<string,Transform>();
  foreach(var b in data.bones) {
   var t=new GameObject(b.name).transform;t.SetParent(string.IsNullOrEmpty(b.parent)?go.transform:map[b.parent],false);
   t.localPosition=b.position;t.localRotation=b.rotation;t.localScale=b.scale;map[b.name]=t;
  }
  if(map.Count!=68)throw new Exception("Expected Marta's 68 joints");return go;
 }
 const string D="Assets/SebastianaMod/";
 static string Root {get{return Path.GetFullPath(Path.Combine(Application.dataPath,"../.."));}}
 static void Texture(string name,bool normal=false) {
  var t=(TextureImporter)AssetImporter.GetAtPath(D+name);
  var textureType=normal?TextureImporterType.NormalMap:TextureImporterType.Default;
  bool srgb=name.Contains("BaseColor");
  if(t.maxTextureSize==4096&&t.textureType==textureType&&t.sRGBTexture==srgb&&
     t.alphaSource==TextureImporterAlphaSource.None&&t.textureCompression==TextureImporterCompression.CompressedHQ&&
     t.compressionQuality==100&&t.anisoLevel==8)return;
  t.maxTextureSize=4096;t.textureType=textureType;
  t.sRGBTexture=srgb;t.alphaSource=TextureImporterAlphaSource.None;
  t.textureCompression=TextureImporterCompression.CompressedHQ;t.compressionQuality=100;t.anisoLevel=8;t.SaveAndReimport();
 }
 static bool IsFppArmBone(string name) {
  return (name.StartsWith("Left")||name.StartsWith("Right")) &&
   (name.Contains("Arm")||name.Contains("Hand"));
 }
 static float FppArmWeight(BoneWeight w,Transform[] bones) {
  float total=0;
  if(w.weight0>0&&IsFppArmBone(bones[w.boneIndex0].name))total+=w.weight0;
  if(w.weight1>0&&IsFppArmBone(bones[w.boneIndex1].name))total+=w.weight1;
  if(w.weight2>0&&IsFppArmBone(bones[w.boneIndex2].name))total+=w.weight2;
  if(w.weight3>0&&IsFppArmBone(bones[w.boneIndex3].name))total+=w.weight3;
  return total;
 }
 static void SetCameraClearanceMask(Mesh mesh,Transform[] bones) {
  // Red selects the jacket region. Alpha protects the animated sleeves,
  // hands and fingers from the larger clearance used around the torso.
  var vertices=mesh.vertices;
  var segmentStarts=new[]{bones.First(b=>b.name=="LeftArm").position,bones.First(b=>b.name=="RightArm").position};
  var segmentEnds=new[]{bones.First(b=>b.name=="LeftForeArm").position,bones.First(b=>b.name=="RightForeArm").position};
  mesh.colors32=mesh.boneWeights.Select((w,i)=>{
   float limbWeight=FppArmWeight(w,bones);
   float arm=Mathf.SmoothStep(0,1,Mathf.InverseLerp(.12f,.65f,limbWeight));
   for(int side=0;side<2;side++) {
    var delta=segmentEnds[side]-segmentStarts[side];
    var toVertex=vertices[i]-segmentStarts[side];
    float along=Vector3.Dot(toVertex,delta)/delta.sqrMagnitude;
    float distance=(toVertex-delta*Mathf.Clamp01(along)).magnitude;
    float sleeve=Mathf.SmoothStep(0,1,Mathf.InverseLerp(.03f,.22f,along))*
                 (1-Mathf.SmoothStep(0,1,Mathf.InverseLerp(.056f,.107f,distance)));
    arm=Mathf.Max(arm,sleeve);
   }
   float jacket=Mathf.SmoothStep(0,1,Mathf.InverseLerp(.82f,1.12f,vertices[i].y));
   return new Color32((byte)Mathf.RoundToInt(jacket*255),255,255,(byte)Mathf.RoundToInt(arm*255));
  }).ToArray();
 }
 public static void Build() {
  AssetDatabase.Refresh();Texture("Sebastiana_BaseColor.png");Texture("Sebastiana_Normal.png",true);Texture("Sebastiana_ORM.png");
  var importer=(ModelImporter)AssetImporter.GetAtPath(D+"Skin.fbx");
  if(!importer.isReadable||importer.importAnimation||importer.animationType!=ModelImporterAnimationType.Generic||
     importer.optimizeGameObjects||importer.meshCompression!=ModelImporterMeshCompression.Off||
     importer.indexFormat!=ModelImporterIndexFormat.UInt32||importer.materialImportMode!=ModelImporterMaterialImportMode.None) {
   importer.isReadable=true;importer.importAnimation=false;importer.animationType=ModelImporterAnimationType.Generic;
   importer.optimizeGameObjects=false;importer.meshCompression=ModelImporterMeshCompression.Off;
   importer.indexFormat=ModelImporterIndexFormat.UInt32;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.SaveAndReimport();
  }
  var shader=Shader.Find("Sebastiana/DetailedTwoSided");if(shader==null)throw new Exception("Detailed shader missing");
  var mat=AssetDatabase.LoadAssetAtPath<Material>(D+"SebastianaDetailed.mat");
  if(mat==null){mat=new Material(shader);AssetDatabase.CreateAsset(mat,D+"SebastianaDetailed.mat");}mat.shader=shader;
  mat.SetTexture("_MainTex",AssetDatabase.LoadAssetAtPath<Texture2D>(D+"Sebastiana_BaseColor.png"));
  mat.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(D+"Sebastiana_Normal.png"));
  mat.SetTexture("_ORM",AssetDatabase.LoadAssetAtPath<Texture2D>(D+"Sebastiana_ORM.png"));mat.SetFloat("_BumpScale",.7f);
  mat.SetFloat("_HeadCameraRadius",0);mat.SetFloat("_ColorDepth",1.3f);mat.SetFloat("_Saturation",1.15f);EditorUtility.SetDirty(mat);
  var headMat=AssetDatabase.LoadAssetAtPath<Material>(D+"SebastianaHead.mat");
  if(headMat==null){headMat=new Material(mat);AssetDatabase.CreateAsset(headMat,D+"SebastianaHead.mat");}
  headMat.shader=shader;headMat.CopyPropertiesFromMaterial(mat);
  // Full head clearance must allow for the native camera's displacement
  // in thrusts and reactions, while external shots stay outside this radius.
  headMat.SetFloat("_HeadCameraRadius",.49f);EditorUtility.SetDirty(headMat);
  var source=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(D+"Skin.fbx"));
  var skin=MakeMartaSkeleton();
  var map=skin.GetComponentsInChildren<Transform>().ToDictionary(t=>t.name,t=>t);
  var headRest=skin.transform.InverseTransformPoint(map["Head"].position);
  headMat.SetVector("_HeadRestAnchor",new Vector4(headRest.x,headRest.y,headRest.z,1));
  foreach(var a in skin.GetComponentsInChildren<Animator>())UnityEngine.Object.DestroyImmediate(a);
  foreach(var a in skin.GetComponentsInChildren<Animation>())UnityEngine.Object.DestroyImmediate(a);
  int triangles=0;float maxRotDifference=0;int rigidHeadCount=0;
  foreach(var r in source.GetComponentsInChildren<SkinnedMeshRenderer>()) {
   bool head=r.name.Contains("Head");
   var child=new GameObject(head?"SebastianaHead":"SebastianaBody");
   // The native decal system shares bind poses by bone identity. Keep
   // both renderers in one mesh space so their shared Head bind agrees.
   var parent=skin.transform;child.transform.SetParent(parent,false);
   var imported=r.sharedMesh;
   var mesh=new Mesh { name=child.name,indexFormat=IndexFormat.UInt32 };
   var matrix=parent.worldToLocalMatrix*r.transform.localToWorldMatrix;
   var normalMatrix=matrix.inverse.transpose;var v=imported.vertices;var n=imported.normals;var tang=imported.tangents;
   for(int i=0;i<v.Length;i++) {
    v[i]=matrix.MultiplyPoint3x4(v[i]);if(n.Length==v.Length)n[i]=normalMatrix.MultiplyVector(n[i]).normalized;
    if(tang.Length==v.Length){var q=matrix.MultiplyVector(new Vector3(tang[i].x,tang[i].y,tang[i].z)).normalized;tang[i]=new Vector4(q.x,q.y,q.z,tang[i].w*(matrix.determinant<0?-1:1));}
   }
   mesh.vertices=v;mesh.normals=n;mesh.tangents=tang;mesh.uv=imported.uv;
   var joinedTriangles=new List<int>();
   for(int s=0;s<imported.subMeshCount;s++)joinedTriangles.AddRange(imported.GetTriangles(s,true));
   if(matrix.determinant<0)for(int i=0;i<joinedTriangles.Count;i+=3) {
    int first=joinedTriangles[i];joinedTriangles[i]=joinedTriangles[i+1];joinedTriangles[i+1]=first;
   }
   mesh.SetTriangles(joinedTriangles,0);
   mesh.RecalculateBounds();triangles+=mesh.triangles.Length/3;
   string path=D+child.name+(head?"RigidSkin":"")+".asset";var existing=AssetDatabase.LoadAssetAtPath<Mesh>(path);
   var bones=head?new[]{map["Head"]}:r.bones.Select(b=>map[b.name]).ToArray();
   if(head) {
    // Marta's decal projector discovers SkinnedMeshRenderers. A single
    // Head influence gives it the rigid face and hat without facial skinning.
    mesh.boneWeights=Enumerable.Repeat(new BoneWeight{boneIndex0=0,weight0=1},v.Length).ToArray();
    rigidHeadCount=v.Length;
   }else {
    mesh.boneWeights=imported.boneWeights;
    SetCameraClearanceMask(mesh,bones);
    for(int i=0;i<bones.Length;i++)maxRotDifference=Mathf.Max(maxRotDifference,Quaternion.Angle(r.bones[i].rotation,bones[i].rotation));
   }
   mesh.bindposes=bones.Select(b=>b.worldToLocalMatrix*child.transform.localToWorldMatrix).ToArray();
   if(existing==null){AssetDatabase.CreateAsset(mesh,path);existing=mesh;}else{EditorUtility.CopySerialized(mesh,existing);UnityEngine.Object.DestroyImmediate(mesh);EditorUtility.SetDirty(existing);}
   var smr=child.AddComponent<SkinnedMeshRenderer>();
   smr.sharedMesh=existing;
   smr.bones=bones;
   smr.rootBone=map["Root"];
   smr.sharedMaterial=head?headMat:mat;
   smr.quality=SkinQuality.Bone4;
   smr.updateWhenOffscreen=true;
   smr.localBounds=head?existing.bounds:new Bounds(new Vector3(0,1,0),Vector3.one*5);
  }
  if(rigidHeadCount<1000)throw new Exception("Rigid head is missing");
  VerifyDecalMeshes(skin);
  SebastianaFppBuilder.Attach(skin);
  PrefabUtility.SaveAsPrefabAsset(skin,D+"Skin.prefab");UnityEngine.Object.DestroyImmediate(source);UnityEngine.Object.DestroyImmediate(skin);AssetDatabase.SaveAssets();
  MakeSelectorPortrait();AssetDatabase.ImportAsset(D+"Skin_pic.png",ImportAssetOptions.ForceUpdate);
  var pic=(TextureImporter)AssetImporter.GetAtPath(D+"Skin_pic.png");pic.textureType=TextureImporterType.Sprite;pic.spriteImportMode=SpriteImportMode.Single;pic.maxTextureSize=2048;pic.alphaSource=TextureImporterAlphaSource.FromInput;pic.alphaIsTransparency=true;pic.SaveAndReimport();
  var go=new GameObject("Skin_pic",typeof(RectTransform),typeof(UnityEngine.UI.Image));go.layer=5;go.GetComponent<UnityEngine.UI.Image>().sprite=AssetDatabase.LoadAssetAtPath<Sprite>(D+"Skin_pic.png");go.GetComponent<UnityEngine.UI.Image>().preserveAspect=true;
  go.GetComponent<UnityEngine.UI.Image>().raycastTarget=false;go.GetComponent<RectTransform>().sizeDelta=new Vector2(2160,3840);PrefabUtility.SaveAsPrefabAsset(go,D+"Skin_pic.prefab");UnityEngine.Object.DestroyImmediate(go);
  ValidateAndRender();
  var outDir=Path.Combine(Root,"mod_sebastiana");Directory.CreateDirectory(outDir);
  var builds=new[]{new AssetBundleBuild{assetBundleName="skin_marta_sebastiana",assetNames=new[]{D+"Skin.prefab"}},new AssetBundleBuild{assetBundleName="pic_marta_sebastiana",assetNames=new[]{D+"Skin_pic.prefab"}}};
  if(BuildPipeline.BuildAssetBundles(outDir,builds,BuildAssetBundleOptions.ChunkBasedCompression,BuildTarget.StandaloneWindows64)==null)throw new Exception("Bundle build failed");
  foreach(var name in new[]{"skin_marta_sebastiana","pic_marta_sebastiana"}) {var b=AssetBundle.LoadFromFile(Path.Combine(outDir,name));if(b==null)throw new Exception("Bundle load failed");if(b.LoadAllAssets<GameObject>().Length!=1)throw new Exception("Prefab count invalid");b.Unload(true);}
  File.WriteAllText(Path.Combine(Root,"unity_build_report.txt"),"Source: Sebastiana_source.glb (T-pose PBR model with its own rig, decimated to the game budget)\nCharacter: Marta only (native Mafra5/Marfa rig)\nUnity "+Application.unityVersion+"\nTriangles: "+triangles+"\nRigid head skinned to Head only: "+rigidHeadCount+" vertices\nReadable body and head, each with one wound-projection submesh.\nNative Marta skeleton: 68 joints, original local positions/rotations/scales.\nBoth Marta-specific bundles loaded successfully.\n");
  Debug.Log("SEBASTIANA_MARTA_BUILD_OK");
 }
 static void VerifyDecalMeshes(GameObject skin) {
  var renderers=skin.GetComponentsInChildren<SkinnedMeshRenderer>();
  if(renderers.Length!=2)throw new Exception("Expected body and rigid head for wound projection");
  foreach(var renderer in renderers) {
   var mesh=renderer.sharedMesh;
   if(!mesh.isReadable||mesh.subMeshCount!=1||mesh.boneWeights.Length!=mesh.vertexCount||
      mesh.normals.Length!=mesh.vertexCount||mesh.tangents.Length!=mesh.vertexCount)
    throw new Exception("Incomplete wound projection inputs: "+renderer.name);
  }
  var head=renderers.Single(r=>r.name=="SebastianaHead");
  var body=renderers.Single(r=>r.name=="SebastianaBody");
  var sharedHead=Array.IndexOf(body.bones,head.bones.Single());
  if(sharedHead<0||body.sharedMesh.bindposes[sharedHead]!=head.sharedMesh.bindposes[0])
   throw new Exception("Head and body disagree on the shared decal bind pose");
  var points=head.sharedMesh.vertices;
  var indices=head.sharedMesh.triangles;
  for(int i=0;i<indices.Length;i+=3)
   for(int j=0;j<3;j++)
    if(Vector3.Distance(points[indices[i+j]],points[indices[i+(j+1)%3]])>.19f)
     throw new Exception("Unexpected stretched triangle in the rigid head mesh: "+indices[i+j]+" "+points[indices[i+j]].ToString("F3")+" -> "+indices[i+(j+1)%3]+" "+points[indices[i+(j+1)%3]].ToString("F3")+" verts="+points.Length);
 }
 static void MakeSelectorPortrait() {
  // A supplied artwork (model/selector_portrait.png) is the selector image;
  // the 3D render below is the fallback when no artwork is present.
  string art=Path.Combine(Root,"model/selector_portrait.png");
  if(File.Exists(art)){File.Copy(art,D+"Skin_pic.png",true);return;}
  SebastianaBuild.MakeScene();var camera=UnityEngine.Object.FindObjectOfType<Camera>();camera.backgroundColor=new Color(0,0,0,0);camera.clearFlags=CameraClearFlags.SolidColor;
  var map=GameObject.Find("Skin").GetComponentsInChildren<Transform>().ToDictionary(t=>t.name,t=>t);
  // Relaxed standing pose with nothing in the hands: the selector shows the
  // character, not a weapon grip.
  RelaxedPose(map);
  PortraitLights();
  camera.orthographic=false;camera.fieldOfView=27f;camera.nearClipPlane=.1f;
  Capture("Sebastiana_Marta_selector",camera,new Vector3(-1.75f,1.15f,5.0f),true,1024,1536,new Vector3(0,.95f,0));
  File.Copy(Path.Combine(Root,"Sebastiana_Marta_selector.png"),D+"Skin_pic.png",true);
 }
 static void RelaxedPose(Dictionary<string,Transform> map) {
  foreach(var side in new[]{"Left","Right"}) {
   float x=side=="Left"?-1:1;
   Aim(map,side+"Arm",side+"ForeArm",new Vector3(x*.34f,-1f,.02f));
   Aim(map,side+"ForeArm",side+"Hand",new Vector3(x*.16f,-1f,.22f));
   Aim(map,side+"Hand",side+"HandMiddle1",new Vector3(x*.08f,-1f,.12f));
   // Palm towards the thigh: roll the hand about the forearm axis.
   var hand=map[side+"Hand"];var palmSide=map[side+"HandIndex1"].position-map[side+"HandPinky1"].position;
   var axis=(map[side+"HandMiddle1"].position-hand.position).normalized;
   var want=Vector3.ProjectOnPlane(Vector3.forward,axis);var have=Vector3.ProjectOnPlane(palmSide,axis);
   if(have.sqrMagnitude>1e-6&&want.sqrMagnitude>1e-6)hand.rotation=Quaternion.AngleAxis(Vector3.SignedAngle(have,want,axis),axis)*hand.rotation;
   RelaxFingers(map,side);
  }
 }
 static void RelaxFingers(Dictionary<string,Transform> map,string side) {
  float sign=side=="Right"?1:-1;
  foreach(var finger in new[]{"Index","Middle","Ring","Pinky"}) {
   float a=finger=="Index"?10:finger=="Middle"?14:finger=="Ring"?18:22;
   for(int j=1;j<=3;j++)map[side+"Hand"+finger+j].localRotation*=Quaternion.AngleAxis(sign*(j==1?a:a*.9f),Vector3.forward);
  }
  map[side+"HandThumb2"].localRotation*=Quaternion.AngleAxis(sign*10,Vector3.forward);
 }
 static void PortraitLights() {
  foreach(var l in UnityEngine.Object.FindObjectsOfType<Light>())UnityEngine.Object.DestroyImmediate(l.gameObject);
  void Add(string n,float intensity,Vector3 euler,Color c){var l=new GameObject(n,typeof(Light)).GetComponent<Light>();l.type=LightType.Directional;l.intensity=intensity;l.color=c;l.shadows=LightShadows.Soft;l.transform.rotation=Quaternion.Euler(euler);}
  Add("Key",.85f,new Vector3(28,145,0),new Color(1f,.96f,.9f));
  Add("Fill",.28f,new Vector3(12,-140,0),new Color(.85f,.9f,1f));
  Add("Rim",.55f,new Vector3(18,20,0),new Color(1f,.93f,.85f));
  RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;RenderSettings.ambientLight=new Color(.30f,.31f,.34f);
 }
 static void Capture(string name,Camera cam,Vector3 position,bool transparent=false,int width=1000,int height=1200,Vector3? target=null) {
  // Editor camera renders can reuse cached skinning when no player frame ran.
  // Render the current bone matrices explicitly for deterministic pose QA.
  var temps=new List<GameObject>();var meshes=new List<Mesh>();var renderers=UnityEngine.Object.FindObjectsOfType<SkinnedMeshRenderer>();
  foreach(var r in renderers) {
   var m=UnityEngine.Object.Instantiate(r.sharedMesh);var verts=m.vertices;var norms=m.normals;var bw=m.boneWeights;var bp=m.bindposes;
   var matrices=r.bones.Select((b,i)=>r.transform.worldToLocalMatrix*b.localToWorldMatrix*bp[i]).ToArray();
   for(int i=0;i<verts.Length;i++) {
    var w=bw[i];Vector3 p=Vector3.zero,n=Vector3.zero;
    int[] ids={w.boneIndex0,w.boneIndex1,w.boneIndex2,w.boneIndex3};float[] ws={w.weight0,w.weight1,w.weight2,w.weight3};
    for(int k=0;k<4;k++)if(ws[k]>0){p+=matrices[ids[k]].MultiplyPoint3x4(verts[i])*ws[k];if(norms.Length==verts.Length)n+=matrices[ids[k]].MultiplyVector(norms[i])*ws[k];}
    if(float.IsNaN(p.x)||p.magnitude>10)throw new Exception("Invalid deformed body vertex");verts[i]=p;if(norms.Length==verts.Length)norms[i]=n.normalized;
   }
   m.vertices=verts;if(norms.Length==verts.Length)m.normals=norms;m.RecalculateBounds();
   var o=new GameObject("PoseValidationMesh");o.transform.SetParent(r.transform,false);o.AddComponent<MeshFilter>().sharedMesh=m;o.AddComponent<MeshRenderer>().sharedMaterials=r.sharedMaterials;r.enabled=false;temps.Add(o);meshes.Add(m);
  }
  cam.transform.position=position;cam.transform.LookAt(target??new Vector3(0,1,0));var rt=new RenderTexture(width,height,24,RenderTextureFormat.ARGB32);cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;var t=new Texture2D(width,height,transparent?TextureFormat.RGBA32:TextureFormat.RGB24,false);t.ReadPixels(new Rect(0,0,width,height),0,0);t.Apply();File.WriteAllBytes(Path.Combine(Root,name+".png"),t.EncodeToPNG());cam.targetTexture=null;RenderTexture.active=null;UnityEngine.Object.DestroyImmediate(rt);UnityEngine.Object.DestroyImmediate(t);
  foreach(var r in renderers)r.enabled=true;foreach(var o in temps)UnityEngine.Object.DestroyImmediate(o);foreach(var m in meshes)UnityEngine.Object.DestroyImmediate(m);
 }
 static void Aim(Dictionary<string,Transform> bones,string bone,string child,Vector3 direction){var b=bones[bone];b.rotation=Quaternion.FromToRotation(bones[child].position-b.position,direction)*b.rotation;}
 static void GuardPose(Dictionary<string,Transform> map) {
  Aim(map,"RightArm","RightForeArm",new Vector3(.3f,-.25f,.7f));Aim(map,"RightForeArm","RightHand",new Vector3(-.05f,.05f,.85f));
  Aim(map,"LeftArm","LeftForeArm",new Vector3(-.2f,-.6f,-.1f));Aim(map,"LeftForeArm","LeftHand",new Vector3(.1f,-.6f,-.2f));
 }
 static void CloseFingers(Dictionary<string,Transform> map,string side) {
  float sign=side=="Right"?1:-1;
  foreach(var finger in new[]{"Index","Middle","Ring","Pinky"}) {
   float a=finger=="Index"?50:finger=="Pinky"?65:58;
   for(int j=1;j<=3;j++)map[side+"Hand"+finger+j].localRotation*=Quaternion.AngleAxis(sign*(j==1?a:j==2?72:40),Vector3.forward);
  }
  map[side+"HandThumb2"].localRotation*=Quaternion.AngleAxis(sign*30,Vector3.forward);
  map[side+"HandThumb3"].localRotation*=Quaternion.AngleAxis(sign*30,Vector3.forward);
 }
 [MenuItem("Sebastiana/Probar agarre de Marta")]
 public static void TestMartaGrip() {
  SebastianaBuild.MakeScene();var map=GameObject.Find("Skin").GetComponentsInChildren<Transform>().ToDictionary(t=>t.name,t=>t);
  PreviewSword(map);GuardPose(map);CloseFingers(map,"Right");CloseFingers(map,"Left");SceneView.RepaintAll();
 }
 static GameObject PreviewSword(Dictionary<string,Transform> map) {
  // Reference is local QA only. Neither this geometry nor the game reference
  // files are included in the Skin prefab or the Nexus bundles.
  string path=Path.Combine(Root,"game_reference/CupRapierPreview.json");if(!File.Exists(path))return null;
  var data=JsonUtility.FromJson<PreviewMesh>(File.ReadAllText(path));var parent=map["RightHandProp"];var verts=data.vertices;
  for(int i=0;i<verts.Length;i++)verts[i]=parent.InverseTransformPoint(verts[i]);
  var mesh=new Mesh();mesh.vertices=verts;mesh.triangles=data.triangles;mesh.RecalculateNormals();mesh.RecalculateBounds();
  var obj=new GameObject("MartaSword_QA_Only");obj.hideFlags=HideFlags.DontSave;obj.transform.SetParent(parent,false);obj.AddComponent<MeshFilter>().sharedMesh=mesh;
  var mat=new Material(Shader.Find("Standard"));mat.color=new Color(.45f,.47f,.5f);mat.SetFloat("_Metallic",.8f);mat.SetFloat("_Glossiness",.45f);obj.AddComponent<MeshRenderer>().sharedMaterial=mat;return obj;
 }
 public static void ValidateAndRender() {
  SebastianaBuild.MakeScene();var skin=GameObject.Find("Skin");var map=skin.GetComponentsInChildren<Transform>().ToDictionary(t=>t.name,t=>t);var saved=map.ToDictionary(k=>k.Key,k=>k.Value.localRotation);var cam=UnityEngine.Object.FindObjectOfType<Camera>();cam.orthographicSize=1.18f;
  Capture("Sebastiana_Unity_preview",cam,new Vector3(0,1,4));
  foreach(var s in new[]{"Left","Right"}){float sign=s=="Left"?-1:1;Aim(map,s+"Arm",s+"ForeArm",new Vector3(sign*.7f,.7f,0));Aim(map,s+"ForeArm",s+"Hand",new Vector3(sign*.5f,.7f,.3f));}
  Capture("Sebastiana_Unity_arms_up",cam,new Vector3(0,1,4));Capture("Sebastiana_Unity_arms_up_back",cam,new Vector3(0,1,-4));
  foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  Aim(map,"RightArm","RightForeArm",new Vector3(-.25f,-.25f,.7f));Aim(map,"RightForeArm","RightHand",new Vector3(.15f,.15f,.8f));
  Capture("Sebastiana_Unity_guard",cam,new Vector3(-2,1,4));
  foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  var sword=PreviewSword(map);GuardPose(map);CloseFingers(map,"Right");CloseFingers(map,"Left");
  Capture("Sebastiana_Marta_grip",cam,new Vector3(-1.5f,1.1f,4));
  cam.orthographic=false;cam.fieldOfView=65f;cam.nearClipPlane=.03f;
  var eye=map["Head"].position+new Vector3(0,.09f,.07f);
  Capture("Sebastiana_Marta_fpp",cam,eye,false,1280,720,eye+new Vector3(0,-.34f,1));
  var displacedEye=eye+new Vector3(.26f,.04f,.09f);
  Capture("Sebastiana_Marta_fpp_offset",cam,displacedEye,false,1280,720,displacedEye+new Vector3(0,-.34f,1));
  Capture("Sebastiana_Marta_fpp_down",cam,eye,false,1280,720,eye+new Vector3(0,-1,.44f));
  Capture("Sebastiana_Marta_fpp_wide",cam,new Vector3(-1.4f,1.4f,3.2f),false,1080,1080);
  cam.orthographic=true;
  var prop=map["RightHandProp"];cam.orthographicSize=.19f;Capture("Sebastiana_Marta_hand_closeup",cam,prop.position+new Vector3(.3f,.2f,.65f),false,1000,1000,prop.position);cam.orthographicSize=1.18f;
  var rightForearm=map["RightForeArm"];
  var rightAxis=map["RightHand"].position-rightForearm.position;
  rightForearm.rotation=Quaternion.AngleAxis(65,rightAxis)*rightForearm.rotation;
  Capture("Sebastiana_Marta_pronation",cam,new Vector3(-1.5f,1.1f,4));
  UnityEngine.Object.DestroyImmediate(sword);foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  map["Neck"].localRotation*=Quaternion.Euler(-18,22,-9);
  map["Head"].localRotation*=Quaternion.Euler(20,32,15);
  map["Spine1"].localRotation*=Quaternion.Euler(9,-26,13);
  cam.orthographicSize=.35f;
  Capture("Sebastiana_Unity_head_test",cam,new Vector3(.45f,1.65f,3),false,900,900,new Vector3(0,1.52f,0));
  foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  foreach(var side in new[]{"Left","Right"}) {
   float sign=side=="Right"?1:-1;
   Aim(map,side+"Arm",side+"ForeArm",new Vector3(sign*.78f,.56f,.28f));
   Aim(map,side+"ForeArm",side+"Hand",new Vector3(sign*.05f,.78f,-.5f));
  }
  cam.orthographic=false;
  Capture("Sebastiana_Marta_underarms",cam,new Vector3(.08f,1.04f,.94f),false,1000,950,new Vector3(0,1.49f,0));
  foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  foreach(var side in new[]{"Right","Left"}) {
   float sign=side=="Right"?1:-1;
   Aim(map,side+"Arm",side+"ForeArm",new Vector3(sign*.39f,-.03f,.94f));
   Aim(map,side+"ForeArm",side+"Hand",new Vector3(sign*.38f,.04f,.94f));
   CloseFingers(map,side);
   var target=Vector3.Lerp(map[side+"Arm"].position,map[side+"Hand"].position,.34f);
   Capture("Sebastiana_Marta_extension_"+side,cam,new Vector3(sign*1.24f,1.48f,-1.55f),false,1000,900,target);
   Capture("Sebastiana_Marta_inner_"+side,cam,target+new Vector3(-sign*.58f,-.45f,1.0f),false,1000,900,target);
   foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
   Aim(map,side+"Arm",side+"ForeArm",new Vector3(sign*.14f,.60f,.78f));
   Aim(map,side+"ForeArm",side+"Hand",new Vector3(sign*.09f,.72f,.60f));
   target=Vector3.Lerp(map[side+"Arm"].position,map[side+"ForeArm"].position,.44f);
   Capture("Sebastiana_Marta_raised_"+side,cam,target+new Vector3(sign*.88f,-.10f,-1.18f),false,1000,900,target);
   foreach(var kv in saved)map[kv.Key].localRotation=kv.Value;
  }
  UnityEditor.SceneManagement.EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(),D+"SebastianaPreview.unity");
 }
}
