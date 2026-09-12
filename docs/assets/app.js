(() => {
  'use strict';

  // Per-language strings. A translated page sets window.HERMES_I18N before this
  // script runs (this file is deferred, so an inline script always wins). Every
  // lookup falls back to the English default, so the English pages need nothing.
  const T = (key, fallback) => {
    const table = window.HERMES_I18N;
    const value = table && table[key];
    return typeof value === 'string' && value ? value : fallback;
  };

  const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#${name}"></use></svg>`;
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  // ---------------------------------------------------------------- toast
  const toast = $('#toast');
  let toastTimer;
  function announce(message) {
    if (!toast) return;
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.hidden = false;
    toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
  }

  // ------------------------------------------------------- copy buttons
  // Works on any page with <pre><code> blocks.
  function initCopyButtons() {
    $$('pre .copy').forEach((button) => {
      const pre = button.closest('pre');
      const code = pre.querySelector('code');
      if (!code) return;
      // data-kind is language-independent; data-label is translated for readers.
      const isPrompt = pre.dataset.kind === 'prompt' || pre.dataset.label === 'Discord prompt';
      const label = isPrompt
        ? T('copy.discord', 'Copy Discord prompt')
        : T('copy.terminal', 'Copy terminal command');
      button.type = 'button';
      button.hidden = false;
      button.innerHTML = `${icon('copy')}<span>${T('copy.button', 'Copy')}</span>`;
      button.setAttribute('aria-label', label);
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
          await navigator.clipboard.writeText(code.textContent);
          button.innerHTML = `${icon('check')}<span>${T('copy.done', 'Copied')}</span>`;
          button.dataset.copied = 'true';
          button.setAttribute('aria-label', T('copy.aria', 'Copied to clipboard'));
          announce(T('toast.copied', 'Copied. Paste it when you\u2019re ready.'));
          setTimeout(() => {
            button.innerHTML = `${icon('copy')}<span>${T('copy.button', 'Copy')}</span>`;
            delete button.dataset.copied;
            button.setAttribute('aria-label', label);
            button.disabled = false;
          }, 1600);
        } catch {
          const range = document.createRange();
          range.selectNodeContents(code);
          const selection = window.getSelection();
          selection.removeAllRanges();
          selection.addRange(range);
          button.disabled = false;
          announce(T('toast.manual', 'Automatic copying is unavailable. The text is selected so you can copy it.'));
        }
      });
    });
  }

  // The tab logic from the remote branch lives in initTabs() below, generalised
  // to any [role=tablist] so it survived the .os-tabs -> .tabs rename.

  // -------------------------------------------------------- tab panels
  function initTabs() {
    $$('[role="tablist"]').forEach((host) => {
      const tabs = [...host.querySelectorAll('[role="tab"]')];
      if (!tabs.length) return;
      host.hidden = false;
      function selectTab(tab, moveFocus = false) {
        tabs.forEach((item) => {
          const selected = item === tab;
          item.setAttribute('aria-selected', String(selected));
          item.tabIndex = selected ? 0 : -1;
          const panel = document.getElementById(item.getAttribute('aria-controls'));
          if (panel) panel.hidden = !selected;
        });
        if (moveFocus) tab.focus();
      }
      // The OS switcher preselects the visitor's platform; any other tablist
      // keeps whichever tab the markup already marks as selected.
      const initialOS = /Mac|iPhone|iPad/.test(navigator.platform) ? 'mac'
        : /Linux/.test(navigator.platform) ? 'linux' : 'windows';
      selectTab(host.querySelector(`#tab-${initialOS}`)
        || tabs.find((tab) => tab.getAttribute('aria-selected') === 'true')
        || tabs[0]);
      tabs.forEach((tab, index) => {
        tab.addEventListener('click', () => selectTab(tab));
        tab.addEventListener('keydown', (event) => {
          let target;
          // Arrow direction follows the reading direction of the page.
          const rtl = document.documentElement.dir === 'rtl';
          const forward = rtl ? 'ArrowLeft' : 'ArrowRight';
          const back = rtl ? 'ArrowRight' : 'ArrowLeft';
          if (event.key === forward) target = (index + 1) % tabs.length;
          if (event.key === back) target = (index + tabs.length - 1) % tabs.length;
          if (event.key === 'Home') target = 0;
          if (event.key === 'End') target = tabs.length - 1;
          if (target !== undefined) {
            event.preventDefault();
            selectTab(tabs[target], true);
          }
        });
      });
    });
  }

  // ----------------------------------------------------- setup progress
  function initProgress() {
    const host = $('.setup-progress');
    const completionInputs = $$('[data-complete]');
    if (!host || !completionInputs.length) return;
    const storageKey = 'nft-toolkit-setup-v1';
    const validSteps = completionInputs.map((input) => input.dataset.complete);
    let completed = [];
    let storageAvailable = true;
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
      if (Array.isArray(saved)) completed = [...new Set(saved.filter((id) => validSteps.includes(id)))];
    } catch { storageAvailable = false; }
    const progressHelp = $('#progress-help');
    const progressCount = $('#progress-count');
    const progressMeter = $('#setup-meter');
    function updateProgress() {
      const count = completionInputs.filter((input) => input.checked).length;
      if (progressMeter) progressMeter.value = count;
      if (progressCount) progressCount.textContent = T('progress.count', '{n} of 4').replace('{n}', String(count));
      if (progressHelp) {
        progressHelp.textContent = storageAvailable
          ? T('progress.saved', 'Saved in this browser')
          : T('progress.visit', 'Progress kept for this visit');
      }
    }
    host.hidden = false;
    completionInputs.forEach((input) => {
      const label = input.closest('.completion');
      if (label) label.hidden = false;
      input.checked = completed.includes(input.dataset.complete);
      input.addEventListener('change', () => {
        completed = completionInputs.filter((item) => item.checked).map((item) => item.dataset.complete);
        try { localStorage.setItem(storageKey, JSON.stringify(completed)); }
        catch { storageAvailable = false; }
        updateProgress();
        if (completed.length === 4) announce(T('toast.complete', 'Setup complete. Your next step: send your agent a message.'));
      });
    });
    updateProgress();
  }

  // ------------------------------------------------ skill search + filters
  function initSkillLibrary() {
    const search = $('#skill-search');
    const tools = $('.library-tools');
    const results = $('#skill-results');
    const count = $('#skill-count');
    if (!search || !results || !count) return;
    if (tools) tools.hidden = false;
    const filters = $$('[data-filter]');
    const categories = $$('#skill-results .cat').map((heading) => ({
      heading,
      container: heading.nextElementSibling,
      cards: [...heading.nextElementSibling.querySelectorAll('.skill')]
    }));
    let activeFilter = 'all';
    function filterSkills() {
      const query = search.value.toLocaleLowerCase().trim();
      let total = 0;
      for (const category of categories) {
        let visible = 0;
        for (const card of category.cards) {
          const matchesCategory = activeFilter === 'all' || category.heading.textContent === activeFilter;
          const matchesQuery = `${card.textContent} ${category.heading.textContent}`.toLocaleLowerCase().includes(query);
          card.hidden = !(matchesCategory && matchesQuery);
          if (!card.hidden) visible++;
        }
        category.heading.hidden = visible === 0;
        if (category.container) category.container.hidden = visible === 0;
        total += visible;
      }
      const noun = total === 1 ? T('skills.one', 'skill') : T('skills.many', 'skills');
      // The tail carries its own leading space, because languages that do not use
      // a space before punctuation (Chinese, Japanese) need to supply none.
      const tail = total === 31 ? T('skills.ready', ' to put to work') : T('skills.found', ' found');
      count.textContent = `${total} ${noun}${tail}`;
      const empty = $('#empty-skills');
      if (empty) empty.hidden = total !== 0;
    }
    filters.forEach((button) => {
      button.addEventListener('click', () => {
        activeFilter = button.dataset.filter;
        filters.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
        filterSkills();
      });
    });
    search.addEventListener('input', filterSkills);
    const reset = $('#reset-search');
    if (reset) {
      reset.addEventListener('click', () => {
        search.value = '';
        activeFilter = 'all';
        filters.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.filter === 'all')));
        filterSkills();
        search.focus();
      });
    }
    filterSkills();
  }

  // ------------------------------------------------------- demo messages
  function initDemo() {
    const rows = $('#result-rows');
    const controls = $('.demo-controls');
    if (!rows || !controls) return;
    const rarityRows = rows.innerHTML;
    const demoData = {
      rarity: {
        prompt: T('demo.rarity.prompt', 'rank this collection and show me the rare ones'),
        answer: T('demo.rarity.answer', 'Collection ranked. Here are the three rarest.'),
        title: T('demo.rarity.title', 'Rarity report'),
        subtitle: T('demo.rarity.subtitle', 'Demo collection'),
        rows: rarityRows,
        foot: T('demo.rarity.foot', 'Research only. No transactions sent.')
      },
      mint: {
        prompt: T('demo.mint.prompt', 'check this mint before I connect my wallet'),
        answer: T('demo.mint.answer', 'I\u2019ll check the contract, price, and supply first.'),
        title: T('demo.mint.title', 'Mint research'),
        subtitle: T('demo.mint.subtitle', 'Example checklist'),
        rows: [T('demo.mint.row1', 'Verify the real contract'), T('demo.mint.row2', 'Read the onchain mint price'), T('demo.mint.row3', 'Check remaining supply')]
          .map((text) => `<div class="result-row">${icon('search')}<span>${text}</span><em>${T('demo.mint.tag', 'Check first')}</em></div>`).join(''),
        foot: T('demo.mint.foot', 'Review the findings before approving a mint.')
      },
      wallet: {
        prompt: T('demo.wallet.prompt', 'what has this wallet been buying lately?'),
        answer: T('demo.wallet.answer', 'I\u2019ll turn the wallet\u2019s public activity into a report.'),
        title: T('demo.wallet.title', 'Wallet intelligence'),
        subtitle: T('demo.wallet.subtitle', 'Example report'),
        rows: [T('demo.wallet.row1', 'Recent purchases'), T('demo.wallet.row2', 'Collections held'), T('demo.wallet.row3', 'Sales and transfers')]
          .map((text) => `<div class="result-row">${icon('code')}<span>${text}</span><em>${T('demo.wallet.tag', 'Onchain')}</em></div>`).join(''),
        foot: T('demo.wallet.foot', 'Public wallet data. No private keys needed.')
      }
    };
    controls.hidden = false;
    const demoButtons = $$('[data-demo]');
    demoButtons.forEach((button) => {
      button.addEventListener('click', () => {
        const data = demoData[button.dataset.demo];
        const prompt = $('#demo-prompt');
        const answer = $('#demo-answer');
        const title = $('#result-title');
        const subtitle = $('#result-subtitle');
        const foot = $('#result-foot');
        if (prompt) prompt.innerHTML = `<span class="mention">@hermes</span> ${data.prompt}`;
        if (answer) answer.textContent = data.answer;
        if (title) title.textContent = data.title;
        if (subtitle) subtitle.textContent = data.subtitle;
        rows.innerHTML = data.rows;
        if (foot) foot.textContent = data.foot;
        demoButtons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
      });
    });
  }

  // -------------------------------------------------------- guide sidebar
  function initGuideMenu() {
    const menu = $('#guide-menu');
    if (!menu) return;
    const mobile = window.matchMedia('(max-width: 700px)');
    function updateMenu() { menu.open = !mobile.matches; }
    updateMenu();
    mobile.addEventListener('change', updateMenu);
    const summary = menu.querySelector('summary');
    if (summary) {
      summary.addEventListener('click', (event) => {
        if (!mobile.matches) event.preventDefault();
      });
    }
    $$('.toc a').forEach((link) => {
      link.addEventListener('click', () => { if (mobile.matches) menu.open = false; });
    });
  }

  // ------------------------------------------------------- active chapter
  function initChapterTracking() {
    const chapters = $$('.guide-content section[id]');
    const links = $$('.toc a');
    const backToTop = $('.top');
    if (!chapters.length || !links.length) return;
    let framePending = false;
    function updateChapter() {
      framePending = false;
      let active = chapters[0].id;
      for (const chapter of chapters) {
        if (chapter.getBoundingClientRect().top <= 150) active = chapter.id;
      }
      links.forEach((link) => {
        if (link.hash === `#${active}`) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
      if (backToTop) backToTop.hidden = window.scrollY < 600;
    }
    window.addEventListener('scroll', () => {
      if (!framePending) {
        framePending = true;
        requestAnimationFrame(updateChapter);
      }
    }, { passive: true });
    updateChapter();
  }

  // -------------------------------------------------------- language menu
  function initLanguageMenu() {
    const langMenu = $('#lang-menu');
    if (!langMenu) return;
    document.addEventListener('click', (event) => {
      if (langMenu.open && !langMenu.contains(event.target)) langMenu.open = false;
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') langMenu.open = false;
    });
  }

  initCopyButtons();
  initTabs();
  initProgress();
  initSkillLibrary();
  initDemo();
  initGuideMenu();
  initChapterTracking();
  initLanguageMenu();
})();
