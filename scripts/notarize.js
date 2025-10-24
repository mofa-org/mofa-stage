/**
 * Notarization script for macOS builds
 * This script runs after signing to submit the app to Apple for notarization
 *
 * Required environment variables:
 * - APPLE_ID: Your Apple ID email
 * - APPLE_APP_SPECIFIC_PASSWORD: App-specific password from appleid.apple.com
 * - APPLE_TEAM_ID: Your Apple Developer Team ID (10-character string)
 *
 * To skip notarization (for testing), set SKIP_NOTARIZE=true
 */

// Load environment variables from .env file
require('dotenv').config();

const { notarize } = require('@electron/notarize');
const path = require('path');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;

  // Only notarize on macOS
  if (electronPlatformName !== 'darwin') {
    console.log('Skipping notarization (not macOS)');
    return;
  }

  // Skip notarization if flag is set
  if (process.env.SKIP_NOTARIZE === 'true') {
    console.log('⚠️  Skipping notarization (SKIP_NOTARIZE=true)');
    console.log('   The app will be signed but not notarized.');
    return;
  }

  // Check required environment variables
  const appleId = process.env.APPLE_ID;
  const applePassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  if (!appleId || !applePassword || !teamId) {
    console.error('❌ Missing required environment variables for notarization:');
    if (!appleId) console.error('   - APPLE_ID');
    if (!applePassword) console.error('   - APPLE_APP_SPECIFIC_PASSWORD');
    if (!teamId) console.error('   - APPLE_TEAM_ID');
    console.error('\n   Set SKIP_NOTARIZE=true to skip notarization (not recommended for production)');
    throw new Error('Notarization failed: missing credentials');
  }

  const appId = 'com.mofa.stage.desktop';
  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);

  console.log('\n🔐 Starting notarization process...');
  console.log(`   App ID: ${appId}`);
  console.log(`   App Path: ${appPath}`);
  console.log(`   Apple ID: ${appleId}`);
  console.log(`   Team ID: ${teamId}`);

  try {
    await notarize({
      appPath,
      appleId,
      appleIdPassword: applePassword,
      teamId,
    });
    console.log('✅ Notarization successful!');
    console.log('   Your app is now signed and notarized by Apple.');
  } catch (error) {
    console.error('❌ Notarization failed:', error.message);
    console.error('\n   Common issues:');
    console.error('   - Invalid Apple ID or password');
    console.error('   - Network connection problems');
    console.error('   - App has code signing issues');
    console.error('\n   You can set SKIP_NOTARIZE=true to build without notarization.');
    throw error;
  }
};
