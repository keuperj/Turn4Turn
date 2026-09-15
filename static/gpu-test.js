const $=id=>document.getElementById(id);
const stageNames=['secure','api','adapter','device','compute','canvas'];

function stage(name,state,note){
  const element=$(`stage-${name}`);element.className=state;
  if(note)element.querySelector('small').textContent=note;
}
function text(value){return value===undefined||value===null||value===''?'Not reported':String(value)}
function bytes(value){
  if(!Number.isFinite(value))return text(value);
  const units=['B','KiB','MiB','GiB'];let size=value,index=0;
  while(size>=1024&&index<units.length-1){size/=1024;index++}
  return `${size>=10||index===0?size.toFixed(0):size.toFixed(1)} ${units[index]}`;
}
function rows(target,values,className){
  target.replaceChildren(...values.map(([label,value])=>{
    const item=document.createElement('div');if(className)item.className=className;
    const key=document.createElement(className?'small':'dt');key.textContent=label;
    const result=document.createElement(className?'strong':'dd');result.textContent=text(value);
    item.append(key,result);return item;
  }));
}
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
    `For temporary Chromium testing only, add this origin to chrome://flags/#unsafely-treat-insecure-origin-as-secure: ${location.origin}`,
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
function showFailure(kind,error){
  const summary=$('summary');summary.className='summary fail';
  $('summary-title').textContent='WebGPU is not ready';$('summary-text').textContent='The game should continue using WebGL on this browser.';
  $('failure-reason').textContent=error;$('help').hidden=false;$('details').hidden=true;
  $('hints').replaceChildren(...hintsFor(kind).map(message=>{const li=document.createElement('li');li.textContent=message;return li}));
}
function showDetails(adapter,info,fallback){
  const kind=info.type||info.architecture||(fallback?'Software fallback':'Hardware adapter');
  rows($('identity'),[
    ['Type',kind],['Vendor',info.vendor],['Architecture',info.architecture],
    ['Device',info.device],['Description',info.description],['Fallback adapter',fallback?'Yes':'No'],
  ]);
  const limits=adapter.limits;
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
  const features=[...adapter.features].sort();$('feature-count').textContent=features.length;
  $('features').replaceChildren(...features.map(value=>{const code=document.createElement('code');code.textContent=value;return code}));
  $('details').hidden=false;
}

async function run(){
  $('details').hidden=true;$('help').hidden=true;
  const summary=$('summary');summary.className='summary pending';
  $('summary-title').textContent='Testing this browser…';$('summary-text').textContent='Requesting a high-performance GPU adapter.';
  for(const name of stageNames)stage(name,'','Waiting');
  if(!window.isSecureContext){stage('secure','fail','HTTPS required');showFailure('secure','This page is not a secure browser context.');return}
  stage('secure','pass','Secure context');
  if(!navigator.gpu){stage('api','fail','Unavailable');showFailure('api','This browser does not expose navigator.gpu.');return}
  stage('api','pass','Available');
  let current='adapter',device=null;
  try{
    let adapter=null;
    for(let attempt=1;attempt<=3&&!adapter;attempt++){
      adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});
      if(!adapter)await new Promise(resolve=>setTimeout(resolve,500));
    }
    if(!adapter){stage('adapter','fail','Not found');showFailure('adapter','The browser could not obtain a WebGPU adapter.');return}
    stage('adapter','pass','Detected');
    const info=adapter.info||(adapter.requestAdapterInfo?await adapter.requestAdapterInfo():{});
    const fallback=Boolean(info.isFallbackAdapter??adapter.isFallbackAdapter);
    showDetails(adapter,info,fallback);
    current='device';device=await adapter.requestDevice();stage('device','pass','Created');
    let lost=null;device.lost.then(value=>{lost=`GPU device lost (${value.reason}): ${value.message}`});

    current='compute';
    const input=new Uint32Array([1,2,3,4]);
    const source=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});
    const output=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC});
    const read=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
    device.queue.writeBuffer(source,0,input);
    const module=device.createShaderModule({code:'@group(0) @binding(0) var<storage,read> a:array<u32>; @group(0) @binding(1) var<storage,read_write> b:array<u32>; @compute @workgroup_size(4) fn main(@builtin(global_invocation_id) id:vec3<u32>){b[id.x]=a[id.x]*2u+1u;}'});
    const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'main'}});
    const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:source}},{binding:1,resource:{buffer:output}}]});
    let encoder=device.createCommandEncoder(),pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(1);pass.end();encoder.copyBufferToBuffer(output,0,read,0,input.byteLength);device.queue.submit([encoder.finish()]);
    await read.mapAsync(GPUMapMode.READ);if(lost)throw new Error(lost);
    const result=[...new Uint32Array(read.getMappedRange().slice(0))];read.unmap();source.destroy();output.destroy();read.destroy();
    if(result.join(',')!=='3,5,7,9')throw new Error(`Compute shader returned ${result.join(', ')} instead of 3, 5, 7, 9.`);
    stage('compute','pass','Passed');

    current='canvas';const canvas=document.createElement('canvas');canvas.width=canvas.height=4;
    const context=canvas.getContext('webgpu');if(!context)throw new Error('A WebGPU canvas context could not be created.');
    context.configure({device,format:navigator.gpu.getPreferredCanvasFormat(),alphaMode:'opaque'});
    encoder=device.createCommandEncoder();pass=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:{r:.1,g:.2,b:.3,a:1},loadOp:'clear',storeOp:'store'}]});pass.end();device.queue.submit([encoder.finish()]);
    await device.queue.onSubmittedWorkDone();if(lost)throw new Error(lost);stage('canvas','pass','Passed');
    summary.className='summary pass';$('summary-title').textContent=fallback?'WebGPU works through a fallback adapter':'WebGPU is ready';
    $('summary-text').textContent=fallback?'Compute and rendering passed, but performance may be limited.':'Hardware-accelerated compute and rendering both passed.';
  }catch(error){stage(current,'fail','Failed');showFailure(current,`${error.name||'Error'}: ${error.message||error}`)}
  finally{if(device)device.destroy()}
}

$('retry').addEventListener('click',run);run();
