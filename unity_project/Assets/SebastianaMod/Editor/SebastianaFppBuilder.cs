using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using HutongGames.PlayMaker;
using A = HutongGames.PlayMaker.Actions;

public static class SebastianaFppBuilder {
 static FsmOwnerDefault Target(FsmGameObject gameObject) {
  return new FsmOwnerDefault { OwnerOption = OwnerDefaultOption.SpecifyGameObject, GameObject = gameObject };
 }

 public static void Attach(GameObject skin) {
  var controller = new GameObject("SebastianaVisibility");
  controller.transform.SetParent(skin.transform, false);
  var component = controller.AddComponent<PlayMakerFSM>();
  component.FsmName = "SebastianaSuppressStockFace";
  var fsm = component.Fsm;
  fsm.DataVersion = 2;

  var loader = new FsmGameObject("SkinLoader") { UseVariable = true };
  var animator = new FsmGameObject("MartaAnimator") { UseVariable = true };
  // The native toTPP event can reactivate these four stock objects during
  // a wide shot, including the original face. Scope lookups to this fighter.
  var stockNames = new[] { "headMESH", "CC_Base_Teeth", "CC_Base_Tongue", "polySurface3",
   // Marta's wound overlays are copies of her own body shape. With a custom
   // skin they would float over it as a second, transparent body when hit.
   "DecalArmpitSlice", "DecalBloody", "DecalBloodyLeft", "DecalBloodyRight", "DecalChoppedHand",
   "DecalChoppedHead", "DecalHead", "DecalHeadSmall", "DecalLeftArm", "DecalLeftForeArm",
   "DecalMarfaGrab_A", "DecalMarfaGrab_B", "DecalRightArm", "DecalRightForeArm",
   "DecalSpine1", "DecalSpine1Small", "DecalStomach" };
  var stockParts = stockNames.Select(name => new FsmGameObject(name) { UseVariable = true }).ToArray();
  fsm.Variables.GameObjectVariables = new[] { loader, animator }.Concat(stockParts).ToArray();
  var finished = FsmEvent.GetFsmEvent("FINISHED");
  fsm.Events = new[] { finished };

  var startup = new FsmState(fsm) {
   Name = "WaitForSkinLoader",
   Actions = new FsmStateAction[] { new A.Wait { time = .45f, finishEvent = finished } }
  };
  var resolveActions = new List<FsmStateAction> {
   // The game instantiates Skin under the bundle loader, which is a child
   // of the fighter's Animator object.
   new A.GetParent { gameObject = Target(new FsmGameObject { Value = skin }), storeResult = loader },
   new A.GetParent { gameObject = Target(loader), storeResult = animator }
  };
  for (int i = 0; i < stockNames.Length; i++) {
   resolveActions.Add(new A.GetChild {
    gameObject = Target(animator), childName = stockNames[i], withTag = "Untagged", storeResult = stockParts[i]
   });
  }
  var resolve = new FsmState(fsm) { Name = "ResolveStockFace", Actions = resolveActions.ToArray() };
  var suppress = new FsmState(fsm) {
   Name = "KeepStockFaceHidden",
   Actions = stockParts.Select(part => (FsmStateAction)new A.ActivateGameObject {
    gameObject = Target(part), activate = false, recursive = false, everyFrame = true, resetOnExit = false
   }).ToArray()
  };
  startup.Transitions = new[] { new FsmTransition { FsmEvent = finished, ToState = resolve.Name } };
  resolve.Transitions = new[] { new FsmTransition { FsmEvent = finished, ToState = suppress.Name } };
  fsm.States = new[] { startup, resolve, suppress };
  fsm.StartState = startup.Name;
  fsm.SaveActions();
  component.OnBeforeSerialize();
  if (fsm.States.Any(state => state.ActionData.ActionCount != state.Actions.Length))
   throw new Exception("Stock face controller serialization mismatch");
 }
}
