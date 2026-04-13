/**
 * extract-x-dms.js — Extract a full X/Twitter DM conversation from the browser.
 *
 * STATUS: BROKEN — Does not scroll back to bottom after extraction.
 *   The conversation is left stuck at the top. Needs fixing before use.
 *
 * Usage:
 *   1. Open x.com → navigate to the DM conversation
 *   2. Open DevTools console (Cmd+Opt+I)
 *   3. Paste this entire script → Enter
 *   4. Wait for scrolling to complete (progress logged)
 *   5. Transcript is in your clipboard
 *   6. Paste into memory/sources/x-dms/<date>-<creator>.md
 *
 * Set DRY_RUN = true below to only probe selectors and show sample messages.
 */

(async () => {
  // ── Configuration ──────────────────────────────────────────────────
  const DRY_RUN = false;
  const MAX_SCROLL_ITERATIONS = 500;
  const NO_NEW_MESSAGES_LIMIT = 5;
  const SCROLL_DELAY_MS = 600;
  const BATCH_LOG_INTERVAL = 10;

  // ── Helpers ────────────────────────────────────────────────────────
  const log = (msg) => console.log(`%c[DM Extract] ${msg}`, 'color: #1DA1F2; font-weight: bold');
  const warn = (msg) => console.warn(`[DM Extract] ${msg}`);

  function queryFirst(selectors, root = document) {
    for (const sel of selectors) {
      try {
        const el = root.querySelector(sel);
        if (el) return { el, selector: sel };
      } catch (_) { /* invalid selector, skip */ }
    }
    return null;
  }

  function queryAll(selectors, root = document) {
    for (const sel of selectors) {
      try {
        const els = root.querySelectorAll(sel);
        if (els.length > 0) return { els: Array.from(els), selector: sel };
      } catch (_) { /* skip */ }
    }
    return { els: [], selector: null };
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return hash;
  }

  // ── Phase 1: Discovery ─────────────────────────────────────────────
  log('Phase 1: Discovering DOM structure...');

  // --- 1a. Find scroller container ---
  // Strategy: try known selectors first, then probe ALL elements for one
  // that is scrollable (overflow-y scroll/auto) with significant scrollHeight,
  // positioned within the DM conversation area (right side of screen).
  const SCROLLER_SELECTORS = [
    '[data-testid="DmScrollerContainer"]',
    '[data-testid="DMConversation"]',
    'div[data-testid="DMConversation"] > div',
    'section[role="region"] div[style*="overflow"]',
  ];

  let scroller = null;
  let scrollerSource = '';

  // Try known selectors first
  const scrollerResult = queryFirst(SCROLLER_SELECTORS);
  if (scrollerResult) {
    scroller = scrollerResult.el;
    scrollerSource = `selector: ${scrollerResult.selector}`;
  }

  // Fallback: programmatic scan for scrollable containers
  if (!scroller) {
    log('Known selectors missed — scanning for scrollable containers...');
    const candidates = [];
    // Check all divs and sections for scrollability
    const allEls = document.querySelectorAll('div, section');
    for (const el of allEls) {
      const cs = window.getComputedStyle(el);
      const overflowY = cs.overflowY;
      if (overflowY === 'scroll' || overflowY === 'auto') {
        // Must have scrollable content (scrollHeight > clientHeight or will once loaded)
        // and be reasonably sized (not tiny widgets)
        const rect = el.getBoundingClientRect();
        if (rect.height > 200 && rect.width > 200) {
          candidates.push({
            el,
            scrollHeight: el.scrollHeight,
            clientHeight: el.clientHeight,
            area: rect.height * rect.width,
            rect,
          });
        }
      }
    }

    if (candidates.length > 0) {
      // Heuristic: pick the candidate in the right portion of the screen
      // (DM conversation panel) with the largest scrollable area.
      // On X, the DM list is on the left and the conversation is on the right.
      const screenMid = window.innerWidth / 2;
      const rightCandidates = candidates.filter((c) => c.rect.left >= screenMid - 100);
      const pool = rightCandidates.length > 0 ? rightCandidates : candidates;

      // Among those, prefer the one with the most scroll content
      pool.sort((a, b) => b.scrollHeight - a.scrollHeight);
      scroller = pool[0].el;
      scrollerSource = `programmatic scan (${candidates.length} candidates, picked scrollHeight=${pool[0].scrollHeight})`;
      log(`Found ${candidates.length} scrollable containers, selected best match`);
    }
  }

  if (!scroller) {
    console.error('[DM Extract] Could not find scroller container. Are you on an open DM conversation?');
    console.log('Make sure a DM conversation is open (not just the DM list).');
    return;
  }
  log(`Scroller: ${scrollerSource}`);

  // --- 1b. Find message entries ---
  // Strategy: try known selectors, then look for repeated child structures
  // within the scroller that contain text content.
  const MESSAGE_ENTRY_SELECTORS = [
    '[data-testid="messageEntry"]',
    '[data-testid="message-entry"]',
    'div[data-testid="cellInnerDiv"]',
  ];

  let msgSelector = null;
  let messageEls = [];

  const msgResult = queryAll(MESSAGE_ENTRY_SELECTORS, scroller);
  if (msgResult.els.length > 0) {
    messageEls = msgResult.els;
    msgSelector = msgResult.selector;
  }

  // Fallback: try scroller-global query (entries might not be direct descendants)
  if (messageEls.length === 0) {
    const globalResult = queryAll(MESSAGE_ENTRY_SELECTORS);
    if (globalResult.els.length > 0) {
      messageEls = globalResult.els;
      msgSelector = `${globalResult.selector} (global)`;
    }
  }

  // Fallback: find direct children of the scroller's first child (virtual list container)
  if (messageEls.length === 0) {
    log('Message entry selectors missed — scanning scroller children...');
    // X typically uses a virtual list: scroller > div (container) > div (items)
    // Find the child with the most children (that's the virtual list)
    let bestChild = null;
    let bestCount = 0;
    for (const child of scroller.children) {
      if (child.children.length > bestCount) {
        bestCount = child.children.length;
        bestChild = child;
      }
    }
    // Also check scroller itself
    if (scroller.children.length > bestCount) {
      bestChild = scroller;
      bestCount = scroller.children.length;
    }
    if (bestChild && bestCount >= 2) {
      messageEls = Array.from(bestChild.children);
      msgSelector = `scroller children scan (${bestCount} items)`;
    }
  }

  if (messageEls.length === 0) {
    console.error('[DM Extract] Could not find message entries inside scroller.');
    return;
  }
  log(`Message entries (${messageEls.length}): ${msgSelector}`);

  // Store which selector approach worked so we can reuse during scrolling
  const messageQueryFn = () => {
    // Re-query with whatever worked
    if (msgSelector && !msgSelector.includes('scan')) {
      const baseSel = msgSelector.replace(' (global)', '');
      const root = msgSelector.includes('global') ? document : scroller;
      const els = root.querySelectorAll(baseSel);
      if (els.length > 0) return Array.from(els);
    }
    // Fallback to scroller children scan
    let bestChild = scroller;
    let bestCount = scroller.children.length;
    for (const child of scroller.children) {
      if (child.children.length > bestCount) {
        bestCount = child.children.length;
        bestChild = child;
      }
    }
    return Array.from(bestChild.children);
  };

  // --- 1c. Text, timestamp, and header selectors ---
  const MESSAGE_TEXT_SELECTORS = [
    '[data-testid="tweetText"]',
    '[data-testid="messageText"]',
    'div[dir="auto"][lang]',
    'div[dir="auto"] > span',
  ];

  const TIMESTAMP_SELECTORS = [
    'time[datetime]',
    'span[data-testid="messageTimestamp"]',
  ];

  const HEADER_NAME_SELECTORS = [
    'div[data-testid="DMConversationHeader"] span',
    'div[data-testid="conversation_header"] span',
    'h2[role="heading"] span',
    'div[data-testid="DMHeader"] span',
  ];

  const LOAD_EARLIER_SELECTORS = [
    'div[role="button"][class*="load"]',
    'button[class*="load"]',
    'div[data-testid="loadEarlierMessages"]',
  ];

  // Get conversation partner name from header
  let partnerName = 'Unknown';
  const headerResult = queryFirst(HEADER_NAME_SELECTORS);
  if (headerResult) {
    const text = headerResult.el.textContent.trim();
    if (text && text.length > 0 && text.length < 100) {
      partnerName = text;
    }
  }
  // Fallback: try to get name from the page title or any prominent heading
  if (partnerName === 'Unknown') {
    // X page title is typically "Conversation with Name / X"
    const titleMatch = document.title.match(/(?:with|@)\s*(.+?)(?:\s*\/|\s*[-–]|\s*$)/i);
    if (titleMatch) {
      partnerName = titleMatch[1].trim();
    }
  }
  log(`Conversation partner: ${partnerName}`);

  // ── Sender Detection Heuristic ─────────────────────────────────────
  function detectSender(entryEl) {
    // Method 1: Check background color — your messages have blue bubble
    const allDivs = entryEl.querySelectorAll('div');
    for (const div of allDivs) {
      const bg = window.getComputedStyle(div).backgroundColor;
      if (!bg || bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') continue;
      // Parse rgb values
      const match = bg.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (match) {
        const [, r, g, b] = match.map(Number);
        // Blue-ish (your messages): high blue, lower red/green
        if (b > 180 && r < 80 && g < 180 && b > r && b > g) return 'You';
        // Also check for the specific X brand blue
        if (r === 29 && g === 155 && b === 240) return 'You';
      }
    }

    // Method 2: Positional — your messages are right-aligned
    const rect = entryEl.getBoundingClientRect();
    const scrollerRect = scroller.getBoundingClientRect();
    const entryRight = rect.right;
    const entryLeft = rect.left;
    const scrollerRight = scrollerRect.right;
    const scrollerLeft = scrollerRect.left;
    const scrollerWidth = scrollerRect.width;

    // Check inner bubble position, not the outer cell (which may be full width)
    const innerBubbles = entryEl.querySelectorAll('div[dir="auto"]');
    for (const bubble of innerBubbles) {
      const bRect = bubble.getBoundingClientRect();
      if (bRect.width < 20) continue;
      const bCenter = bRect.left + bRect.width / 2;
      const scrollerCenter = scrollerLeft + scrollerWidth / 2;
      if (bCenter > scrollerCenter + 30) return 'You';
      if (bCenter < scrollerCenter - 30) return partnerName;
    }

    // Method 3: Walk up looking for flex alignment
    let current = entryEl;
    for (let i = 0; i < 8 && current && current !== scroller; i++) {
      const cs = window.getComputedStyle(current);
      if (cs.justifyContent === 'flex-end') return 'You';
      if (cs.justifyContent === 'flex-start') return partnerName;
      if (cs.marginLeft === 'auto' && cs.marginRight !== 'auto') return 'You';
      if (cs.marginRight === 'auto' && cs.marginLeft !== 'auto') return partnerName;
      current = current.parentElement;
    }

    return 'Unknown';
  }

  // ── Message Extraction from a DOM node ─────────────────────────────
  function extractMessage(entryEl) {
    // Get text — try selectors, then fall back to finding the deepest dir="auto" text
    let text = '';
    const textResult = queryFirst(MESSAGE_TEXT_SELECTORS, entryEl);
    if (textResult) {
      text = textResult.el.textContent.trim();
    }
    if (!text) {
      // Fallback: grab all dir="auto" text nodes that aren't tiny UI labels
      const autos = entryEl.querySelectorAll('[dir="auto"]');
      for (const el of autos) {
        const t = el.textContent.trim();
        if (t.length > 0 && t.length < 5000) {
          text = t;
          break;
        }
      }
    }

    // Check for images
    const images = entryEl.querySelectorAll('img[src*="media"], img[src*="pbs.twimg"], img[src*="ton.twimg"]');
    const imageUrls = Array.from(images)
      .map((img) => img.src)
      .filter((src) => !src.includes('emoji') && !src.includes('profile_images') && !src.includes('hashflag'));

    // Check for links
    const links = entryEl.querySelectorAll('a[href]');
    const linkUrls = Array.from(links)
      .map((a) => a.href)
      .filter((href) => href && !href.includes('x.com/messages') && !href.startsWith('javascript'));

    // Get timestamp
    let timestamp = null;
    const timeResult = queryFirst(TIMESTAMP_SELECTORS, entryEl);
    if (timeResult) {
      timestamp = timeResult.el.getAttribute('datetime') || timeResult.el.textContent.trim();
    }

    // If no text and no media, skip (date separator or empty cell)
    if (!text && imageUrls.length === 0 && linkUrls.length === 0) return null;

    // Build content string
    let content = text;
    if (imageUrls.length > 0) {
      content += (content ? ' ' : '') + imageUrls.map((u) => `[image]`).join(' ');
    }
    if (linkUrls.length > 0) {
      const newLinks = linkUrls.filter((l) => !content.includes(l));
      if (newLinks.length > 0) {
        content += (content ? ' ' : '') + newLinks.map((u) => `[link: ${u}]`).join(' ');
      }
    }

    if (!content) return null;

    const sender = detectSender(entryEl);

    return {
      sender,
      text: content,
      timestamp,
      _hash: hashString(content + (timestamp || '')),
    };
  }

  // ── Dry Run Mode ───────────────────────────────────────────────────
  if (DRY_RUN) {
    log('=== DRY RUN MODE ===');
    log(`Scroller: ${scrollerSource}`);
    log(`Message entries: ${msgSelector} (${messageEls.length} visible)`);
    log(`Partner: ${partnerName}`);

    const samples = messageEls.slice(0, 5);
    samples.forEach((el, i) => {
      const msg = extractMessage(el);
      if (msg) {
        console.log(`  Sample ${i + 1}: [${msg.sender}] ${msg.text.slice(0, 100)}${msg.text.length > 100 ? '...' : ''}`);
      } else {
        console.log(`  Sample ${i + 1}: (no extractable content — date separator or empty cell)`);
      }
    });

    log('Dry run complete. Set DRY_RUN = false to extract full conversation.');
    return;
  }

  // ── Phase 2: Auto-Scroll + Incremental Extraction ──────────────────
  log('Phase 2: Scrolling and extracting messages...');

  const seenHashes = new Set();
  const allMessages = [];

  // Track last known timestamp so we can propagate it to messages without one.
  // X only shows timestamps on some messages (e.g. first in a group).
  let lastTimestamp = null;

  function harvestVisible() {
    const els = messageQueryFn();
    let newCount = 0;
    for (const el of els) {
      const msg = extractMessage(el);
      if (!msg) continue;

      // Propagate timestamp from nearby messages
      if (msg.timestamp) {
        lastTimestamp = msg.timestamp;
      } else if (lastTimestamp) {
        msg.timestamp = lastTimestamp;
        // Rehash with the propagated timestamp
        msg._hash = hashString(msg.text + msg.timestamp);
      }

      if (seenHashes.has(msg._hash)) continue;
      seenHashes.add(msg._hash);
      allMessages.push(msg);
      newCount++;
    }
    return newCount;
  }

  // Harvest initial visible messages
  harvestVisible();
  log(`Initial harvest: ${allMessages.length} messages`);

  let noNewCount = 0;
  let iteration = 0;

  while (iteration < MAX_SCROLL_ITERATIONS && noNewCount < NO_NEW_MESSAGES_LIMIT) {
    // Try to click "Load earlier messages" button
    const loadBtn = queryFirst(LOAD_EARLIER_SELECTORS);
    if (loadBtn) {
      loadBtn.el.click();
      await sleep(SCROLL_DELAY_MS);
    }

    // Scroll UP to load older messages
    scroller.scrollTop = 0;
    await sleep(SCROLL_DELAY_MS);

    const newCount = harvestVisible();

    if (newCount === 0) {
      noNewCount++;
    } else {
      noNewCount = 0;
    }

    iteration++;

    if (iteration % BATCH_LOG_INTERVAL === 0) {
      log(`Scroll ${iteration}: ${allMessages.length} total messages (${newCount} new this batch)`);
    }
  }

  // Scroll back to bottom so the conversation is usable again
  scroller.scrollTop = scroller.scrollHeight;

  log(`Scrolling complete after ${iteration} iterations. Total raw messages: ${allMessages.length}`);

  // ── Phase 3: Deduplicate & Sort ────────────────────────────────────
  log('Phase 3: Deduplicating and sorting...');

  const dedupMap = new Map();
  for (const msg of allMessages) {
    const key = `${msg._hash}-${msg.timestamp || ''}`;
    if (!dedupMap.has(key)) {
      dedupMap.set(key, msg);
    }
  }
  const messages = Array.from(dedupMap.values());

  // Sort chronologically
  messages.sort((a, b) => {
    if (!a.timestamp && !b.timestamp) return 0;
    if (!a.timestamp) return -1;
    if (!b.timestamp) return 1;
    const da = new Date(a.timestamp);
    const db = new Date(b.timestamp);
    if (isNaN(da.getTime()) || isNaN(db.getTime())) {
      return (a.timestamp || '').localeCompare(b.timestamp || '');
    }
    return da - db;
  });

  log(`Final message count: ${messages.length}`);

  // ── Phase 4: Output ────────────────────────────────────────────────
  log('Phase 4: Formatting output...');

  const now = new Date().toISOString().slice(0, 10);

  let textOutput = `=== X DM Conversation with ${partnerName} ===\n`;
  textOutput += `Extracted: ${now} | Messages: ${messages.length}\n\n`;

  let currentDate = '';
  for (const msg of messages) {
    let date = '';
    let time = '';

    if (msg.timestamp) {
      const d = new Date(msg.timestamp);
      if (!isNaN(d.getTime())) {
        date = d.toISOString().slice(0, 10);
        time = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
      } else {
        date = msg.timestamp;
      }
    }

    if (date && date !== currentDate) {
      currentDate = date;
      textOutput += `\n--- ${currentDate} ---\n`;
    }

    const timeStr = time ? `[${time}]` : '[??:??]';
    textOutput += `${timeStr} ${msg.sender}: ${msg.text}\n`;
  }

  // Build JSON output
  const jsonOutput = messages.map((m) => ({
    sender: m.sender,
    text: m.text,
    timestamp: m.timestamp,
  }));

  // Store on window for manual access
  window.__dmExtractText = textOutput;
  window.__dmExtractJSON = jsonOutput;

  // Download as .txt file
  function downloadFile(content, filename, mime = 'text/plain') {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const safeName = partnerName.replace(/[^a-zA-Z0-9_-]/g, '-').toLowerCase();
  const filename = `${now}-x-dms-${safeName}.txt`;
  downloadFile(textOutput, filename);
  log(`Downloaded: ${filename}`);

  // Print summary
  console.log('\n' + textOutput.slice(0, 2000) + (textOutput.length > 2000 ? '\n\n... (truncated in console, full text downloaded & window.__dmExtractText)' : ''));
  log(`Done! ${messages.length} messages extracted.`);
  log('Re-download: downloadFile(window.__dmExtractText, "dms.txt")');
  log('JSON: copy(JSON.stringify(window.__dmExtractJSON, null, 2))');
})();
