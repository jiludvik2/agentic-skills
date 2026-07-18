#!/usr/bin/env node
'use strict';
/*
 * merge-settings.js — idempotently add / replace / remove the gsd-standards-guard
 * PreToolUse hook entry in a Claude Code settings.json, preserving every other
 * entry (GSD's own hooks, user hooks). Mirrors GSD's own merge discipline.
 *
 *   node merge-settings.js <settings.json> <command> [--matcher M] [--remove]
 *
 * Identity: our entry is the PreToolUse block whose command contains the marker
 * substring "gsd-standards-guard.js". Add-or-replace removes any existing such
 * block first, then appends a fresh one. --remove strips it and leaves the rest.
 */

const fs = require('fs');

const MARKER = 'gsd-standards-guard.js';

function main() {
  const [settingsPath, command] = process.argv.slice(2);
  const remove = process.argv.includes('--remove');
  const mIdx = process.argv.indexOf('--matcher');
  const matcher = mIdx !== -1 ? process.argv[mIdx + 1] : 'Read|Grep|Glob|Edit|Write';

  if (!settingsPath) {
    console.error('usage: merge-settings.js <settings.json> <command> [--matcher M] [--remove]');
    process.exit(2);
  }

  let settings = {};
  if (fs.existsSync(settingsPath)) {
    const raw = fs.readFileSync(settingsPath, 'utf8').trim();
    if (raw !== '') {
      try {
        settings = JSON.parse(raw);
      } catch (e) {
        console.error(`merge-settings: ${settingsPath} is not valid JSON — refusing to touch it (${e.message})`);
        process.exit(1);
      }
    }
  }

  if (typeof settings !== 'object' || settings === null || Array.isArray(settings)) {
    console.error('merge-settings: settings.json top level is not an object — refusing to touch it');
    process.exit(1);
  }

  settings.hooks = settings.hooks || {};
  const list = Array.isArray(settings.hooks.PreToolUse) ? settings.hooks.PreToolUse : [];

  // Drop any prior gsd-standards-guard entry (keyed by the marker in the command).
  const kept = list.filter((entry) => {
    const hooks = (entry && Array.isArray(entry.hooks)) ? entry.hooks : [];
    return !hooks.some((h) => h && typeof h.command === 'string' && h.command.includes(MARKER));
  });

  if (!remove) {
    if (!command) {
      console.error('merge-settings: a command is required to install');
      process.exit(2);
    }
    kept.push({
      matcher,
      hooks: [{ type: 'command', command }],
    });
  }

  if (kept.length > 0) {
    settings.hooks.PreToolUse = kept;
  } else {
    delete settings.hooks.PreToolUse;
    if (Object.keys(settings.hooks).length === 0) delete settings.hooks;
  }

  fs.mkdirSync(require('path').dirname(settingsPath), { recursive: true });
  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2) + '\n');
  console.log(`merge-settings: ${remove ? 'removed' : 'installed'} PreToolUse entry in ${settingsPath}`);
}

main();
