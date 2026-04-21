// PawCare — main.js
// Handles: AJAX doctor filter, auto-dismiss flash, payment form, animations

document.addEventListener('DOMContentLoaded', () => {

  // ── Auto-dismiss flash messages after 4 seconds ──────────────────────
  const flashes = document.querySelectorAll('.flash-toast');
  flashes.forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.6s, transform 0.6s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-12px)';
      setTimeout(() => el.remove(), 600);
    }, 4000);
  });

  // ── Doctor specialization AJAX filter ────────────────────────────────
  const filterBtns = document.querySelectorAll('[data-spec-filter]');
  const doctorGrid = document.getElementById('doctors-grid');

  if (filterBtns.length && doctorGrid) {
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        // Active state
        filterBtns.forEach(b => b.classList.remove('filter-active'));
        btn.classList.add('filter-active');

        const spec = btn.dataset.specFilter;
        const url  = `/api/doctors?specialization=${encodeURIComponent(spec)}`;

        // Fade out
        doctorGrid.style.opacity = '0.4';
        doctorGrid.style.transition = 'opacity 0.2s';

        fetch(url)
          .then(r => r.json())
          .then(doctors => {
            doctorGrid.innerHTML = doctors.length
              ? doctors.map(d => renderDoctorCard(d)).join('')
              : '<p style="color:var(--muted);grid-column:1/-1;text-align:center;padding:2rem;">No doctors found for this specialization.</p>';
            doctorGrid.style.opacity = '1';
            // Re-attach book-now listeners
            attachBookListeners();
          })
          .catch(() => { doctorGrid.style.opacity = '1'; });
      });
    });
  }

  // ── Render a doctor card (used after AJAX fetch) ───────────────────
  function renderDoctorCard(d) {
    const statusBadge = d.status === 'available'
      ? `<span class="availability-badge available">🟢 Available</span>`
      : `<span class="availability-badge unavailable">🔴 Unavailable</span>`;
    const bookBtn = d.status === 'available'
      ? `<button class="book-now-btn" data-doctor-id="${d.id}" data-doctor-name="${d.name}">Book →</button>`
      : `<span style="font-size:0.78rem;color:var(--muted);">Unavailable</span>`;
    return `
      <div class="vet-card">
        <div class="vet-img" style="background:${d.bg_color};">${d.emoji}</div>
        <div class="vet-body">
          <div class="vet-card-name">${d.name}</div>
          <div class="vet-card-spec">${d.specialization}</div>
          <div style="font-size:0.8rem;color:var(--muted);line-height:1.6;">${d.experience} · ${d.qualification}</div>
          <div class="vet-card-footer">
            ${statusBadge}
            ${bookBtn}
          </div>
        </div>
      </div>`;
  }

  // ── Attach Book Now button listeners (inline booking jump) ────────
  function attachBookListeners() {
    document.querySelectorAll('.book-now-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const id   = btn.dataset.doctorId;
        const name = btn.dataset.doctorName;
        // Set doctor_id in booking form
        const select = document.getElementById('doctor_id');
        if (select) {
          select.value = id;
          // Highlight the selection
          select.style.borderColor = 'var(--sage-dark)';
        }
        // Scroll to booking form
        const bookSec = document.getElementById('book');
        if (bookSec) bookSec.scrollIntoView({ behavior: 'smooth' });
        // Show toast
        showToast(`Booking with ${name} selected!`, 'success');
      });
    });
  }
  attachBookListeners();

  // ── Simple toast helper ─────────────────────────────────────────────
  function showToast(msg, type) {
    const toast = document.createElement('div');
    toast.className = `flash-toast ${type}`;
    toast.style.position = 'fixed';
    toast.style.top = '24px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '280px';
    toast.style.textAlign = 'center';
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = 'opacity 0.5s';
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 500);
    }, 3000);
  }

  // ── Payment method switcher (on payment.html) ─────────────────────
  const payForm = document.getElementById('payment-form');
  if (payForm) {
    const method = payForm.dataset.method;
    const sections = document.querySelectorAll('.pay-section');
    sections.forEach(s => {
      if (s.dataset.for === method) {
        s.style.display = 'block';
      } else {
        s.style.display = 'none';
      }
    });
  }

  // ── Booking form: pre-fill owner name from session (if available) ─
  const ownerInput = document.querySelector('input[name="owner_name"]');
  // The owner name is pre-filled via Jinja if logged in

  // ── Intersection observer for scroll animations ───────────────────
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-in');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.service-card, .vet-card, .testimonial-card').forEach(el => {
      observer.observe(el);
    });
  }

  // ── Admin: confirm before destructive actions ─────────────────────
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

  // ── Status badge color helper (admin table) ───────────────────────
  document.querySelectorAll('.status-badge').forEach(badge => {
    const s = badge.textContent.trim();
    if (s === 'Pending')   { badge.style.background='#FEF3C7'; badge.style.color='#92400E'; }
    if (s === 'Confirmed') { badge.style.background='#DBEAFE'; badge.style.color='#1E40AF'; }
    if (s === 'Completed') { badge.style.background='#D1FAE5'; badge.style.color='#065F46'; }
    if (s === 'Cancelled') { badge.style.background='#FEE2E2'; badge.style.color='#991B1B'; }
    if (s === 'Paid')      { badge.style.background='#D1FAE5'; badge.style.color='#065F46'; }
  });

});
