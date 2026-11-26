// Editor-only serializers and QA implementations for actions already present
// in Hellish Quart. The bundle stores their native names and parameters only.
using UnityEngine;
using HutongGames.PlayMaker;
namespace HutongGames.PlayMaker.Actions {
 public class Wait:FsmStateAction {
  public FsmFloat time;public FsmEvent finishEvent;public bool realTime;float start;
  public override void OnEnter(){start=Time.realtimeSinceStartup;}
  public override void OnUpdate(){if(Time.realtimeSinceStartup-start>=time.Value){Fsm.Event(finishEvent);Finish();}}
 }
 public class GetParent:FsmStateAction {
  public FsmOwnerDefault gameObject;public FsmGameObject storeResult;
  public override void OnEnter(){var g=Fsm.GetOwnerDefaultTarget(gameObject);storeResult.Value=g&&g.transform.parent?g.transform.parent.gameObject:null;Finish();}
 }
 public class GetChild:FsmStateAction {
  public FsmOwnerDefault gameObject;public FsmString childName;public FsmString withTag;public FsmGameObject storeResult;
  public override void OnEnter(){var g=Fsm.GetOwnerDefaultTarget(gameObject);storeResult.Value=null;if(g)foreach(var t in g.GetComponentsInChildren<Transform>(true))if(t.name==childName.Value){storeResult.Value=t.gameObject;break;}Finish();}
 }
 public class ActivateGameObject:FsmStateAction {
  public FsmOwnerDefault gameObject;public FsmBool activate;public FsmBool recursive;public bool resetOnExit;public bool everyFrame;
  public override void OnEnter(){var g=Fsm.GetOwnerDefaultTarget(gameObject);if(g)g.SetActive(activate.Value);if(!everyFrame)Finish();}
  public override void OnUpdate(){if(everyFrame){var g=Fsm.GetOwnerDefaultTarget(gameObject);if(g)g.SetActive(activate.Value);}}
 }
}
