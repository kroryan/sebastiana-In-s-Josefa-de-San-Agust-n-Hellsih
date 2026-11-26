Shader "Sebastiana/DetailedTwoSided" {
 Properties {
  _MainTex ("Color", 2D) = "white" {}
  _BumpMap ("Normal", 2D) = "bump" {}
  _ORM ("Occlusion Roughness Metallic", 2D) = "white" {}
  _BumpScale ("Normal strength", Range(0,2)) = 1
  _ColorDepth ("Color depth (deeper mid and light tones)", Range(1,2)) = 1.3
  _Saturation ("Saturation", Range(0,2)) = 1.15
  [HideInInspector] _HeadCameraRadius ("Eye clearance near the head pivot", Float) = 0
  [HideInInspector] _HeadRestAnchor ("Head pivot in skin space", Vector) = (0,1.6,0,1)
 }
 SubShader {
  Tags { "RenderType"="Opaque" "Queue"="Geometry" }
  LOD 300
  Cull Off
  CGPROGRAM
  #pragma surface surf Standard fullforwardshadows addshadow vertex:EyeClearance
  #pragma target 3.0
  #include "UnityStandardUtils.cginc"
  sampler2D _MainTex, _BumpMap, _ORM;
  half _BumpScale;
  half _ColorDepth, _Saturation;
  float _HeadCameraRadius;
  float4 _HeadRestAnchor;
  struct Input {float2 uv_MainTex; float3 worldPos; float4 color : COLOR; float facing : VFACE;};
  float EyeProximity() {
   float3 root = mul(unity_ObjectToWorld, float4(0,0,0,1)).xyz;
   float3 toEye = _WorldSpaceCameraPos - root;
   return (1 - smoothstep(.21, .40, length(toEye.xz))) *
          smoothstep(1.21, 1.40, toEye.y) * (1 - smoothstep(1.96, 2.12, toEye.y));
  }
  void EyeClearance(inout appdata_full v) {
   #if !defined(UNITY_PASS_SHADOWCASTER) && !defined(UNITY_PASS_META)
   if (_HeadCameraRadius == 0 && unity_OrthoParams.w < 0.5) {
    // The game's eye camera can be directly above the chest in a downward
    // view. Move the torso visually behind the eye, leaving the weapon arm
    // aligned with the real hand and preserving the unmodified wide view.
    float3 forward = -UNITY_MATRIX_V[2].xyz;
    forward.y = 0;
    forward *= rsqrt(max(dot(forward,forward), .04));
    float offset = .29 * EyeProximity() * (1 - v.color.a);
    v.vertex.xyz -= mul((float3x3)unity_WorldToObject, forward * offset);
   }
   #endif
  }
  void surf (Input IN, inout SurfaceOutputStandard o) {
   #if !defined(UNITY_PASS_SHADOWCASTER) && !defined(UNITY_PASS_META)
   if (unity_OrthoParams.w < 0.5) {
    if (_HeadCameraRadius > 0) {
     float3 headPivot = mul(unity_ObjectToWorld, _HeadRestAnchor).xyz;
     clip(distance(_WorldSpaceCameraPos, headPivot) - _HeadCameraRadius);
    } else if (EyeProximity() > .01) {
     float cameraDistance = distance(_WorldSpaceCameraPos, IN.worldPos);
     float eye = EyeProximity();
     if (IN.facing < 0) clip(cameraDistance - eye * lerp(1.35, 0.13, IN.color.a));
     float bodyClearance = lerp(0.12, 0.39, IN.color.r);
     clip(cameraDistance - eye * lerp(bodyClearance, 0.04, IN.color.a));
    }
   }
   #endif
   fixed4 color=tex2D(_MainTex, IN.uv_MainTex);
   half3 orm=tex2D(_ORM, IN.uv_MainTex).rgb;
   // Same hues, less washed out in the game's lighting: a gentle curve
   // deepens mid and light tones, then a small saturation lift.
   half3 albedo=pow(saturate(color.rgb), _ColorDepth);
   half luma=dot(albedo, half3(.2126,.7152,.0722));
   o.Albedo=saturate(lerp(luma.xxx, albedo, _Saturation));
   o.Normal=UnpackScaleNormal(tex2D(_BumpMap, IN.uv_MainTex), _BumpScale);
   o.Normal*=IN.facing>=0 ? 1 : -1;
   o.Occlusion=lerp(0.5,1,orm.r);
   o.Smoothness=clamp((1-orm.g)*0.45,0.05,0.35);
   o.Metallic=min(orm.b,0.15);
   o.Alpha=1;
  }
  ENDCG
 }
 FallBack "Diffuse"
}
