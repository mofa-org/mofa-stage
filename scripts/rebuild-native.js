#!/usr/bin/env node

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Rebuild native Electron dependencies while keeping caches inside the workspace.

const workspaceRoot = path.resolve(__dirname, '..');
let electronBuilderCli;

try {
  electronBuilderCli = require.resolve('electron-builder/out/cli/cli.js');
} catch (error) {
  console.warn('electron-builder is not available; skipping native rebuild.');
  process.exit(0);
}

const cacheDir = path.join(workspaceRoot, '.cache', 'electron');
const gypCacheDir = path.join(cacheDir, 'gyp');
const isPostinstall = process.env.npm_lifecycle_event === 'postinstall';
const nanHeaderPath = path.join(workspaceRoot, 'node_modules', 'nan', 'nan.h');

const downloadCacheDir = path.join(cacheDir, 'downloads');
const builderCacheDir = path.join(cacheDir, 'builder');

[cacheDir, gypCacheDir, downloadCacheDir, builderCacheDir].forEach((dir) => {
  fs.mkdirSync(dir, { recursive: true });
});

function ensureNanAccessorCompatibility() {
  if (!fs.existsSync(nanHeaderPath)) {
    return;
  }

  let source = fs.readFileSync(nanHeaderPath, 'utf8');

  const templateRegex = /#if defined\(V8_MAJOR_VERSION\) && \(V8_MAJOR_VERSION > 12 [\s\S]+?#endif\n  \);/;
  const templateReplacement = `#if defined(V8_MAJOR_VERSION) && (V8_MAJOR_VERSION > 12 \\\n            || (V8_MAJOR_VERSION == 12 && defined(V8_MINOR_VERSION) \\\n            && V8_MINOR_VERSION >= 5))\n  tpl->SetNativeDataProperty(\n      name\n    , getter_\n    , setter_\n    , obj\n    , attribute\n  );\n#elif defined(V8_MAJOR_VERSION) && V8_MAJOR_VERSION >= 12\n  tpl->SetAccessor(\n      v8::Local<v8::Name>(name)\n    , getter_\n    , setter_\n    , obj\n    , settings\n    , attribute\n  );\n#else\n  tpl->SetAccessor(\n      name\n    , getter_\n    , setter_\n    , obj\n    , settings\n    , attribute\n#if (NODE_MODULE_VERSION < NODE_16_0_MODULE_VERSION)\n    , signature\n#endif\n  );\n#endif`;

  const objectRegex = /#if defined\(V8_MAJOR_VERSION\) &&[\s\S]+?attribute\)\.FromMaybe\(false\);\n#else\n  return obj->SetAccessor\([\s\S]+?attribute\)\.FromMaybe\(false\);\n#endif/;
  const objectReplacement = `#if defined(V8_MAJOR_VERSION) &&                                               \\\n    (V8_MAJOR_VERSION > 12 ||                                                  \\\n     (V8_MAJOR_VERSION == 12 && defined(V8_MINOR_VERSION) &&                   \\\n      V8_MINOR_VERSION >= 5))\n  return obj->SetNativeDataProperty(\n      GetCurrentContext()\n    , name\n    , getter_\n    , setter_\n    , dataobj\n    , attribute).FromMaybe(false);\n#elif defined(V8_MAJOR_VERSION) && V8_MAJOR_VERSION >= 12\n  return obj->SetAccessor(\n      GetCurrentContext()\n    , v8::Local<v8::Name>(name)\n    , getter_\n    , setter_\n    , dataobj\n    , settings\n    , attribute).FromMaybe(false);\n#else\n  return obj->SetAccessor(\n      GetCurrentContext()\n    , name\n    , getter_\n    , setter_\n    , dataobj\n    , settings\n    , attribute).FromMaybe(false);\n#endif`;

  const alreadyPatched = source.includes('v8::Local<v8::Name>(name)');
  let patched = false;

  if (!alreadyPatched && templateRegex.test(source)) {
    source = source.replace(templateRegex, templateReplacement);
    patched = true;
  }

  if (!alreadyPatched && objectRegex.test(source)) {
    source = source.replace(objectRegex, objectReplacement);
    patched = true;
  }

  if (patched) {
    fs.writeFileSync(nanHeaderPath, source);
    console.log('Applied nan accessor compatibility patch.');
  }
}

ensureNanAccessorCompatibility();

if (process.env.SKIP_ELECTRON_REBUILD === '1') {
  console.log('Skipping native rebuild because SKIP_ELECTRON_REBUILD=1.');
  process.exit(0);
}

const env = {
  ...process.env,
  ELECTRON_CACHE: downloadCacheDir,
  ELECTRON_BUILDER_CACHE: builderCacheDir,
  ELECTRON_GYP_CACHE: gypCacheDir
};

const result = spawnSync(process.execPath, [electronBuilderCli, 'install-app-deps'], {
  cwd: workspaceRoot,
  stdio: 'inherit',
  env
});

if (result.error) {
  console.error('Failed to spawn electron-builder:', result.error.message);
  if (isPostinstall) {
    console.error('Continuing without native rebuild; run "npm run rebuild:native" manually after installing build tools.');
    process.exit(0);
  }
  process.exit(result.status ?? 1);
}

if (result.status !== 0) {
  if (isPostinstall) {
    console.error('electron-builder install-app-deps exited with code', result.status);
    console.error('Local terminal features may be unavailable until you run "npm run rebuild:native" manually.');
    process.exit(0);
  }
  process.exit(result.status);
}
