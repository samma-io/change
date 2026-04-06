import { createHash } from 'node:crypto';

export async function extract(page, response) {
  const result = {
    scripts: [],
    links: [],
    forms: [],
    iframes: [],
    headers: {},
    cookies: [],
    resources: [],
  };

  // scripts
  try {
    const rawScripts = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('script')).map((el) => {
        if (el.src) {
          return { type: 'external', src: el.src };
        } else {
          return { type: 'inline', content: el.textContent || '' };
        }
      });
    });

    result.scripts = rawScripts
      .filter((s) => s.type === 'external' || s.content.trim() !== '')
      .map((s) => {
        if (s.type === 'external') {
          return { type: 'external', src: s.src };
        }
        const hash = createHash('sha256').update(s.content).digest('hex');
        return { type: 'inline', hash };
      });
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract scripts: ${err.message}\n`);
    result.scripts = [];
  }

  // links
  try {
    result.links = await page.evaluate(() => {
      const hrefs = Array.from(document.querySelectorAll('a[href]')).map((el) => el.href);
      const seen = new Set();
      return hrefs.filter((href) => {
        if (!href || href === '' || href === '#') return false;
        if (href.startsWith('javascript:')) return false;
        if (seen.has(href)) return false;
        seen.add(href);
        return true;
      });
    });
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract links: ${err.message}\n`);
    result.links = [];
  }

  // forms
  try {
    result.forms = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('form')).map((el) => ({
        action: el.action,
        method: el.method.toUpperCase(),
        enctype: el.enctype,
      }));
    });
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract forms: ${err.message}\n`);
    result.forms = [];
  }

  // iframes
  try {
    result.iframes = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('iframe'))
        .map((el) => el.src)
        .filter((src) => src && src !== '');
    });
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract iframes: ${err.message}\n`);
    result.iframes = [];
  }

  // headers
  try {
    if (response !== null) {
      result.headers = response.headers();
    }
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract headers: ${err.message}\n`);
    result.headers = {};
  }

  // cookies
  try {
    const hostname = new URL(page.url()).hostname;
    const allCookies = await page.context().cookies();
    result.cookies = allCookies
      .filter((c) => c.domain && (c.domain === hostname || c.domain === `.${hostname}` || hostname.endsWith(c.domain.replace(/^\./, ''))))
      .map(({ name, httpOnly, secure, sameSite }) => ({ name, httpOnly, secure, sameSite }));
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract cookies: ${err.message}\n`);
    result.cookies = [];
  }

  // resources
  try {
    const rawResources = await page.evaluate(() => {
      const urls = [];

      // <link rel="stylesheet"> and <link rel="preload">
      for (const el of document.querySelectorAll('link[rel]')) {
        const rel = el.rel || '';
        if (rel.includes('stylesheet') || rel.includes('preload')) {
          if (el.href) urls.push(el.href);
        }
      }

      // <img src>
      for (const el of document.querySelectorAll('img[src]')) {
        if (el.src) urls.push(el.src);
      }

      return urls;
    });

    const seen = new Set();
    result.resources = rawResources.filter((url) => {
      if (!url.startsWith('http://') && !url.startsWith('https://')) return false;
      if (seen.has(url)) return false;
      seen.add(url);
      return true;
    });
  } catch (err) {
    process.stderr.write(`[extractor] Warning: failed to extract resources: ${err.message}\n`);
    result.resources = [];
  }

  return result;
}
