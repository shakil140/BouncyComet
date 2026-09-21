/* ==========================================================================
   Bouncy Comet - site behaviour
   Vanilla ES2018+. No dependencies. Defensive about missing elements.
   Modules: mobile nav, sticky header, scroll reveal, footer year,
            screenshot lightbox, contact form, smooth anchor scroll.
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     Helpers
     ---------------------------------------------------------------------- */

  var $  = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  // Takes the page behind a modal layer out of the tab order and the a11y tree.
  function setBackgroundInert(on) {
    var parts = [
      document.getElementById('main'),
      document.querySelector('.site-footer'),
      document.querySelector('.site-header')
    ];
    parts.forEach(function (el) {
      if (!el) { return; }
      if (on) {
        if ('inert' in el) { el.inert = true; }
        el.setAttribute('aria-hidden', 'true');
      } else {
        if ('inert' in el) { el.inert = false; }
        el.removeAttribute('aria-hidden');
      }
    });
  }

  // Cycles Tab / Shift+Tab inside `container` so focus cannot escape a modal.
  function trapTab(e, container) {
    if (e.key !== 'Tab') { return; }
    var f = Array.prototype.slice.call(container.querySelectorAll(FOCUSABLE))
      .filter(function (el) { return el.offsetParent !== null || el === document.activeElement; });
    if (!f.length) { return; }
    var first = f[0];
    var last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }

  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),' +
                  'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';


  /* ----------------------------------------------------------------------
     1. Mobile navigation
     ---------------------------------------------------------------------- */

  function initNav() {
    var burger = $('#navBurger');
    var panel  = $('#navLinks');
    if (!burger || !panel) { return; }

    var body = document.body;

    function isOpen() { return body.classList.contains('nav-open'); }

    function openNav() {
      body.classList.add('nav-open');
      burger.setAttribute('aria-expanded', 'true');
      burger.setAttribute('aria-label', 'Close menu');
      // The panel covers the page, so take everything behind it out of reach.
      var main = document.getElementById('main');
      var foot = document.querySelector('.site-footer');
      [main, foot].forEach(function (el) {
        if (!el) { return; }
        if ('inert' in el) { el.inert = true; }
        el.setAttribute('aria-hidden', 'true');
      });
      // Move focus to the first link so keyboard users land inside the panel.
      var first = panel.querySelector(FOCUSABLE);
      if (first) { first.focus(); }
    }

    function closeNav(restoreFocus) {
      if (!isOpen()) { return; }
      body.classList.remove('nav-open');
      burger.setAttribute('aria-expanded', 'false');
      burger.setAttribute('aria-label', 'Open menu');
      var main = document.getElementById('main');
      var foot = document.querySelector('.site-footer');
      [main, foot].forEach(function (el) {
        if (!el) { return; }
        if ('inert' in el) { el.inert = false; }
        el.removeAttribute('aria-hidden');
      });
      if (restoreFocus !== false) { burger.focus(); }
    }

    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      if (isOpen()) { closeNav(true); } else { openNav(); }
    });

    // Any link inside the panel closes it (same-page anchors included).
    panel.addEventListener('click', function (e) {
      var link = e.target && e.target.closest ? e.target.closest('a') : null;
      if (link) { closeNav(false); }
    });

    // Click anywhere outside the panel.
    document.addEventListener('click', function (e) {
      if (!isOpen()) { return; }
      if (panel.contains(e.target) || burger.contains(e.target)) { return; }
      closeNav(true);
    });

    // Escape closes and returns focus to the burger.
    document.addEventListener('keydown', function (e) {
      if (!isOpen()) { return; }
      if (e.key === 'Escape') { closeNav(true); }
      else if (e.key === 'Tab') { trapTab(e, panel); }
    });

    // Leaving mobile width should never strand the page in the open state.
    if (window.matchMedia) {
      var wide = window.matchMedia('(min-width: 900px)');
      var onWide = function (ev) { if (ev.matches) { closeNav(false); } };
      if (typeof wide.addEventListener === 'function') {
        wide.addEventListener('change', onWide);
      } else if (typeof wide.addListener === 'function') {
        wide.addListener(onWide);
      }
    }
  }


  /* ----------------------------------------------------------------------
     2. Sticky header shadow
     ---------------------------------------------------------------------- */

  function initStickyHeader() {
    var header = $('#siteHeader');
    if (!header) { return; }

    var ticking = false;

    function apply() {
      ticking = false;
      var stuck = (window.pageYOffset || document.documentElement.scrollTop || 0) > 8;
      header.classList.toggle('is-stuck', stuck);
    }

    function onScroll() {
      if (ticking) { return; }
      ticking = true;
      window.requestAnimationFrame(apply);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    apply();
  }


  /* ----------------------------------------------------------------------
     3. Scroll reveal
     ---------------------------------------------------------------------- */

  function initReveal() {
    var items = $$('.reveal');
    if (!items.length) { return; }

    function showAll() {
      items.forEach(function (el) { el.classList.add('is-in'); });
    }

    if (!('IntersectionObserver' in window) || prefersReducedMotion()) {
      showAll();
      return;
    }

    var io = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        entry.target.classList.add('is-in');
        observer.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0 });

    items.forEach(function (el) { io.observe(el); });
  }


  /* ----------------------------------------------------------------------
     4. Footer year
     ---------------------------------------------------------------------- */

  function initYear() {
    var el = $('#year');
    if (el) { el.textContent = String(new Date().getFullYear()); }
  }


  /* ----------------------------------------------------------------------
     5. Screenshot lightbox
     ---------------------------------------------------------------------- */

  function initLightbox() {
    var shots = $$('.shot');
    if (!shots.length) { return; }

    // ---- Work out the big image + caption for each shot -----------------
    var slides = shots.map(function (shot) {
      var img = shot.querySelector('img');
      var src = '';

      if (shot.getAttribute('data-full')) {
        src = shot.getAttribute('data-full');
      } else if (img) {
        // "diceback-menu.jpg" -> "diceback-menu@2x.jpg"
        src = img.currentSrc || img.getAttribute('src') || '';
        // currentSrc may already BE the @2x candidate on a retina screen, which
        // would otherwise produce a non-existent "...@2x@2x.webp".
        if (!/@2x(\.[a-z0-9]+)(\?.*)?$/i.test(src)) {
          src = src.replace(/(\.[a-z0-9]+)(\?.*)?$/i, function (m, ext, query) {
            return '@2x' + ext + (query || '');
          });
        }
      }

      var capEl = shot.querySelector('.shot__cap');
      return {
        el: shot,
        src: src,
        alt: (img && img.getAttribute('alt')) || '',
        cap: capEl ? capEl.textContent.trim() : ''
      };
    }).filter(function (s) { return !!s.src; });

    if (!slides.length) { return; }

    // ---- Build the overlay once ----------------------------------------
    var overlay = document.createElement('div');
    overlay.className = 'lb';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Screenshot viewer');
    overlay.hidden = true;

    var dialog = document.createElement('div');
    dialog.className = 'lb__dialog';

    var bigImg = document.createElement('img');
    bigImg.className = 'lb__img';
    bigImg.setAttribute('decoding', 'async');

    var cap = document.createElement('p');
    cap.className = 'lb__cap';

    function makeBtn(cls, label, glyph) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'lb__btn ' + cls;
      b.setAttribute('aria-label', label);
      b.innerHTML = '<span aria-hidden="true">' + glyph + '</span>';
      return b;
    }

    var btnClose = makeBtn('lb__close', 'Close screenshot viewer', '&times;');
    var btnPrev  = makeBtn('lb__prev', 'Previous screenshot', '&#8249;');
    var btnNext  = makeBtn('lb__next', 'Next screenshot', '&#8250;');

    dialog.appendChild(bigImg);
    dialog.appendChild(cap);
    dialog.appendChild(btnClose);
    if (slides.length > 1) {
      dialog.appendChild(btnPrev);
      dialog.appendChild(btnNext);
    }
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    var current = 0;
    var lastTrigger = null;

    function render(i) {
      current = (i + slides.length) % slides.length;
      var s = slides[current];
      bigImg.setAttribute('src', s.src);
      bigImg.setAttribute('alt', s.alt);
      cap.textContent = s.cap;
      overlay.setAttribute('aria-label',
        'Screenshot ' + (current + 1) + ' of ' + slides.length +
        (s.cap ? ': ' + s.cap : ''));
    }

    function open(i, trigger) {
      lastTrigger = trigger || null;
      render(i);
      overlay.hidden = false;
      document.body.classList.add('lb-open');
      setBackgroundInert(true);
      btnClose.focus();
    }

    function close() {
      if (overlay.hidden) { return; }
      overlay.hidden = true;
      document.body.classList.remove('lb-open');
      setBackgroundInert(false);
      if (lastTrigger && typeof lastTrigger.focus === 'function') { lastTrigger.focus(); }
      lastTrigger = null;
    }

    slides.forEach(function (s, i) {
      // A <button class="shot"> is already keyboard-operable; anything else
      // gets the attributes it needs.
      if (s.el.tagName !== 'BUTTON') {
        if (!s.el.hasAttribute('tabindex')) { s.el.setAttribute('tabindex', '0'); }
        if (!s.el.hasAttribute('role')) { s.el.setAttribute('role', 'button'); }
        s.el.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
            e.preventDefault();
            open(i, s.el);
          }
        });
      }
      s.el.addEventListener('click', function () { open(i, s.el); });
    });

    btnClose.addEventListener('click', close);
    btnPrev.addEventListener('click', function () { render(current - 1); });
    btnNext.addEventListener('click', function () { render(current + 1); });

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) { close(); }
    });

    document.addEventListener('keydown', function (e) {
      if (overlay.hidden) { return; }
      if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'ArrowLeft' && slides.length > 1) { render(current - 1); }
      else if (e.key === 'ArrowRight' && slides.length > 1) { render(current + 1); }
      else if (e.key === 'Tab') { trapTab(e, dialog); }
    });
  }


  /* ----------------------------------------------------------------------
     6. Contact form
     ---------------------------------------------------------------------- */

  /* ======================================================================
     SWAPPING IN A REAL FORM BACKEND LATER
     ----------------------------------------------------------------------
     Right now the form opens the visitor's own email client via a mailto:
     link, so the site stays 100% static with no server and no third party.
     To post the form to a service instead:

       1. Formspree - create a form, then in contact.html set:
              <form id="contactForm" action="https://formspree.io/f/XXXXXXX"
                    method="POST">
       2. Web3Forms - add a hidden field to the same form:
              <input type="hidden" name="access_key" value="YOUR-KEY">
          and set action="https://api.web3forms.com/submit"
       3. Replace the body of `handleSubmit` below with:

              e.preventDefault();
              var endpoint = form.getAttribute('action');
              fetch(endpoint, {
                method: 'POST',
                body: new FormData(form),
                headers: { 'Accept': 'application/json' }
              })
              .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
              .then(function () { showNote('Thanks - your message is on its way.'); form.reset(); })
              .catch(function () { showNote('Something went wrong. Email studio@bouncycomet.com instead.', true); });

          Keep the validation block above it; delete the mailto: builder.
     ====================================================================== */

  function initContactForm() {
    var form = $('#contactForm');
    if (!form) { return; }

    var note = $('.form__note', form) || $('#formNote');
    var TO = 'studio@bouncycomet.com';

    function showNote(message, isError) {
      if (!note) { window.alert(message); return; }
      note.textContent = message;
      note.classList.toggle('form__note--error', !!isError);
      note.hidden = false;
      note.setAttribute('role', 'status');
      note.setAttribute('aria-live', 'polite');
      note.setAttribute('tabindex', '-1');
      note.focus();
    }

    // Fallback for browsers without :user-invalid - only flag a field the
    // visitor has actually left.
    $$('.field__input, .field__area', form).forEach(function (el) {
      el.addEventListener('blur', function () { el.classList.add('is-touched'); });
    });

    function value(name) {
      var el = form.elements[name];
      return el && typeof el.value === 'string' ? el.value.trim() : '';
    }

    form.addEventListener('submit', function handleSubmit(e) {
      e.preventDefault();

      // --- Honeypot ---------------------------------------------------
      // The #f-company field is hidden from people, so anything in it is a
      // bot. Pretend it worked and drop the submission silently.
      if (value('company')) {
        showNote('Thanks - your email app should be opening now.', false);
        return;
      }

      // --- Validation -------------------------------------------------
      $$('.field__input, .field__area', form).forEach(function (el) {
        el.classList.add('is-touched');
      });

      if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
        var bad = form.querySelector(':invalid');
        if (bad && typeof bad.focus === 'function') { bad.focus(); }
        showNote('Please fill in the required fields before sending.', true);
        return;
      }

      var name    = value('name');
      var email   = value('email');
      var topic   = value('topic');
      var message = value('message');

      if (!name || !email || !message) {
        showNote('Please fill in the required fields before sending.', true);
        return;
      }

      // --- Compose the mailto: link ------------------------------------
      var subject = 'Bouncy Comet' + (topic ? ' - ' + topic : ' - website enquiry') +
                    ' (' + name + ')';

      var bodyLines = [
        'Name: ' + name,
        'Email: ' + email
      ];
      if (topic) { bodyLines.push('Topic: ' + topic); }
      bodyLines.push('');
      bodyLines.push(message);
      bodyLines.push('');
      bodyLines.push('--');
      bodyLines.push('Sent from bouncycomet.com');

      var href = 'mailto:' + TO +
                 '?subject=' + encodeURIComponent(subject) +
                 '&body=' + encodeURIComponent(bodyLines.join('\n'));

      window.location.href = href;

      showNote('Your email app should have opened with the message ready to send. ' +
               'If nothing happened, email ' + TO + ' directly.');
    });
  }


  /* ----------------------------------------------------------------------
     7. Smooth scroll for same-page anchors
     ---------------------------------------------------------------------- */

  function initSmoothScroll() {
    document.addEventListener('click', function (e) {
      var link = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!link) { return; }
      if (link.hasAttribute('download') || link.getAttribute('target') === '_blank') { return; }

      var hash = link.getAttribute('href');
      if (!hash || hash === '#' || hash.length < 2) { return; }

      var target;
      try { target = document.querySelector(hash); } catch (err) { return; }
      if (!target) { return; }

      e.preventDefault();

      target.scrollIntoView({
        behavior: prefersReducedMotion() ? 'auto' : 'smooth',
        block: 'start'
      });

      // Keep the keyboard in step with the eye.
      if (!target.hasAttribute('tabindex')) { target.setAttribute('tabindex', '-1'); }
      target.focus({ preventScroll: true });

      if (window.history && typeof window.history.replaceState === 'function') {
        window.history.replaceState(null, '', hash);
      }
    });
  }


  /* ----------------------------------------------------------------------
     Boot
     ---------------------------------------------------------------------- */

  function boot() {
    try { initNav(); }           catch (e) { /* no-op */ }
    try { initStickyHeader(); }  catch (e) { /* no-op */ }
    try { initReveal(); }        catch (e) { /* no-op */ }
    try { initYear(); }          catch (e) { /* no-op */ }
    try { initLightbox(); }      catch (e) { /* no-op */ }
    try { initContactForm(); }   catch (e) { /* no-op */ }
    try { initSmoothScroll(); }  catch (e) { /* no-op */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
