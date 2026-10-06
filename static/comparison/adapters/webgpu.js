/** Explicit quality study: unsupported devices report an error, never mislabel WebGL. */
import {create as createBabylon} from './babylon.js';
export async function create(canvas){
 if(!navigator.gpu || !await window.BABYLON.WebGPUEngine.IsSupportedAsync)throw Error('WebGPU requires a supported browser and HTTPS or localhost. Choose a WebGL baseline on this device.');
 return createBabylon(canvas,{webgpu:true});
}
