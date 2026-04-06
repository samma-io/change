/**
 * differ.js
 * Compares two page snapshots (baseline vs current) and returns an array of findings.
 */

/**
 * @param {object} baseline - Snapshot produced by extractor.js
 * @param {object} current  - Snapshot produced by extractor.js
 * @returns {Array<{category: string, change_type: string, old_value: any, new_value: any}>}
 */
export function compare(baseline, current) {
  const findings = [];

  try {
    compareScripts(baseline?.scripts ?? [], current?.scripts ?? [], findings);
    compareStringSet('links', baseline?.links ?? [], current?.links ?? [], findings);
    compareForms(baseline?.forms ?? [], current?.forms ?? [], findings);
    compareStringSet('iframes', baseline?.iframes ?? [], current?.iframes ?? [], findings);
    compareHeaders(baseline?.headers ?? {}, current?.headers ?? {}, findings);
    compareCookies(baseline?.cookies ?? [], current?.cookies ?? [], findings);
    compareStringSet('resources', baseline?.resources ?? [], current?.resources ?? [], findings);
  } catch (_err) {
    // Never throw — return whatever we have so far
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Scripts: identify external by src, inline by hash
// ---------------------------------------------------------------------------
function compareScripts(baseScripts, currScripts, findings) {
  const baseExternalBySrc = new Map();
  const baseInlineByHash = new Set();

  for (const s of baseScripts) {
    if (s.type === 'external') {
      baseExternalBySrc.set(s.src, s);
    } else {
      baseInlineByHash.add(s.hash);
    }
  }

  const currExternalBySrc = new Map();
  const currInlineByHash = new Set();

  for (const s of currScripts) {
    if (s.type === 'external') {
      currExternalBySrc.set(s.src, s);
    } else {
      currInlineByHash.add(s.hash);
    }
  }

  // External scripts removed
  for (const [src, script] of baseExternalBySrc) {
    if (!currExternalBySrc.has(src)) {
      findings.push({ category: 'scripts', change_type: 'removed', old_value: script, new_value: null });
    }
  }

  // External scripts added
  for (const [src, script] of currExternalBySrc) {
    if (!baseExternalBySrc.has(src)) {
      findings.push({ category: 'scripts', change_type: 'added', old_value: null, new_value: script });
    }
  }

  // Inline scripts removed
  for (const hash of baseInlineByHash) {
    if (!currInlineByHash.has(hash)) {
      findings.push({ category: 'scripts', change_type: 'removed', old_value: { type: 'inline', hash }, new_value: null });
    }
  }

  // Inline scripts added
  for (const hash of currInlineByHash) {
    if (!baseInlineByHash.has(hash)) {
      findings.push({ category: 'scripts', change_type: 'added', old_value: null, new_value: { type: 'inline', hash } });
    }
  }
}

// ---------------------------------------------------------------------------
// Simple string-set categories: links, iframes, resources
// ---------------------------------------------------------------------------
function compareStringSet(category, baseArr, currArr, findings) {
  const baseSet = new Set(baseArr);
  const currSet = new Set(currArr);

  for (const item of baseSet) {
    if (!currSet.has(item)) {
      findings.push({ category, change_type: 'removed', old_value: item, new_value: null });
    }
  }

  for (const item of currSet) {
    if (!baseSet.has(item)) {
      findings.push({ category, change_type: 'added', old_value: null, new_value: item });
    }
  }
}

// ---------------------------------------------------------------------------
// Forms: compare by index
// ---------------------------------------------------------------------------
function compareFormObjects(a, b) {
  return a.action === b.action && a.method === b.method && a.enctype === b.enctype;
}

function compareForms(baseForms, currForms, findings) {
  const maxLen = Math.max(baseForms.length, currForms.length);

  for (let i = 0; i < maxLen; i++) {
    const baseForm = baseForms[i] ?? null;
    const currForm = currForms[i] ?? null;

    if (baseForm === null) {
      // Extra form in current = added
      findings.push({ category: 'forms', change_type: 'added', old_value: null, new_value: currForm });
    } else if (currForm === null) {
      // Form missing from current = removed
      findings.push({ category: 'forms', change_type: 'removed', old_value: baseForm, new_value: null });
    } else if (!compareFormObjects(baseForm, currForm)) {
      // Same index, different values = modified
      findings.push({ category: 'forms', change_type: 'modified', old_value: baseForm, new_value: currForm });
    }
  }
}

// ---------------------------------------------------------------------------
// Headers: plain object key → value
// ---------------------------------------------------------------------------
function compareHeaders(baseHeaders, currHeaders, findings) {
  const baseKeys = new Set(Object.keys(baseHeaders));
  const currKeys = new Set(Object.keys(currHeaders));

  for (const key of baseKeys) {
    if (!currKeys.has(key)) {
      findings.push({ category: 'headers', change_type: 'removed', old_value: baseHeaders[key], new_value: null });
    } else if (baseHeaders[key] !== currHeaders[key]) {
      findings.push({ category: 'headers', change_type: 'modified', old_value: baseHeaders[key], new_value: currHeaders[key] });
    }
  }

  for (const key of currKeys) {
    if (!baseKeys.has(key)) {
      findings.push({ category: 'headers', change_type: 'added', old_value: null, new_value: currHeaders[key] });
    }
  }
}

// ---------------------------------------------------------------------------
// Cookies: array of { name, httpOnly, secure, sameSite }, identified by name
// ---------------------------------------------------------------------------
function compareCookieObjects(a, b) {
  return a.httpOnly === b.httpOnly && a.secure === b.secure && a.sameSite === b.sameSite;
}

function compareCookies(baseCookies, currCookies, findings) {
  const baseByName = new Map(baseCookies.map((c) => [c.name, c]));
  const currByName = new Map(currCookies.map((c) => [c.name, c]));

  for (const [name, cookie] of baseByName) {
    if (!currByName.has(name)) {
      findings.push({ category: 'cookies', change_type: 'removed', old_value: cookie, new_value: null });
    } else if (!compareCookieObjects(cookie, currByName.get(name))) {
      findings.push({ category: 'cookies', change_type: 'modified', old_value: cookie, new_value: currByName.get(name) });
    }
  }

  for (const [name, cookie] of currByName) {
    if (!baseByName.has(name)) {
      findings.push({ category: 'cookies', change_type: 'added', old_value: null, new_value: cookie });
    }
  }
}
