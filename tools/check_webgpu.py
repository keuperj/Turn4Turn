#!/usr/bin/env python3
"""Check whether a Chromium browser can run WebGPU on the local GPU."""

import argparse
import json
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


CHECK = r"""
async () => {
  const report = {
    secureContext: window.isSecureContext,
    apiAvailable: Boolean(navigator.gpu),
    adapterAvailable: false,
    deviceAvailable: false,
    hardwareAdapter: false,
    computePassed: false,
    canvasPassed: false,
  };
  if (!report.secureContext) {
    report.error = 'WebGPU requires a secure context (HTTPS or localhost).';
    return report;
  }
  if (!navigator.gpu) {
    report.error = 'navigator.gpu is unavailable in this browser.';
    return report;
  }

  try {
    let adapter = null;
    for (let attempt = 1; attempt <= 3 && !adapter; attempt++) {
      adapter = await navigator.gpu.requestAdapter({powerPreference: 'high-performance'});
      report.adapterAttempts = attempt;
      if (!adapter) await new Promise(resolve => setTimeout(resolve, 500));
    }
    if (!adapter) {
      report.error = 'The browser could not obtain a WebGPU adapter after 3 attempts.';
      return report;
    }
    report.adapterAvailable = true;
    const info = adapter.info || {};
    report.adapter = {
      vendor: info.vendor || 'unknown',
      architecture: info.architecture || 'unknown',
      device: info.device || 'unknown',
      description: info.description || 'unknown',
    };
    report.fallbackAdapter = Boolean(info.isFallbackAdapter ?? adapter.isFallbackAdapter);
    report.hardwareAdapter = !report.fallbackAdapter;
    report.features = [...adapter.features].sort();
    report.limits = {
      maxTextureDimension2D: adapter.limits.maxTextureDimension2D,
      maxBufferSize: adapter.limits.maxBufferSize,
      maxStorageBufferBindingSize: adapter.limits.maxStorageBufferBindingSize,
      maxComputeWorkgroupsPerDimension: adapter.limits.maxComputeWorkgroupsPerDimension,
    };

    const device = await adapter.requestDevice();
    report.deviceAvailable = true;
    let lost = null;
    device.lost.then(info => { lost = `${info.reason}: ${info.message}`; });

    const input = new Uint32Array([1, 2, 3, 4]);
    const inputBuffer = device.createBuffer({
      size: input.byteLength,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST,
    });
    const outputBuffer = device.createBuffer({
      size: input.byteLength,
      usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC,
    });
    const readBuffer = device.createBuffer({
      size: input.byteLength,
      usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ,
    });
    device.queue.writeBuffer(inputBuffer, 0, input);
    const module = device.createShaderModule({code: `
      @group(0) @binding(0) var<storage, read> inputData: array<u32>;
      @group(0) @binding(1) var<storage, read_write> outputData: array<u32>;
      @compute @workgroup_size(4)
      fn main(@builtin(global_invocation_id) id: vec3<u32>) {
        outputData[id.x] = inputData[id.x] * 2u + 1u;
      }
    `});
    const pipeline = device.createComputePipeline({
      layout: 'auto',
      compute: {module, entryPoint: 'main'},
    });
    const bindGroup = device.createBindGroup({
      layout: pipeline.getBindGroupLayout(0),
      entries: [
        {binding: 0, resource: {buffer: inputBuffer}},
        {binding: 1, resource: {buffer: outputBuffer}},
      ],
    });
    const computeEncoder = device.createCommandEncoder();
    const pass = computeEncoder.beginComputePass();
    pass.setPipeline(pipeline);
    pass.setBindGroup(0, bindGroup);
    pass.dispatchWorkgroups(1);
    pass.end();
    computeEncoder.copyBufferToBuffer(outputBuffer, 0, readBuffer, 0, input.byteLength);
    device.queue.submit([computeEncoder.finish()]);
    await readBuffer.mapAsync(GPUMapMode.READ);
    report.computeResult = [...new Uint32Array(readBuffer.getMappedRange().slice(0))];
    report.computePassed = report.computeResult.join(',') === '3,5,7,9';
    readBuffer.unmap();

    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 4;
    const context = canvas.getContext('webgpu');
    if (!context) throw new Error('Could not create a WebGPU canvas context.');
    report.canvasFormat = navigator.gpu.getPreferredCanvasFormat();
    context.configure({device, format: report.canvasFormat, alphaMode: 'opaque'});
    const renderEncoder = device.createCommandEncoder();
    const renderPass = renderEncoder.beginRenderPass({colorAttachments: [{
      view: context.getCurrentTexture().createView(),
      clearValue: {r: 0.1, g: 0.2, b: 0.3, a: 1},
      loadOp: 'clear',
      storeOp: 'store',
    }]});
    renderPass.end();
    device.queue.submit([renderEncoder.finish()]);
    await device.queue.onSubmittedWorkDone();
    report.canvasPassed = true;
    if (lost) throw new Error(`WebGPU device was lost (${lost})`);
    report.works = report.computePassed && report.canvasPassed;
    device.destroy();
  } catch (error) {
    report.error = `${error.name || 'Error'}: ${error.message || error}`;
    report.works = false;
  }
  return report;
}
"""


class PageHandler(BaseHTTPRequestHandler):
    """Serve the secure-context test document without external dependencies."""

    def do_GET(self):
        """Return the minimal page in which Playwright evaluates WebGPU."""
        body = b'<!doctype html><meta charset="utf-8"><title>WebGPU check</title>'
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        """Suppress HTTP access logging during the command-line probe."""
        pass


def browser_path(requested):
    """Return an explicit browser path or locate a supported Chromium binary."""
    if requested:
        return requested
    for candidate in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable'):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def main():
    """Run the browser probe, print its report, and return a shell status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', help='path to Chromium/Chrome (auto-detected by default)')
    parser.add_argument('--headed', action='store_true', help='show the browser window during the check')
    parser.add_argument('--json', action='store_true', help='print only the machine-readable report')
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.error('Playwright is required: python3 -m pip install playwright')

    path = browser_path(args.browser)
    httpd = HTTPServer(('127.0.0.1', 0), PageHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            launch = {
                'headless': not args.headed,
                'args': [
                    '--no-sandbox',
                    '--use-angle=vulkan',
                    '--enable-features=Vulkan',
                    '--disable-vulkan-surface',
                    '--enable-unsafe-webgpu',
                ],
            }
            if path:
                launch['executable_path'] = path
            else:
                # Playwright otherwise selects the reduced headless shell, which
                # does not expose the host GPU reliably. This selects Chromium's
                # full "new headless" implementation.
                launch['channel'] = 'chromium'
            browser = playwright.chromium.launch(**launch)
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{httpd.server_port}')
            report = page.evaluate(CHECK)
            report['browser'] = browser.version
            report['browserExecutable'] = path or 'Playwright-managed Chromium'
            browser.close()
    except Exception as error:
        report = {'works': False, 'error': f'{type(error).__name__}: {error}', 'browserExecutable': path}
    finally:
        httpd.shutdown()
        httpd.server_close()

    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        status = 'PASS' if report.get('works') else 'FAIL'
        print(f'{status}: WebGPU runtime check')
        print(f"Browser: {report.get('browser', 'unknown')} ({report.get('browserExecutable') or 'not found'})")
        if report.get('adapterAvailable'):
            adapter = report.get('adapter', {})
            kind = 'software/fallback' if report.get('fallbackAdapter') else 'hardware'
            name = adapter.get('description') if adapter.get('description') != 'unknown' else adapter.get('device')
            print(f"Adapter: {name or 'unknown'} [{kind}], vendor={adapter.get('vendor', 'unknown')}")
        print(f"GPU adapter: {'yes' if report.get('adapterAvailable') else 'no'}")
        print(f"Hardware adapter: {'yes' if report.get('hardwareAdapter') else 'no'}")
        print(f"API: {'yes' if report.get('apiAvailable') else 'no'}")
        print(f"Device: {'yes' if report.get('deviceAvailable') else 'no'}")
        print(f"Compute shader: {'pass' if report.get('computePassed') else 'fail'}")
        print(f"Canvas render: {'pass' if report.get('canvasPassed') else 'fail'}")
        if report.get('error'):
            print(f"Reason: {report['error']}")
    return 0 if report.get('works') else 1


if __name__ == '__main__':
    sys.exit(main())
