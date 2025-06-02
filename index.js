#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

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
      this.configureProject();
      
      console.log('\n✅ Setup complete!');
      console.log('You can now use Signal in your components.');
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

  configureProject() {
    console.log('⚙️  Configuring babel plugin...');

    switch (this.projectType) {
      case 'nextjs':
        this.configureNextJs();
        break;
      case 'cra':
        this.configureCRA();
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

  configureNextJs() {
    const nextConfigPath = path.join(this.projectRoot, 'next.config.js');
    const babelrcPath = path.join(this.projectRoot, '.babelrc.json');

    if (fs.existsSync(babelrcPath)) {
      this.updateBabelrc(babelrcPath);
    } else {
      this.createBabelrc(babelrcPath);
    }
  }

  configureCRA() {
    const cracoConfigPath = path.join(this.projectRoot, 'craco.config.js');
    
    if (!fs.existsSync(cracoConfigPath)) {
      console.log('📥 Installing CRACO for CRA babel configuration...');
      const packageManager = this.detectPackageManager();
      const installCommand = packageManager === 'yarn' 
        ? 'yarn add -D @craco/craco'
        : 'npm install -D @craco/craco';
      
      execSync(installCommand, { stdio: 'inherit' });
      
      this.updatePackageJsonScripts();
    }

    this.createOrUpdateCracoConfig(cracoConfigPath);
  }

  configureVite() {
    const viteConfigPath = this.findViteConfig();
    
    if (viteConfigPath) {
      this.updateViteConfig(viteConfigPath);
    } else {
      this.createViteConfig();
    }
  }

  configureReact() {
    const babelrcPath = path.join(this.projectRoot, '.babelrc.json');
    const babelConfigPath = path.join(this.projectRoot, 'babel.config.js');

    if (fs.existsSync(babelrcPath)) {
      this.updateBabelrc(babelrcPath);
    } else if (fs.existsSync(babelConfigPath)) {
      this.updateBabelConfig(babelConfigPath);
    } else {
      this.createBabelrc(babelrcPath);
    }
  }

  createBabelrc(filePath) {
    const config = {
      presets: this.projectType === 'nextjs' ? ['next/babel'] : ['@babel/preset-react'],
      plugins: ['@aludayalu/signals/plugin']
    };

    fs.writeFileSync(filePath, JSON.stringify(config, null, 2));
    console.log(`📝 Created ${path.basename(filePath)}`);
  }

  updateBabelrc(filePath) {
    const config = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    
    if (!config.plugins) {
      config.plugins = [];
    }

    if (!config.plugins.includes('@aludayalu/signals/plugin')) {
      config.plugins.unshift('@aludayalu/signals/plugin');
      fs.writeFileSync(filePath, JSON.stringify(config, null, 2));
      console.log(`📝 Updated ${path.basename(filePath)}`);
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
      console.log(`📝 Updated ${path.basename(filePath)}`);
    }
  }

  createOrUpdateCracoConfig(filePath) {
    const config = `module.exports = {
  babel: {
    plugins: ['@aludayalu/signals/plugin']
  }
};`;

    if (!fs.existsSync(filePath)) {
      fs.writeFileSync(filePath, config);
      console.log('📝 Created craco.config.js');
    } else {
      console.log('📝 CRACO config exists. Please manually add "@aludayalu/signals/plugin" to babel.plugins array.');
    }
  }

  updatePackageJsonScripts() {
    this.packageJson.scripts = {
      ...this.packageJson.scripts,
      start: 'craco start',
      build: 'craco build',
      test: 'craco test'
    };

    fs.writeFileSync(this.packageJsonPath, JSON.stringify(this.packageJson, null, 2));
    console.log('📝 Updated package.json scripts for CRACO');
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
      console.log(`📝 Updated ${path.basename(configPath)}`);
    }
  }
}

const setup = new SignalsSetup();
setup.run().catch(console.error);