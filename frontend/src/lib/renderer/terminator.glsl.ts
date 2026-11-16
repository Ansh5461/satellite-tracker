/** Atmosphere rim for Earth sphere (earth surface uses MeshStandardMaterial). */

export const atmosphereVertex = /* glsl */ `
varying vec3 vNormalV;
varying vec3 vViewV;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vNormalV = normalize(normalMatrix * normal);
  vViewV = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}
`;

export const atmosphereFragment = /* glsl */ `
varying vec3 vNormalV;
varying vec3 vViewV;
void main() {
  float fresnel = pow(1.0 - abs(dot(normalize(vNormalV), normalize(vViewV))), 2.4);
  vec3 col = mix(vec3(0.12, 0.35, 0.85), vec3(0.65, 0.88, 1.0), fresnel);
  gl_FragColor = vec4(col, fresnel * 0.65);
}
`;
