using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using UnityEditor;
using UnityEditor.SceneManagement;

public static class SebastianaBuild {
 const string Dir="Assets/SebastianaMod/";
 static string Root { get { return Path.GetFullPath(Path.Combine(Application.dataPath,"../..")); } }
 [MenuItem("Sebastiana/Construir mod")]
 public static void Build() { SebastianaFinalBuild.Build(); }
 public static void LegacyBuild() {
  PlayerSettings.productName="Sebastiana - Hellish Quart Mod";
  PlayerSettings.companyName="SebastianaMod";
  AssetDatabase.Refresh();
  var importer=(ModelImporter)AssetImporter.GetAtPath(Dir+"Skin.fbx");
  importer.isReadable=true; importer.importAnimation=false;
  importer.animationType=ModelImporterAnimationType.Generic;
  importer.optimizeGameObjects=false; importer.meshCompression=ModelImporterMeshCompression.Off;
  importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.SaveAndReimport();
  var tex=(TextureImporter)AssetImporter.GetAtPath(Dir+"Sebastiana_BaseColor.png");
  tex.maxTextureSize=2048;tex.sRGBTexture=true;tex.alphaSource=TextureImporterAlphaSource.None;tex.SaveAndReimport();
  var normal=(TextureImporter)AssetImporter.GetAtPath(Dir+"Sebastiana_Normal.png");
  normal.textureType=TextureImporterType.NormalMap;normal.maxTextureSize=2048;normal.SaveAndReimport();
  var mat=AssetDatabase.LoadAssetAtPath<Material>(Dir+"Sebastiana.mat");
  if(mat==null){mat=new Material(Shader.Find("Standard"));AssetDatabase.CreateAsset(mat,Dir+"Sebastiana.mat");}
  mat.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(Dir+"Sebastiana_BaseColor.png");
  mat.SetTexture("_BumpMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Dir+"Sebastiana_Normal.png"));
  mat.EnableKeyword("_NORMALMAP");mat.SetFloat("_Metallic",0.05f);mat.SetFloat("_Glossiness",0.25f);
  var go=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Dir+"Skin.fbx"));go.name="Skin";
  foreach(var r in go.GetComponentsInChildren<SkinnedMeshRenderer>()) {
   r.sharedMaterials=Enumerable.Repeat(mat,r.sharedMaterials.Length).ToArray();r.updateWhenOffscreen=true;
   r.localBounds=new Bounds(new Vector3(0,1,0),new Vector3(4,4,4));
   if(!r.sharedMesh.isReadable)throw new Exception("Mesh must be readable");
  }
  var bones=go.GetComponentsInChildren<Transform>();
  var refGo=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/HellishQuartModdingKit/Assets/HQMaleSkeleton/Skin.fbx"));
  float maxError=0;
  foreach(var b in refGo.GetComponentsInChildren<Transform>()) {
   var a=bones.FirstOrDefault(x=>x.name==b.name);if(a!=null)maxError=Mathf.Max(maxError,Vector3.Distance(a.position,b.position));
  }
  UnityEngine.Object.DestroyImmediate(refGo);
  if(maxError>0.001f)throw new Exception("Skeleton mismatch: "+maxError);
  PrefabUtility.SaveAsPrefabAsset(go,Dir+"Skin.prefab");UnityEngine.Object.DestroyImmediate(go);
  var picImport=(TextureImporter)AssetImporter.GetAtPath(Dir+"Skin_pic.png");
  picImport.textureType=TextureImporterType.Sprite;picImport.spriteImportMode=SpriteImportMode.Single;picImport.maxTextureSize=1024;picImport.SaveAndReimport();
  var pic=new GameObject("Skin_pic",typeof(RectTransform),typeof(CanvasRenderer),typeof(Image));pic.layer=5;
  pic.GetComponent<Image>().sprite=AssetDatabase.LoadAssetAtPath<Sprite>(Dir+"Skin_pic.png");pic.GetComponent<Image>().raycastTarget=false;
  pic.GetComponent<RectTransform>().sizeDelta=new Vector2(1000,1100);
  PrefabUtility.SaveAsPrefabAsset(pic,Dir+"Skin_pic.prefab");UnityEngine.Object.DestroyImmediate(pic);
  var outDir=Path.Combine(Root,"mod_sebastiana");Directory.CreateDirectory(outDir);
  var builds=new[]{new AssetBundleBuild{assetBundleName="skin_universal_sebastiana",assetNames=new[]{Dir+"Skin.prefab"}},new AssetBundleBuild{assetBundleName="pic_universal_sebastiana",assetNames=new[]{Dir+"Skin_pic.prefab"}}};
  var manifest=BuildPipeline.BuildAssetBundles(outDir,builds,BuildAssetBundleOptions.ChunkBasedCompression,BuildTarget.StandaloneWindows64);
  if(manifest==null)throw new Exception("Bundle build failed");
  foreach(var n in new[]{"skin_universal_sebastiana","pic_universal_sebastiana"}) {
   var bundle=AssetBundle.LoadFromFile(Path.Combine(outDir,n));if(bundle==null)throw new Exception("Cannot load bundle "+n);
   if(bundle.LoadAllAssets<GameObject>().Length!=1)throw new Exception("Expected one prefab in "+n);bundle.Unload(true);
  }
  MakeScene();
  var cam=UnityEngine.Object.FindObjectOfType<Camera>();
  var target=new RenderTexture(1000,1100,24);cam.targetTexture=target;cam.Render();
  RenderTexture.active=target;var preview=new Texture2D(1000,1100,TextureFormat.RGB24,false);preview.ReadPixels(new Rect(0,0,1000,1100),0,0);preview.Apply();
  File.WriteAllBytes(Path.Combine(Root,"Sebastiana_Unity_preview.png"),preview.EncodeToPNG());
  cam.targetTexture=null;RenderTexture.active=null;UnityEngine.Object.DestroyImmediate(target);UnityEngine.Object.DestroyImmediate(preview);
  File.WriteAllText(Path.Combine(Root,"unity_build_report.txt"),"Unity "+Application.unityVersion+"\nWindows64 bundles loaded successfully\nOriginal skeleton max position error: "+maxError+" m\nRead/Write enabled. No animation retargeting or optimized bone hierarchy.\n");
  Debug.Log("SEBASTIANA_BUILD_OK");
 }
 [MenuItem("Sebastiana/Abrir escena")]
 public static void MakeScene() {
  var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
  var go=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Dir+"Skin.prefab"));
  var camObj=new GameObject("PreviewCamera",typeof(Camera));var camera=camObj.GetComponent<Camera>();camera.clearFlags=CameraClearFlags.SolidColor;camera.backgroundColor=new Color(.13f,.14f,.16f);camera.orthographic=true;camera.orthographicSize=1.12f;
  camera.transform.position=new Vector3(0,1.02f,4);camera.transform.LookAt(new Vector3(0,1.02f,0));
  var light=new GameObject("KeyLight",typeof(Light));light.GetComponent<Light>().type=LightType.Directional;light.GetComponent<Light>().intensity=1.1f;light.transform.rotation=Quaternion.Euler(35,160,0);
  var fill=new GameObject("FillLight",typeof(Light));fill.GetComponent<Light>().type=LightType.Directional;fill.GetComponent<Light>().intensity=.6f;fill.transform.rotation=Quaternion.Euler(20,-70,0);
  RenderSettings.ambientLight=new Color(.5f,.5f,.5f);
  EditorSceneManager.SaveScene(scene,Dir+"SebastianaPreview.unity");
  EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(Dir+"SebastianaPreview.unity",true)};
  Selection.activeGameObject=go;if(SceneView.lastActiveSceneView!=null)SceneView.lastActiveSceneView.FrameSelected();
 }
 [MenuItem("Sebastiana/Probar brazos arriba")]
 public static void TestArms() {
  var skin=GameObject.Find("Skin");if(skin==null)return;
  foreach(var side in new[]{"Left","Right"}) {
   var arm=skin.GetComponentsInChildren<Transform>().First(t=>t.name==side+"Arm");
   var elbow=skin.GetComponentsInChildren<Transform>().First(t=>t.name==side+"ForeArm");
   var target=new Vector3(side=="Left"?-.8f:.8f,.6f,0);
   arm.rotation=Quaternion.FromToRotation(elbow.position-arm.position,target)*arm.rotation;
  }
  SceneView.RepaintAll();
 }
 [MenuItem("Sebastiana/Restaurar pose")]
 public static void ResetPose(){MakeScene();}
}
