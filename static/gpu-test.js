/** @fileoverview Present WebGPU diagnostics, adapter details, and recovery guidance. */
import {testWebGPU} from './webgpu-check.js';

const $=id=>document.getElementById(id);
const stageNames=['secure','api','adapter','device','compute','canvas'];

/** Update one displayed WebGPU diagnostic stage. */
function stage(name,state,note){
  const element=$(`stage-${name}`);element.className=state;
  if(note)element.querySelector('small').textContent=note;
}
/** Format unavailable diagnostic values consistently. */
function text(value){return value===undefined||value===null||value===''?'Not reported':String(value)}
/** Format a capacity value with binary size units. */
function bytes(value){
  if(!Number.isFinite(value))return text(value);
  const units=['B','KiB','MiB','GiB'];let size=value,index=0;
  while(size>=1024&&index<units.length-1){size/=1024;index++}
  return `${size>=10||index===0?size.toFixed(0):size.toFixed(1)} ${units[index]}`;
}
/** Populate a diagnostic definition list or metric grid. */
function rows(target,values,className){
  target.replaceChildren(...values.map(([label,value])=>{
    const item=document.createElement('div');if(className)item.className=className;
    const key=document.createElement(className?'small':'dt');key.textContent=label;
    const result=document.createElement(className?'strong':'dd');result.textContent=text(value);
    item.append(key,result);return item;
  }));
}
/**
 * Build browser-specific recovery steps for the failed diagnostic stage.
 *
 * @param {string} kind Name of the first failed WebGPU stage.
 * @returns {string[]} Actionable hints for the visiting browser.
 */
function hintsFor(kind){
  const firefox=/Firefox\//.test(navigator.userAgent);
  const common=firefox?[
    'Update Firefox and the graphics driver, then restart Firefox.',
    'Keep hardware acceleration enabled under Settings → General → Performance, and inspect the Graphics section of about:support.',
  ]:[
    'Update the browser and graphics driver, then restart the browser.',
    'Enable hardware acceleration in the browser settings and inspect chrome://gpu for blocked or disabled features.',
  ];
  if(kind==='secure')return [
    'WebGPU requires HTTPS. The localhost exception does not apply when this server is opened through a network IP.',
    'Serve Turn4Turn through an HTTPS reverse proxy for normal use.',
    ...(firefox?[
      `For a trusted local server with a self-signed certificate, open https://${location.host}, choose Advanced, then Accept the Risk and Continue.`,
      'If Firefox does not offer that button, install the local certificate authority in Firefox or the operating-system trust store.',
      'An HTTPS-Only Mode exception merely permits HTTP; it does not turn an HTTP address into the secure context WebGPU requires.',
    ]:[
      `For temporary Chromium testing only, add this origin to chrome://flags/#unsafely-treat-insecure-origin-as-secure: ${location.origin}`,
    ]),
  ];
  if(kind==='api')return [
    ...common,
    ...(firefox?[
      'Open about:config, set dom.webgpu.enabled to true, and restart Firefox.',
      'On Linux or an Intel Mac, use the current Firefox Nightly build; WebGPU is not enabled by default in regular Firefox builds on those platforms.',
    ]:[
      'Use a current Chromium, Chrome, Edge, or another browser release that supports WebGPU.',
      'On Linux development systems, enable chrome://flags/#enable-unsafe-webgpu and restart Chromium.',
    ]),
  ];
  if(kind==='adapter')return [
    ...common,
    ...(firefox?[
      'Open about:config, confirm dom.webgpu.enabled is true, and restart Firefox.',
      'On Linux, use Firefox Nightly and verify that Vulkan and your GPU driver are current.',
    ]:[
      'On Linux, verify Vulkan is installed and working with: vulkaninfo --summary',
      'For Chromium development, enable Unsafe WebGPU Support and Vulkan in chrome://flags, then restart.',
    ]),
    'Virtual machines, containers, and remote desktops must expose a hardware GPU to the browser.',
  ];
  return [...common,'Close other GPU-heavy applications and reload this test.',firefox?'Review about:support for blocked graphics features or device-reset errors.':'Check chrome://gpu for driver workarounds, device loss, or WebGPU errors.'];
}
/** Show failure. */
function showFailure(kind,error){
  const summary=$('summary');summary.className='summary fail';
  $('summary-title').textContent='WebGPU is not ready';$('summary-text').textContent='The game should continue using WebGL on this browser.';
  $('failure-reason').textContent=error;$('help').hidden=false;$('details').hidden=true;
  $('hints').replaceChildren(...hintsFor(kind).map(message=>{const li=document.createElement('li');li.textContent=message;return li}));
}
/** Show details. */
function showDetails(result){
  const {info,fallback,limits,features}=result;
  const kind=info.type||info.architecture||(fallback?'Software fallback':'Hardware adapter');
  rows($('identity'),[
    ['Type',kind],['Vendor',info.vendor],['Architecture',info.architecture],
    ['Device',info.device],['Description',info.description],['Fallback adapter',fallback?'Yes':'No'],
  ]);
  rows($('limits'),[
    ['Maximum 2D texture',`${limits.maxTextureDimension2D} × ${limits.maxTextureDimension2D}`],
    ['Maximum buffer',bytes(limits.maxBufferSize)],
    ['Storage binding',bytes(limits.maxStorageBufferBindingSize)],
    ['Uniform binding',bytes(limits.maxUniformBufferBindingSize)],
    ['Bind groups',limits.maxBindGroups],
    ['Vertex attributes',limits.maxVertexAttributes],
    ['Compute workgroup',`${limits.maxComputeWorkgroupSizeX} × ${limits.maxComputeWorkgroupSizeY} × ${limits.maxComputeWorkgroupSizeZ}`],
    ['Compute invocations',limits.maxComputeInvocationsPerWorkgroup],
    ['Workgroups / dimension',limits.maxComputeWorkgroupsPerDimension],
  ],'limit');
  $('feature-count').textContent=features.length;
  $('features').replaceChildren(...features.map(value=>{const code=document.createElement('code');code.textContent=value;return code}));
  $('details').hidden=false;
}

/** Run the complete WebGPU diagnostic and render its result. */
async function run(){
  $('details').hidden=true;$('help').hidden=true;
  const summary=$('summary');summary.className='summary pending';
  $('summary-title').textContent='Testing this browser…';$('summary-text').textContent='Requesting a high-performance GPU adapter.';
  for(const name of stageNames)stage(name,'','Waiting');
  const result=await testWebGPU({onStage:stage});
  if(!result.ok){showFailure(result.stage,result.reason);return}
  showDetails(result);
  summary.className='summary pass';
  $('summary-title').textContent=result.fallback?'WebGPU works through a fallback adapter':'WebGPU is ready';
  $('summary-text').textContent=result.fallback?'Compute and rendering passed, but performance may be limited.':'Hardware-accelerated compute and rendering both passed.';
}

$('retry').addEventListener('click',run);run();
