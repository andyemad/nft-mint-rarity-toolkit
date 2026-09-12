(() => {
  'use strict';

  const icon = (name) => `<svg class="icon" aria-hidden="true"><use href="#${name}"></use></svg>`;
  const toast = document.querySelector('#toast');
  let toastTimer;
  function announce(message) {
    clearTimeout(toastTimer);
    toast.textContent = message;
    toast.hidden = false;
    toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
  }

  // Commands remain selectable when clipboard permission is unavailable.
  document.querySelectorAll('pre .copy').forEach((button) => {
    const pre = button.closest('pre');
    const code = pre.querySelector('code');
    const label = pre.dataset.label === 'Discord prompt' ? 'Copy Discord prompt' : 'Copy terminal command';
    button.type = 'button';
    button.hidden = false;
    button.innerHTML = `${icon('copy')}<span>Copy</span>`;
    button.setAttribute('aria-label', label);
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(code.textContent);
        button.innerHTML = `${icon('check')}<span>Copied</span>`;
        button.dataset.copied = 'true';
        button.setAttribute('aria-label', 'Copied to clipboard');
        announce('Copied. Paste it when you’re ready.');
        setTimeout(() => {
          button.innerHTML = `${icon('copy')}<span>Copy</span>`;
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
        announce('Automatic copying is unavailable. The text is selected so you can copy it.');
      }
    });
  });

  // Native content is visible before enhancement, including all three OS panels.
  const osTabs = [...document.querySelectorAll('.os-tabs [role="tab"]')];
  document.querySelector('.os-tabs').hidden = false;
  function selectOS(tab, moveFocus = false) {
    osTabs.forEach((item) => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
    });
    if (moveFocus) tab.focus();
  }
  const initialOS = /Mac|iPhone|iPad/.test(navigator.platform) ? 'mac' : /Linux/.test(navigator.platform) ? 'linux' : 'windows';
  selectOS(document.querySelector(`#tab-${initialOS}`));
  osTabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectOS(tab));
    tab.addEventListener('keydown', (event) => {
      let target;
      if (event.key === 'ArrowRight') target = (index + 1) % osTabs.length;
      if (event.key === 'ArrowLeft') target = (index + osTabs.length - 1) % osTabs.length;
      if (event.key === 'Home') target = 0;
      if (event.key === 'End') target = osTabs.length - 1;
      if (target !== undefined) {
        event.preventDefault();
        selectOS(osTabs[target], true);
      }
    });
  });

  // Store only the four setup checkboxes, with an in-memory fallback.
  const storageKey = 'nft-toolkit-setup-v1';
  const completionInputs = [...document.querySelectorAll('[data-complete]')];
  const validSteps = completionInputs.map((input) => input.dataset.complete);
  let completed = [];
  let storageAvailable = true;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(saved)) completed = [...new Set(saved.filter((id) => validSteps.includes(id)))];
  } catch { storageAvailable = false; }
  const progressHelp = document.querySelector('#progress-help');
  const progressCount = document.querySelector('#progress-count');
  const progressMeter = document.querySelector('#setup-meter');
  function updateProgress() {
    const count = completionInputs.filter((input) => input.checked).length;
    progressMeter.value = count;
    progressCount.textContent = `${count} of 4`;
    progressHelp.textContent = storageAvailable ? 'Saved in this browser' : 'Progress kept for this visit';
  }
  document.querySelector('.setup-progress').hidden = false;
  completionInputs.forEach((input) => {
    input.closest('.completion').hidden = false;
    input.checked = completed.includes(input.dataset.complete);
    input.addEventListener('change', () => {
      completed = completionInputs.filter((item) => item.checked).map((item) => item.dataset.complete);
      try { localStorage.setItem(storageKey, JSON.stringify(completed)); }
      catch { storageAvailable = false; }
      updateProgress();
      if (completed.length === 4) announce('Setup complete. Your next step: send your agent a message.');
    });
  });
  updateProgress();

  // Search and category filters operate on the complete, server-rendered library.
  const search = document.querySelector('#skill-search');
  const filters = [...document.querySelectorAll('[data-filter]')];
  const categories = [...document.querySelectorAll('#skill-results .cat')].map((heading) => ({
    heading,
    container: heading.nextElementSibling,
    cards: [...heading.nextElementSibling.querySelectorAll('.skill')]
  }));
  let activeFilter = 'all';
  document.querySelector('.library-tools').hidden = false;
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
      category.container.hidden = visible === 0;
      total += visible;
    }
    document.querySelector('#skill-count').textContent = `${total} ${total === 1 ? 'skill' : 'skills'}${total === 31 ? ' to put to work' : ' found'}`;
    document.querySelector('#empty-skills').hidden = total !== 0;
  }
  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.filter;
      filters.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
      filterSkills();
    });
  });
  search.addEventListener('input', filterSkills);
  document.querySelector('#reset-search').addEventListener('click', () => {
    search.value = '';
    activeFilter = 'all';
    filters.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.filter === 'all')));
    filterSkills();
    search.focus();
  });
  filterSkills();

  // Clearly labeled examples, with no wallet connection or network calls.
  const rows = document.querySelector('#result-rows');
  const rarityRows = rows.innerHTML;
  const demoData = {
    rarity: {
      prompt: 'rank this collection and show me the rare ones',
      answer: 'Collection ranked. Here are the three rarest.',
      title: 'Rarity report', subtitle: 'Demo collection', rows: rarityRows,
      foot: 'Research only. No transactions sent.'
    },
    mint: {
      prompt: 'check this mint before I connect my wallet',
      answer: 'I’ll check the contract, price, and supply first.',
      title: 'Mint research', subtitle: 'Example checklist',
      rows: ['Verify the real contract', 'Read the onchain mint price', 'Check remaining supply'].map((text) => `<div class="result-row">${icon('search')}<span>${text}</span><em>Check first</em></div>`).join(''),
      foot: 'Review the findings before approving a mint.'
    },
    wallet: {
      prompt: 'what has this wallet been buying lately?',
      answer: 'I’ll turn the wallet’s public activity into a report.',
      title: 'Wallet intelligence', subtitle: 'Example report',
      rows: ['Recent purchases', 'Collections held', 'Sales and transfers'].map((text) => `<div class="result-row">${icon('code')}<span>${text}</span><em>Onchain</em></div>`).join(''),
      foot: 'Public wallet data. No private keys needed.'
    }
  };
  document.querySelector('.demo-controls').hidden = false;
  const demoButtons = [...document.querySelectorAll('[data-demo]')];
  demoButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const data = demoData[button.dataset.demo];
      document.querySelector('#demo-prompt').innerHTML = `<span class="mention">@hermes</span> ${data.prompt}`;
      document.querySelector('#demo-answer').textContent = data.answer;
      document.querySelector('#result-title').textContent = data.title;
      document.querySelector('#result-subtitle').textContent = data.subtitle;
      rows.innerHTML = data.rows;
      document.querySelector('#result-foot').textContent = data.foot;
      demoButtons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    });
  });

  const mobile = window.matchMedia('(max-width: 700px)');
  const menu = document.querySelector('#guide-menu');
  function updateMenu() { menu.open = !mobile.matches; }
  updateMenu();
  mobile.addEventListener('change', updateMenu);
  menu.querySelector('summary').addEventListener('click', (event) => {
    if (!mobile.matches) event.preventDefault();
  });
  document.querySelectorAll('.toc a').forEach((link) => {
    link.addEventListener('click', () => { if (mobile.matches) menu.open = false; });
  });

  const chapters = [...document.querySelectorAll('.guide-content section[id]')];
  const links = [...document.querySelectorAll('.toc a')];
  const backToTop = document.querySelector('.top');
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
    backToTop.hidden = window.scrollY < 600;
  }
  window.addEventListener('scroll', () => {
    if (!framePending) {
      framePending = true;
      requestAnimationFrame(updateChapter);
    }
  }, { passive: true });
  updateChapter();
})();
