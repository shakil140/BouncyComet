/* ==========================================================================
   Bouncy Comet - site behaviour
   Vanilla ES2018+. No dependencies. Defensive about missing elements.
   Modules: mobile nav, sticky header, scroll reveal, footer year, rails
            (carousels), floating-toy parallax, screenshot lightbox,
            contact form, smooth anchor scroll, the rules of each game
            (folded on a phone), the launch switch.
   ========================================================================== */

(function () {
  'use strict';

  /* ======================================================================
     LAUNCH SWITCH - is Dice Duo public on Google Play yet?
     ----------------------------------------------------------------------
     false  The game is on Google Play in closed testing: its store page opens
            for enrolled testers only. Every page says "In closed testing on
            Google Play" and offers "Tell me when it launches". This is how
            the site ships.
     true   The game is public. Every "closed testing" line becomes a
            "Get it on Google Play" link, on every page at once.

     LAUNCH DAY: change false to true on the line below. Nothing else.
     Then publish as always (python tools/stamp_assets.py first, so browsers
     fetch this file again).

     How it works: a page writes both versions of a line and marks them
     data-launch="soon" and data-launch="live". The "live" one also carries
     the `hidden` attribute, so a browser that never runs this file shows the
     "soon" version. initLaunch() (section 10) shows one set and hides the
     other. The store address is written in the links themselves:
     https://play.google.com/store/apps/details?id=com.bouncycomet.diceduo
     ====================================================================== */

  var DICE_DUO_IS_PUBLIC = false;


  /* ----------------------------------------------------------------------
     Helpers
     ---------------------------------------------------------------------- */

  var $  = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  // The line in each page's <head> hides scroll-reveal blocks and folds the mobile menu
  // before first paint, trusting this file to show them again. This flag tells it the
  // file did arrive: without it that line takes the 'js' class away once the page has loaded.
  window.__bc = 1;

  // Pages with a strict Content-Security-Policy cannot run the inline line that
  // normally sets this before first paint, so make sure it is always there.
  document.documentElement.classList.add('js');

  function prefersReducedMotion() {
    return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  var FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]),' +
                  'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

  // Takes parts of the page behind a modal layer out of the tab order and the a11y tree.
  function setInert(elements, on) {
    elements.forEach(function (el) {
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
    var f = $$(FOCUSABLE, container).filter(function (el) {
      return el.offsetParent !== null || el === document.activeElement;
    });
    if (!f.length) { return; }
    var first = f[0];
    var last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  }

  var ICON = {
    left:  '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    right: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    close: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round"/></svg>'
  };


  /* ----------------------------------------------------------------------
     1. Mobile navigation
     ---------------------------------------------------------------------- */

  function initNav() {
    var burger = $('#navBurger');
    var panel  = $('#navLinks');
    if (!burger || !panel) { return; }

    var body = document.body;

    function behind() { return [document.getElementById('main'), $('.site-footer')]; }
    function isOpen() { return body.classList.contains('nav-open'); }

    function openNav() {
      body.classList.add('nav-open');
      burger.setAttribute('aria-expanded', 'true');
      burger.setAttribute('aria-label', 'Close menu');
      // The panel covers the page, so take everything behind it out of reach.
      setInert(behind(), true);
      var first = panel.querySelector(FOCUSABLE);
      if (first) { first.focus(); }
    }

    function closeNav(restoreFocus) {
      if (!isOpen()) { return; }
      body.classList.remove('nav-open');
      burger.setAttribute('aria-expanded', 'false');
      burger.setAttribute('aria-label', 'Open menu');
      setInert(behind(), false);
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

    // Escape closes and returns focus to the burger; Tab stays inside the header.
    document.addEventListener('keydown', function (e) {
      if (!isOpen()) { return; }
      if (e.key === 'Escape') { closeNav(true); }
      else if (e.key === 'Tab') { trapTab(e, $('#siteHeader') || panel); }
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
     2. Sticky header + floating-toy parallax (one scroll listener for both)
     ---------------------------------------------------------------------- */

  function initScroll() {
    var header = $('#siteHeader');
    var groups = prefersReducedMotion() ? [] : $$('.floaters');
    if (!header && !groups.length) { return; }

    var ticking = false;

    function apply() {
      ticking = false;
      var y = window.pageYOffset || document.documentElement.scrollTop || 0;
      if (header) { header.classList.toggle('is-stuck', y > 8); }
      // Each group of toys drifts a little, by how far its section is from the middle
      // of the screen: at most 70px, times each toy's own --depth.
      var vh = window.innerHeight || 1;
      groups.forEach(function (group) {
        var box = group.getBoundingClientRect();
        if (box.bottom < -200 || box.top > vh + 200) { return; }
        var off = (box.top + box.height / 2 - vh / 2) / vh;
        var shift = Math.max(-1, Math.min(1, off)) * -70;
        group.style.setProperty('--shift', shift.toFixed(1));
      });
    }

    function onScroll() {
      if (ticking) { return; }
      ticking = true;
      window.requestAnimationFrame(apply);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
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
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0 });

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
     5. Rails: a row of cards that becomes a carousel when it does not fit.
        The track is a normal scroll area (swipe, wheel and arrow keys work
        without this code). The script adds the two arrow buttons, fades the
        cut-off end, and brings a card into view when Tab lands on it (a
        browser does not do that for a card that is already partly visible).
     ---------------------------------------------------------------------- */

  function initRails() {
    $$('.rail').forEach(function (rail) {
      var track = $('.rail__track', rail);
      if (!track) { return; }

      var label = rail.getAttribute('data-label') || 'items';
      var controls = document.createElement('div');
      controls.className = 'rail__controls';

      function makeBtn(dir, text, glyph) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'rail__btn';
        b.setAttribute('aria-label', text);
        b.innerHTML = glyph;
        b.addEventListener('click', function () {
          // An arrow at its end stays focusable (aria-disabled, not disabled): a button
          // that disables itself under the keyboard would drop the focus to the page.
          if (b.getAttribute('aria-disabled') === 'true') { return; }
          var first = track.firstElementChild;
          var step = first ? first.getBoundingClientRect().width + 20 : track.clientWidth * 0.8;
          track.scrollBy({ left: dir * Math.max(step, track.clientWidth * 0.6), behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
        });
        return b;
      }

      var prev = makeBtn(-1, 'Scroll ' + label + ' back', ICON.left);
      var next = makeBtn(1, 'Scroll ' + label + ' forward', ICON.right);
      controls.appendChild(prev);
      controls.appendChild(next);
      rail.appendChild(controls);

      var ticking = false;

      function update() {
        ticking = false;
        var max = track.scrollWidth - track.clientWidth;
        var scrollable = max > 4;
        rail.classList.toggle('is-scrollable', scrollable);
        // A scroll area must be reachable by keyboard only when it actually scrolls.
        if (scrollable) { track.setAttribute('tabindex', '0'); } else { track.removeAttribute('tabindex'); }
        var atStart = track.scrollLeft <= 2;
        var atEnd = track.scrollLeft >= max - 2;
        prev.setAttribute('aria-disabled', atStart ? 'true' : 'false');
        next.setAttribute('aria-disabled', atEnd ? 'true' : 'false');
        rail.classList.toggle('at-start', atStart);
        rail.classList.toggle('at-end', atEnd);
      }

      function queue() {
        if (ticking) { return; }
        ticking = true;
        window.requestAnimationFrame(update);
      }

      track.addEventListener('focusin', function (e) {
        if (e.target === track || typeof e.target.scrollIntoView !== 'function') { return; }
        if (!rail.classList.contains('is-scrollable')) { return; }
        var el = e.target;
        // One frame later: the browser's own scrolling for the focus change runs first
        // and would undo a scroll made inside this event.
        window.requestAnimationFrame(function () {
          var card = el.getBoundingClientRect();
          var view = track.getBoundingClientRect();
          if (card.left >= view.left + 8 && card.right <= view.right - 8) { return; }
          var target = track.scrollLeft + (card.left + card.width / 2) - (view.left + view.width / 2);
          track.scrollTo({ left: target, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
        });
      });

      track.addEventListener('scroll', queue, { passive: true });
      window.addEventListener('resize', queue, { passive: true });
      window.addEventListener('load', queue);
      update();
    });
  }


  /* ----------------------------------------------------------------------
     6. Screenshot lightbox
        Every .shot button carries data-full="<large image>".
     ---------------------------------------------------------------------- */

  function initLightbox() {
    var shots = $$('.shot');
    if (!shots.length) { return; }

    var slides = shots.map(function (shot) {
      var img = shot.querySelector('img');
      var capEl = shot.querySelector('.shot__cap');
      return {
        el: shot,
        // The tile's own <img src> is a JPEG: the fallback when the large WebP cannot be shown.
        fallback: (img && img.getAttribute('src')) || '',
        src: shot.getAttribute('data-full') || (img && (img.currentSrc || img.getAttribute('src'))) || '',
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
    bigImg.setAttribute('width', '720');
    bigImg.setAttribute('height', '1280');
    bigImg.addEventListener('error', function () {
      var spare = bigImg.getAttribute('data-fallback');
      if (!spare) { return; }
      bigImg.removeAttribute('data-fallback');          // only once: never loop on a missing file
      bigImg.setAttribute('src', spare);
    });

    var cap = document.createElement('p');
    cap.className = 'lb__cap';
    cap.setAttribute('aria-live', 'polite');

    function makeBtn(cls, label, glyph) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'lb__btn ' + cls;
      b.setAttribute('aria-label', label);
      b.innerHTML = glyph;
      return b;
    }

    var btnClose = makeBtn('lb__close', 'Close screenshot viewer', ICON.close);
    var btnPrev  = makeBtn('lb__prev', 'Previous screenshot', ICON.left);
    var btnNext  = makeBtn('lb__next', 'Next screenshot', ICON.right);

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

    function behind() { return [document.getElementById('main'), $('.site-footer'), $('.site-header')]; }

    function render(i) {
      current = (i + slides.length) % slides.length;
      var s = slides[current];
      if (s.fallback && s.fallback !== s.src) { bigImg.setAttribute('data-fallback', s.fallback); }
      else { bigImg.removeAttribute('data-fallback'); }
      bigImg.setAttribute('src', s.src);
      bigImg.setAttribute('alt', s.alt);
      cap.textContent = s.cap + ' (' + (current + 1) + ' of ' + slides.length + ')';
    }

    function open(i, trigger) {
      lastTrigger = trigger || null;
      render(i);
      overlay.hidden = false;
      document.body.classList.add('lb-open');
      setInert(behind(), true);
      btnClose.focus();
    }

    function close() {
      if (overlay.hidden) { return; }
      overlay.hidden = true;
      document.body.classList.remove('lb-open');
      setInert(behind(), false);
      if (lastTrigger && typeof lastTrigger.focus === 'function') { lastTrigger.focus(); }
      lastTrigger = null;
    }

    slides.forEach(function (s, i) {
      s.el.addEventListener('click', function () { open(i, s.el); });
    });

    btnClose.addEventListener('click', close);
    btnPrev.addEventListener('click', function () { render(current - 1); });
    btnNext.addEventListener('click', function () { render(current + 1); });

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target === dialog) { close(); }
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
     7. Contact form
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
              .catch(function () { showNote('Something went wrong. Email hello@bouncycomet.com instead.', true); });

          Keep the validation block above it; delete the mailto: builder.
          (A third-party endpoint also needs a line in the Privacy Policy.)
     ====================================================================== */

  function initContactForm() {
    var form = $('#contactForm');
    if (!form) { return; }

    var note = $('.form__note', form) || $('#formNote');
    var TO = 'hello@bouncycomet.com';
    // Player support and purchase questions go to the address every page names for them.
    var SUPPORT = 'support@bouncycomet.com';
    var SUPPORT_TOPICS = ['Player support', 'Purchase or refund'];

    // keepFocus: the note is announced (it is a live region) but the keyboard stays where it is.
    function showNote(message, isError, keepFocus) {
      if (!note) { window.alert(message); return; }
      note.textContent = message;
      note.classList.toggle('form__note--error', !!isError);
      note.hidden = false;
      note.setAttribute('role', isError ? 'alert' : 'status');
      note.setAttribute('aria-live', isError ? 'assertive' : 'polite');
      note.setAttribute('tabindex', '-1');
      if (!keepFocus) { note.focus(); }
    }

    // "Your name", "Email", "Message": the visible label of a field, without its star.
    function labelOf(el) {
      var label = el.id ? form.querySelector('label[for="' + el.id + '"]') : null;
      return label ? label.textContent.replace('*', '').trim() : 'this field';
    }

    // Only flag a field the visitor has actually left.
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
        // Say which field and what is wrong with it, then put the keyboard in that field.
        var bad = form.querySelector(':invalid');
        var what = 'Please fill in the required fields before sending.';
        if (bad) {
          what = (bad.validity && bad.validity.valueMissing)
            ? 'Please fill in "' + labelOf(bad) + '" before sending.'
            : (bad.type === 'email')
              ? 'That email address does not look complete. Please check "' + labelOf(bad) + '".'
              : 'Please check "' + labelOf(bad) + '".';
        }
        showNote(what, true, true);
        if (bad && typeof bad.focus === 'function') { bad.focus(); }
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

      var to = SUPPORT_TOPICS.indexOf(topic) !== -1 ? SUPPORT : TO;

      var href = 'mailto:' + to +
                 '?subject=' + encodeURIComponent(subject) +
                 '&body=' + encodeURIComponent(bodyLines.join('\n'));

      window.location.href = href;

      showNote('Your email app should have opened with the message ready to send. ' +
               'If nothing happened, email ' + to + ' directly.');
    });
  }


  /* ----------------------------------------------------------------------
     8. Smooth scroll for same-page anchors
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
     9. The three steps of each game (Dice Duo page)
        On a phone css/style.css folds every list of steps behind its button
        (.js .rules:not(.is-open)); this opens and closes them. On a wide
        screen the buttons are hidden and the steps always show.
     ---------------------------------------------------------------------- */

  function initRules() {
    $$('.rules__toggle').forEach(function (button) {
      var block = button.closest ? button.closest('.rules') : button.parentNode;
      if (!block) { return; }
      button.addEventListener('click', function () {
        var open = block.classList.toggle('is-open');
        button.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    });
  }


  /* ----------------------------------------------------------------------
     10. Launch switch
         Shows the data-launch="live" version of every marked line when
         DICE_DUO_IS_PUBLIC (top of this file) is true, and the
         data-launch="soon" version when it is false.
     ---------------------------------------------------------------------- */

  function initLaunch() {
    $$('[data-launch]').forEach(function (el) {
      el.hidden = (el.getAttribute('data-launch') === 'live') !== DICE_DUO_IS_PUBLIC;
    });
  }


  /* ----------------------------------------------------------------------
     Boot
     ---------------------------------------------------------------------- */

  function boot() {
    try { initLaunch(); }        catch (e) { /* no-op */ }
    try { initNav(); }           catch (e) { /* no-op */ }
    try { initScroll(); }        catch (e) { /* no-op */ }
    try { initReveal(); }        catch (e) { /* no-op */ }
    try { initYear(); }          catch (e) { /* no-op */ }
    try { initRails(); }         catch (e) { /* no-op */ }
    try { initLightbox(); }      catch (e) { /* no-op */ }
    try { initContactForm(); }   catch (e) { /* no-op */ }
    try { initSmoothScroll(); }  catch (e) { /* no-op */ }
    try { initRules(); }         catch (e) { /* no-op */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
