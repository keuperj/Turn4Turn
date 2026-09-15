/** @fileoverview Run the bounded WebGPU capability probe shared by game and diagnostics. */
const LIMIT_NAMES=[
  'maxTextureDimension2D','maxBufferSize','maxStorageBufferBindingSize',
  'maxUniformBufferBindingSize','maxBindGroups','maxVertexAttributes',
  'maxComputeWorkgroupSizeX','maxComputeWorkgroupSizeY','maxComputeWorkgroupSizeZ',
  'maxComputeInvocationsPerWorkgroup','maxComputeWorkgroupsPerDimension',
];

/** Resolve after the requested delay. */
function wait(milliseconds){
  return new Promise(resolve=>setTimeout(resolve,milliseconds));
}
/**
 * Reject a browser GPU operation that does not settle within the given limit.
 *
 * @param {Promise<*>} promise Operation to supervise.
 * @param {number} milliseconds Maximum wait time.
 * @param {string} label Human-readable operation name for timeout errors.
 */
function bounded(promise,milliseconds,label){
  let timer;
  const timeout=new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(new Error(label+' timed out after '+milliseconds+' ms.')),milliseconds);
  });
  return Promise.race([promise,timeout]).finally(()=>clearTimeout(timer));
}
/**
 * Copy adapter metadata before the temporary diagnostic device is destroyed.
 *
 * @param {GPUAdapter} adapter Adapter returned by the browser.
 * @returns {{info: Object, fallback: boolean, features: string[], limits: Object}}
 */
function adapterDetails(adapter){
  const source=adapter.info||{};
  const info={
    vendor:source.vendor||'',
    architecture:source.architecture||'',
    device:source.device||'',
    description:source.description||'',
    type:source.type||'',
  };
  return {
    info,
    fallback:Boolean(source.isFallbackAdapter??adapter.isFallbackAdapter),
    features:[...adapter.features].sort(),
    limits:Object.fromEntries(LIMIT_NAMES.map(name=>[name,adapter.limits[name]])),
  };
}

/**
 * Verify that WebGPU can acquire a device, execute WGSL, and present a frame.
 *
 * Every asynchronous GPU boundary is time-limited so callers always receive a
 * result. The temporary device is destroyed before this function returns.
 *
 * @param {Object} options Probe configuration.
 * @param {Function} options.onStage Receives stage, state, and display note.
 * @param {number} options.timeoutMs Timeout applied to each GPU operation.
 * @returns {Promise<Object>} A serializable pass/fail result and adapter details.
 */
export async function testWebGPU({onStage=()=>{},timeoutMs=8000}={}){
  const pass=(name,note)=>onStage(name,'pass',note);
  const failure=(stage,reason)=>{
    onStage(stage,'fail',stage==='adapter'?'Not found':'Failed');
    return {ok:false,stage,reason};
  };
  if(!window.isSecureContext)return failure('secure','This page is not a secure browser context.');
  pass('secure','Secure context');
  if(!navigator.gpu)return failure('api','This browser does not expose navigator.gpu.');
  pass('api','Available');

  let current='adapter',device=null;
  try{
    let adapter=null;
    for(let attempt=1;attempt<=3&&!adapter;attempt++){
      adapter=await bounded(
        navigator.gpu.requestAdapter({powerPreference:'high-performance'}),
        timeoutMs,
        'GPU adapter request',
      );
      if(!adapter&&attempt<3)await wait(500);
    }
    if(!adapter)return failure('adapter','The browser could not obtain a WebGPU adapter.');
    pass('adapter','Detected');
    const details=adapterDetails(adapter);

    current='device';
    device=await bounded(adapter.requestDevice(),timeoutMs,'GPU device request');
    pass('device','Created');
    let lost=null;
    device.lost.then(value=>{lost='GPU device lost ('+value.reason+'): '+value.message});

    current='compute';
    const input=new Uint32Array([1,2,3,4]);
    const source=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_DST});
    const output=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC});
    const read=device.createBuffer({size:input.byteLength,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
    device.queue.writeBuffer(source,0,input);
    const module=device.createShaderModule({code:'@group(0) @binding(0) var<storage,read> a:array<u32>; @group(0) @binding(1) var<storage,read_write> b:array<u32>; @compute @workgroup_size(4) fn main(@builtin(global_invocation_id) id:vec3<u32>){b[id.x]=a[id.x]*2u+1u;}'});
    const pipeline=await bounded(
      device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'main'}}),
      timeoutMs,
      'Compute pipeline creation',
    );
    const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:source}},{binding:1,resource:{buffer:output}}]});
    let encoder=device.createCommandEncoder(),passEncoder=encoder.beginComputePass();
    passEncoder.setPipeline(pipeline);passEncoder.setBindGroup(0,group);passEncoder.dispatchWorkgroups(1);passEncoder.end();
    encoder.copyBufferToBuffer(output,0,read,0,input.byteLength);device.queue.submit([encoder.finish()]);
    await bounded(read.mapAsync(GPUMapMode.READ),timeoutMs,'Compute result');
    if(lost)throw new Error(lost);
    const values=[...new Uint32Array(read.getMappedRange().slice(0))];
    read.unmap();source.destroy();output.destroy();read.destroy();
    if(values.join(',')!=='3,5,7,9')throw new Error('Compute shader returned '+values.join(', ')+' instead of 3, 5, 7, 9.');
    pass('compute','Passed');

    current='canvas';
    const canvas=document.createElement('canvas');canvas.width=canvas.height=4;
    const context=canvas.getContext('webgpu');
    if(!context)throw new Error('A WebGPU canvas context could not be created.');
    context.configure({device,format:navigator.gpu.getPreferredCanvasFormat(),alphaMode:'opaque'});
    encoder=device.createCommandEncoder();
    passEncoder=encoder.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:{r:.1,g:.2,b:.3,a:1},loadOp:'clear',storeOp:'store'}]});
    passEncoder.end();device.queue.submit([encoder.finish()]);
    await bounded(device.queue.onSubmittedWorkDone(),timeoutMs,'Canvas rendering');
    if(lost)throw new Error(lost);
    pass('canvas','Passed');
    return {ok:true,stage:'canvas',...details};
  }catch(error){
    return failure(current,(error.name||'Error')+': '+(error.message||error));
  }finally{
    if(device)device.destroy();
  }
}
