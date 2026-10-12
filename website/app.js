/**
 * ShareHear — Interactive Client Script
 * Handles Tab Switching, FAQ Accordion, Copy to Clipboard, and Mobile Navigation
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Mobile Menu Toggle
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const mobileNav = document.getElementById('mobile-nav');

  if (mobileToggle && mobileNav) {
    mobileToggle.addEventListener('click', () => {
      const isExpanded = mobileToggle.getAttribute('aria-expanded') === 'true';
      mobileToggle.setAttribute('aria-expanded', !isExpanded);
      mobileNav.classList.toggle('hidden');
    });

    // Close mobile nav when clicking any nav link
    const mobileLinks = mobileNav.querySelectorAll('a');
    mobileLinks.forEach(link => {
      link.addEventListener('click', () => {
        mobileNav.classList.add('hidden');
        mobileToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // 2. Interactive Guide Tabs
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanels = document.querySelectorAll('.tab-content');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('aria-controls');

      // Update button states
      tabButtons.forEach(b => {
        b.classList.remove('tab-active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('tab-active');
      btn.setAttribute('aria-selected', 'true');

      // Update panel visibility
      tabPanels.forEach(panel => {
        if (panel.id === targetId) {
          panel.classList.remove('hidden');
          panel.classList.add('block');
        } else {
          panel.classList.remove('block');
          panel.classList.add('hidden');
        }
      });
    });
  });

  // 3. FAQ Accordion with Keyboard Support
  const faqItems = document.querySelectorAll('.faq-item');

  faqItems.forEach(item => {
    const toggleFaq = () => {
      const isOpened = item.classList.contains('is-open');
      const answer = item.querySelector('.faq-answer');

      // Close all other items for clean accordion behavior
      faqItems.forEach(otherItem => {
        if (otherItem !== item) {
          otherItem.classList.remove('is-open');
          otherItem.setAttribute('aria-expanded', 'false');
          const otherAnswer = otherItem.querySelector('.faq-answer');
          if (otherAnswer) otherAnswer.classList.add('hidden');
        }
      });

      if (isOpened) {
        item.classList.remove('is-open');
        item.setAttribute('aria-expanded', 'false');
        if (answer) answer.classList.add('hidden');
      } else {
        item.classList.add('is-open');
        item.setAttribute('aria-expanded', 'true');
        if (answer) answer.classList.remove('hidden');
      }
    };

    item.addEventListener('click', toggleFaq);
    item.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleFaq();
      }
    });
  });

  // 4. Copy to Clipboard Utility
  const copyButtons = document.querySelectorAll('.copy-btn');

  copyButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const textToCopy = btn.getAttribute('data-copy');
      if (!textToCopy) return;

      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalHTML = btn.innerHTML;
        
        // Show success icon
        btn.innerHTML = `<svg class="w-4 h-4 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        btn.setAttribute('title', '¡Copiado!');

        setTimeout(() => {
          btn.innerHTML = originalHTML;
          btn.setAttribute('title', 'Copiar puerto');
        }, 2000);
      } catch (err) {
        console.error('No se pudo copiar el texto: ', err);
      }
    });
  });

  // 5. Subtle Latency Simulation in Live Visualizer
  const latencyBadge = document.querySelector('#equalizer-demo');
  if (latencyBadge) {
    const latencies = ['11ms', '12ms', '10ms', '13ms', '11ms', '14ms', '12ms'];
    let idx = 0;
    setInterval(() => {
      idx = (idx + 1) % latencies.length;
      const statusElement = document.querySelector('strong.text-emerald-400');
      if (statusElement && statusElement.parentElement) {
        statusElement.parentElement.innerHTML = `<strong class="text-emerald-400">RTT:</strong> ${latencies[idx]}`;
      }
    }, 3200);
  }
});
