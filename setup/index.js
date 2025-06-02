#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');

class SignalsSetup {
  constructor() {
    this.projectRoot = process.cwd();
    this.packageJsonPath = path.join(this.projectRoot, 'package.json');
    this.packageJson = null;
    this.projectType = null;
  }

  async run() {
    console.log('🚀 Setting up @aludayalu/signals...\n');

    try {
      this.loadPackageJson();
      this.detectProjectType();
      this.installPackage();
      await this.configureProject();
      
      console.log('\n✅ Setup complete!');
      console.log('You can now use Signal from "@aludayalu/signals" in your components.');
      console.log('🔄 Restart your development server to apply the changes.');
    } catch (error) {
      console.error('❌ Setup failed:', error.message);
      process.exit(1);
    }
  }

  loadPackageJson() {
    if (!fs.existsSync(this.packageJsonPath)) {
      throw new Error('package.json not found. Make sure you are in a valid project directory.');
    }

    this.packageJson = JSON.parse(fs.readFileSync(this.packageJsonPath, 'utf8'));
    console.log(`📦 Found project: ${this.packageJson.name}`);
  }

  detectProjectType() {
    const deps = { ...this.packageJson.dependencies, ...this.packageJson.devDependencies };

    if (deps.next) {
      this.projectType = 'nextjs';
    } else if (deps['react-scripts']) {
      this.projectType = 'cra';
    } else if (deps.vite || deps['@vitejs/plugin-react']) {
      this.projectType = 'vite';
    } else if (deps.react) {
      this.projectType = 'react';
    } else {
      throw new Error('Unsupported project type. This tool supports React, Next.js, Vite, and Create React App projects.');
    }

    console.log(`🔍 Detected project type: ${this.projectType.toUpperCase()}`);
  }

  installPackage() {
    console.log('📥 Installing @aludayalu/signals...');
    
    const packageManager = this.detectPackageManager();
    const installCommand = packageManager === 'yarn' 
      ? 'yarn add @aludayalu/signals'
      : 'npm install @aludayalu/signals';

    try {
      execSync(installCommand, { stdio: 'inherit' });
      console.log('✅ Package installed successfully');
    } catch (error) {
      throw new Error(`Failed to install package: ${error.message}`);
    }
  }

  detectPackageManager() {
    if (fs.existsSync(path.join(this.projectRoot, 'yarn.lock'))) {
      return 'yarn';
    }
    return 'npm';
  }

  async configureProject() {
    console.log('⚙️  Configuring babel plugin...');

    switch (this.projectType) {
      case 'nextjs':
        await this.configureNextJs();
        break;
      case 'cra':
        await this.configureCRA();
        break;
      case 'vite':
        this.configureVite();
        break;
      case 'react':
        this.configureReact();
        break;
    }

    console.log('✅ Configuration complete');
  }

  async configureNextJs() {
    // Check if using Turbopack
    const packageJson = this.packageJson;
    const devScript = packageJson.scripts?.dev || '';
    const usingTurbopack = devScript.includes('--turbo');

    if (usingTurbopack) {
      console.log('⚠️  Turbopack detected in dev script.');
      console.log('Turbopack does not support Babel configurations yet.');
      console.log('');
      console.log('Options:');
      console.log('1. Remove --turbo flag from dev script (recommended)');
      console.log('2. Keep Turbopack and wait for Babel support');
      console.log('');
      
      const choice = await this.promptUser('Remove --turbo flag to use Babel? (y/n): ');
      
      if (choice.toLowerCase() === 'y' || choice.toLowerCase() === 'yes') {
        // Remove --turbo flag
        packageJson.scripts.dev = devScript.replace(/\s*--turbo/g, '').trim();
        fs.writeFileSync(this.packageJsonPath, JSON.stringify(packageJson, null, 2));
        console.log('📝 Removed --turbo flag from dev script');
        
        // Continue with babel setup
        this.setupNextJsBabel();
      } else {
        console.log('❌ Cannot proceed with Babel setup while using Turbopack.');
        console.log('Either remove --turbo flag or wait for Turbopack Babel support.');
        process.exit(1);
      }
    } else {
      this.setupNextJsBabel();
    }
  }

  setupNextJsBabel() {
    const babelrcPath = path.join(this.projectRoot, '.babelrc.json');

    if (fs.existsSync(babelrcPath)) {
      console.log('📄 Found existing .babelrc.json');
      this.updateBabelrc(babelrcPath);
    } else {
      console.log('📄 No babel configuration found, creating .babelrc.json');
      this.createBabelrc(babelrcPath);
    }
  }

  async configureCRA() {
    console.log('⚠️  Create React App detected.');
    console.log('');
    console.log('CRA hides babel configuration by default.');
    console.log('To use custom babel plugins, you need to eject from CRA.');
    console.log('');
    console.log('⚠️  WARNING: Ejecting is permanent and cannot be undone!');
    console.log('After ejecting, you will be responsible for maintaining the build configuration.');
    console.log('');
    
    const confirm = await this.promptUser('Eject from Create React App? (yes/no): ');
    
    if (confirm.toLowerCase() === 'yes') {
      console.log('🚀 Ejecting from Create React App...');
      execSync('npm run eject', { stdio: 'inherit' });
      
      // After ejecting, configure babel in package.json
      this.configureBabelInPackageJsonForCRA();
    } else {
      console.log('❌ Setup cancelled. Cannot proceed without ejecting.');
      console.log('');
      console.log('Alternative: Use Vite or a custom React setup for easier babel configuration.');
      process.exit(1);
    }
  }

  ensureBabelPreset() {
    const deps = { ...this.packageJson.dependencies, ...this.packageJson.devDependencies };
    
    if (!deps['@babel/preset-react']) {
      console.log('📥 Installing @babel/preset-react (required for React projects)...');
      const packageManager = this.detectPackageManager();
      const installCommand = packageManager === 'yarn' 
        ? 'yarn add -D @babel/preset-react'
        : 'npm install -D @babel/preset-react';
      
      execSync(installCommand, { stdio: 'inherit' });
      console.log('✅ @babel/preset-react installed');
    }
  }

  configureBabelInPackageJsonForCRA() {
    if (!this.packageJson.babel) {
      this.packageJson.babel = {
        presets: ['react-app'],
        plugins: []
      };
    }

    if (!this.packageJson.babel.plugins) {
      this.packageJson.babel.plugins = [];
    }

    if (!this.packageJson.babel.plugins.includes('@aludayalu/signals/plugin')) {
      this.packageJson.babel.plugins.unshift('@aludayalu/signals/plugin');
      fs.writeFileSync(this.packageJsonPath, JSON.stringify(this.packageJson, null, 2));
      console.log('📝 Added signals plugin to babel configuration in package.json (using react-app preset)');
    } else {
      console.log('✅ Signals plugin already configured in package.json babel config');
    }
  }

  updateBabelInPackageJson() {
    if (!this.packageJson.babel) {
      this.packageJson.babel = {
        presets: ['@babel/preset-react'],
        plugins: []
      };
    }

    if (!this.packageJson.babel.plugins) {
      this.packageJson.babel.plugins = [];
    }

    if (!this.packageJson.babel.plugins.includes('@aludayalu/signals/plugin')) {
      this.packageJson.babel.plugins.unshift('@aludayalu/signals/plugin');
      fs.writeFileSync(this.packageJsonPath, JSON.stringify(this.packageJson, null, 2));
      console.log('📝 Added signals plugin to babel configuration in package.json');
    } else {
      console.log('✅ Signals plugin already configured in package.json babel config');
    }
  }

  configureVite() {
    const viteConfigPath = this.findViteConfig();
    
    if (viteConfigPath) {
      console.log(`📄 Found existing ${path.basename(viteConfigPath)}`);
      this.updateViteConfig(viteConfigPath);
    } else {
      console.log('📄 No Vite configuration found, creating vite.config.js');
      this.createViteConfig();
    }
  }

  configureReact() {
    const babelrcPath = path.join(this.projectRoot, '.babelrc.json');
    const babelConfigPath = path.join(this.projectRoot, 'babel.config.js');
    const packageJsonBabel = this.packageJson.babel;

    if (fs.existsSync(babelrcPath)) {
      console.log('📄 Found existing .babelrc.json');
      this.updateBabelrc(babelrcPath);
    } else if (fs.existsSync(babelConfigPath)) {
      console.log('📄 Found existing babel.config.js');
      this.updateBabelConfig(babelConfigPath);
    } else if (packageJsonBabel) {
      console.log('📄 Found babel config in package.json');
      this.updateBabelInPackageJson();
    } else {
      console.log('📄 No babel configuration found, creating .babelrc.json');
      this.ensureBabelPreset();
      this.createBabelrc(babelrcPath);
    }
  }

  createBabelrc(filePath) {
    const preset = this.projectType === 'nextjs' ? 'next/babel' : '@babel/preset-react';
    const config = {
      presets: [preset],
      plugins: ['@aludayalu/signals/plugin']
    };

    fs.writeFileSync(filePath, JSON.stringify(config, null, 2));
    console.log(`📝 Created ${path.basename(filePath)} with ${preset} preset`);
  }

  updateBabelrc(filePath) {
    const config = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    if (!config.plugins) {
      config.plugins = [];
    }

    if (!config.plugins.includes('@aludayalu/signals/plugin')) {
      config.plugins.unshift('@aludayalu/signals/plugin');
      fs.writeFileSync(filePath, JSON.stringify(config, null, 2));
      console.log(`📝 Added signals plugin to ${path.basename(filePath)}`);
    } else {
      console.log(`✅ Signals plugin already configured in ${path.basename(filePath)}`);
    }
  }

  updateBabelConfig(filePath) {
    let content = fs.readFileSync(filePath, 'utf8');
    
    if (!content.includes('@aludayalu/signals/plugin')) {
      content = content.replace(
        /plugins:\s*\[/,
        'plugins: [\n    "@aludayalu/signals/plugin",'
      );
      fs.writeFileSync(filePath, content);
      console.log(`📝 Added signals plugin to ${path.basename(filePath)}`);
    } else {
      console.log(`✅ Signals plugin already configured in ${path.basename(filePath)}`);
    }
  }

  findViteConfig() {
    const possibleConfigs = [
      'vite.config.js',
      'vite.config.ts',
      'vite.config.mjs'
    ];

    for (const config of possibleConfigs) {
      const configPath = path.join(this.projectRoot, config);
      if (fs.existsSync(configPath)) {
        return configPath;
      }
    }

    return null;
  }

  createViteConfig() {
    const config = `import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: ['@aludayalu/signals/plugin']
      }
    })
  ]
})`;

    const configPath = path.join(this.projectRoot, 'vite.config.js');
    fs.writeFileSync(configPath, config);
    console.log('📝 Created vite.config.js');
  }

  updateViteConfig(configPath) {
    let content = fs.readFileSync(configPath, 'utf8');
    
    if (!content.includes('@aludayalu/signals/plugin')) {
      if (content.includes('react({')) {
        content = content.replace(
          /react\(\{/,
          `react({
      babel: {
        plugins: ['@aludayalu/signals/plugin']
      },`
        );
      } else {
        content = content.replace(
          /react\(\)/,
          `react({
      babel: {
        plugins: ['@aludayalu/signals/plugin']
      }
    })`
        );
      }
      
      fs.writeFileSync(configPath, content);
      console.log(`📝 Added signals plugin to ${path.basename(configPath)}`);
    } else {
      console.log(`✅ Signals plugin already configured in ${path.basename(configPath)}`);
    }
  }

  promptUser(question) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise(resolve => {
      rl.question(question, answer => {
        rl.close();
        resolve(answer);
      });
    });
  }
}

const setup = new SignalsSetup();
setup.run().catch(console.error);