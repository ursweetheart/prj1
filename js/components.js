/* ═══════════════════════════════════════════════════════════════════════
 * D3 Studio · component Vue dùng chung cho mọi trang
 * Vue 3 global build, không cần bước build — mở file là chạy.
 * ═══════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  const { reactive, computed, ref, onMounted, onUnmounted, watch } = Vue;

  /* ─── Moodboard: lưu không gian khách thích (M6 · hành vi lưu) ───── */
  const KEY = 'd3-moodboard-v1';
  const saved = reactive({ ids: [] });
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (Array.isArray(raw)) saved.ids = raw;
  } catch (e) { /* localStorage bị chặn — moodboard chạy trong bộ nhớ */ }

  const store = {
    saved,
    has: id => saved.ids.includes(id),
    toggle(id) {
      const i = saved.ids.indexOf(id);
      if (i === -1) saved.ids.push(id); else saved.ids.splice(i, 1);
      try { localStorage.setItem(KEY, JSON.stringify(saved.ids)); } catch (e) {}
    },
    get count() { return saved.ids.length }
  };

  /* ─── Dấu hiệu thương hiệu ────────────────────────────────────────── */
  const BrandMark = {
    template: `
      <svg class="brand-mark" viewBox="0 0 128 128" fill="none" stroke="currentColor"
           stroke-width="4" stroke-linecap="square" aria-hidden="true">
        <path d="M28 32 H60 a20 20 0 0 1 0 40 H28 Z"/>
        <path d="M28 58 H60 a20 20 0 0 1 0 40 H28 Z"/>
        <path d="M54 20 H72 a26 26 0 0 1 0 52"/>
        <path d="M54 108 H72 a26 26 0 0 0 0 -52"/>
      </svg>`
  };

  /* ─── Thanh điều hướng (tên mục theo câu 35) ─────────────────────── */
  const SiteNav = {
    components: { BrandMark },
    props: { current: { type: String, default: '' } },
    setup() {
      const open = ref(false);
      const links = [
        { href: 'cong-trinh.html', label: 'Công trình', key: 'cong-trinh' },
        { href: 'dich-vu.html',    label: 'Dịch vụ',    key: 'dich-vu' },
        { href: 've-chung-toi.html', label: 'Về chúng tôi', key: 've-chung-toi' },
        { href: 'lien-he.html',    label: 'Liên hệ',    key: 'lien-he' }
      ];
      return { open, links, store };
    },
    template: `
      <header class="nav">
        <div class="wrap wrap-wide">
          <div class="nav-in">
            <a class="brand" href="index.html" aria-label="D3 Studio · trang chủ">
              <brand-mark /><span class="brand-word">D3 Studio</span>
            </a>
            <nav class="nav-links" aria-label="Điều hướng chính">
              <a v-for="l in links" :key="l.key" :href="l.href"
                 :aria-current="current === l.key ? 'page' : null">{{ l.label }}</a>
            </nav>
            <a class="btn btn-secondary nav-cta" href="lien-he.html">
              Nhận tư vấn<span v-if="store.count" class="num"> · đã lưu {{ store.count }}</span>
            </a>
            <button class="nav-burger" type="button" :aria-expanded="String(open)"
                    aria-label="Mở menu" @click="open = !open"><span></span></button>
          </div>
        </div>
        <div class="nav-sheet" v-if="open">
          <a v-for="l in links" :key="l.key" :href="l.href">{{ l.label }}</a>
          <a class="btn btn-primary" href="lien-he.html" style="margin-top:12px">Nhận tư vấn</a>
        </div>
      </header>`
  };

  /* ─── Chân trang (thông tin theo câu 37) ─────────────────────────── */
  const SiteFoot = {
    components: { BrandMark },
    template: `
      <footer class="foot">
        <div class="wrap wrap-wide">
          <div class="foot-grid">
            <div>
              <a class="brand" href="index.html"><brand-mark /><span class="brand-word">D3 Studio</span></a>
              <p class="small" style="margin-top:14px; max-width:38ch">
                Thiết kế và thi công nội thất. Thư viện công trình được phân loại theo
                từng không gian để bạn tìm đúng thứ mình đang hình dung.
              </p>
            </div>
            <div>
              <h5>Khám phá</h5>
              <a href="cong-trinh.html">Công trình</a>
              <a href="cong-trinh.html#loai=chung-cu">Nhà ở</a>
              <a href="cong-trinh.html#loai=lounge">Thương mại</a>
              <a href="dich-vu.html">Dịch vụ và quy trình</a>
              <a href="ve-chung-toi.html">Về chúng tôi</a>
            </div>
            <div>
              <h5>Liên hệ</h5>
              <a href="lien-he.html">Gửi yêu cầu tư vấn</a>
              <a href="lien-he.html#zalo">Nhắn Zalo</a>
              <a href="lien-he.html#ban-do">Địa chỉ và bản đồ</a>
              <p class="small" style="margin-top:10px">
                Số điện thoại, email và địa chỉ văn phòng — D3 điền khi bàn giao nội dung.
              </p>
            </div>
          </div>
          <div class="foot-base">
            <span>© {{ new Date().getFullYear() }} D3 Studio</span>
            <span>Ảnh công trình thuộc bản quyền D3 Studio</span>
          </div>
        </div>
      </footer>`
  };

  /* ─── Thẻ không gian ──────────────────────────────────────────────── */
  const SpaceCard = {
    props: { space: Object, tall: Boolean, ratio: { type: String, default: '' } },
    setup(props) {
      const D = window.D3;
      const facetLine = computed(() => [
        D.LOAI_LABEL[props.space.loai],
        D.KG_LABEL[props.space.khonggian],
        D.PC_LABEL[props.space.phongcach]
      ].filter(Boolean).join(' · '));
      const href = computed(() =>
        'cong-trinh-chi-tiet.html#' + props.space.projectSlug + '/' + props.space.id);
      return { facetLine, href, store };
    },
    template: `
      <article class="pcard" :class="{ tall }">
        <div style="position:relative">
          <a :href="href" :aria-label="space.projectName + ' — ' + space.space">
            <div class="media" :class="ratio || space.ratio">
              <img :src="space.img" :alt="space.projectName + ' — ' + space.space" loading="lazy">
            </div>
          </a>
          <button class="pcard-save" type="button"
                  :aria-pressed="String(store.has(space.id))"
                  :aria-label="store.has(space.id) ? 'Bỏ lưu không gian này' : 'Lưu vào moodboard'"
                  @click="store.toggle(space.id)">
            <svg viewBox="0 0 24 24" :fill="store.has(space.id) ? 'currentColor' : 'none'"
                 stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <path d="M12 20s-7-4.4-7-9.4A4.1 4.1 0 0 1 12 7a4.1 4.1 0 0 1 7 3.6c0 5-7 9.4-7 9.4z"/>
            </svg>
          </button>
        </div>
        <a class="pcard-cap" :href="href">
          <span class="pcard-name">{{ space.projectName }} — {{ space.space }}</span>
          <span class="pcard-facets">{{ facetLine }}</span>
        </a>
      </article>`
  };

  /* ─── Cột bộ lọc (câu 31) ─────────────────────────────────────────── */
  const FacetPanel = {
    props: { selected: Object, counts: Object },
    emits: ['toggle', 'clear'],
    setup() {
      const expanded = reactive({});
      return { facets: window.D3.FACETS, expanded };
    },
    methods: {
      visible(f) {
        if (f.options.length <= 6 || this.expanded[f.id]) return f.options;
        return f.options.slice(0, 6);
      },
      hidden(f) { return Math.max(0, f.options.length - 6) }
    },
    template: `
      <div class="facets">
        <div v-for="f in facets" :key="f.id">
          <div class="facet-h">
            <span class="meta">{{ f.label }}</span>
            <button v-if="!f.locked && selected[f.id] && selected[f.id].length"
                    class="btn btn-ghost" style="min-height:auto;padding:2px 4px;font-size:13px"
                    type="button" @click="$emit('clear', f.id)">Bỏ chọn</button>
          </div>
          <p v-if="f.locked" class="field-help" style="margin-bottom:8px">{{ f.locked }}</p>
          <div class="facet-opts">
            <button v-for="o in visible(f)" :key="o.id" class="chip" type="button"
                    :disabled="!!f.locked"
                    :aria-pressed="String(!f.locked && selected[f.id] && selected[f.id].includes(o.id))"
                    @click="!f.locked && $emit('toggle', f.id, o.id)">
              {{ o.label }}
              <span v-if="!f.locked" class="facet-count">{{ counts[f.id] ? (counts[f.id][o.id] || 0) : 0 }}</span>
            </button>
            <button v-if="hidden(f) && !expanded[f.id]" class="btn btn-ghost"
                    style="min-height:38px;font-size:13px" type="button"
                    @click="expanded[f.id] = true">+ {{ hidden(f) }} nữa</button>
          </div>
        </div>
      </div>`
  };

  /* ─── Lightbox (câu 29: bấm ảnh để phóng to) ─────────────────────── */
  const Lightbox = {
    props: { items: Array, index: Number },
    emits: ['close', 'go'],
    setup(props, { emit }) {
      const onKey = e => {
        if (e.key === 'Escape') emit('close');
        if (e.key === 'ArrowRight') emit('go', 1);
        if (e.key === 'ArrowLeft') emit('go', -1);
      };
      onMounted(() => {
        document.addEventListener('keydown', onKey);
        document.body.style.overflow = 'hidden';
      });
      onUnmounted(() => {
        document.removeEventListener('keydown', onKey);
        document.body.style.overflow = '';
      });
      return {};
    },
    template: `
      <div class="lb" role="dialog" aria-modal="true" aria-label="Xem ảnh lớn" @click.self="$emit('close')">
        <div class="lb-bar">
          <span class="meta num">{{ index + 1 }} / {{ items.length }}</span>
          <button class="btn btn-secondary" type="button" @click="$emit('close')">Đóng</button>
        </div>
        <img :src="items[index].img" :alt="items[index].alt">
        <button v-if="items.length > 1" class="lb-nav p" type="button"
                aria-label="Ảnh trước" @click="$emit('go', -1)">‹</button>
        <button v-if="items.length > 1" class="lb-nav n" type="button"
                aria-label="Ảnh sau" @click="$emit('go', 1)">›</button>
      </div>`
  };

  /* ─── Concept ↔ Thực tế (M2) ──────────────────────────────────────
   * D3 chưa gửi cặp ảnh concept / thi công thực tế của cùng một góc,
   * nên phía "Thực tế" hiển thị trạng thái trống thật của trường dữ
   * liệu. Kéo tay cầm vẫn hoạt động để thấy đúng tương tác. */
  const BeforeAfter = {
    props: { concept: String, real: { type: String, default: '' }, alt: String },
    setup() {
      const pos = ref(56);
      const el = ref(null);
      let dragging = false;
      const set = clientX => {
        if (!el.value) return;
        const r = el.value.getBoundingClientRect();
        pos.value = Math.min(100, Math.max(0, ((clientX - r.left) / r.width) * 100));
      };
      const down = e => { dragging = true; set(e.clientX); el.value.setPointerCapture(e.pointerId); };
      const move = e => { if (dragging) set(e.clientX); };
      const up = () => { dragging = false; };
      const key = e => {
        if (e.key === 'ArrowLeft')  pos.value = Math.max(0, pos.value - 4);
        if (e.key === 'ArrowRight') pos.value = Math.min(100, pos.value + 4);
      };
      return { pos, el, down, move, up, key };
    },
    template: `
      <div class="ba" ref="el" :style="{ '--pos': pos + '%' }"
           @pointerdown="down" @pointermove="move" @pointerup="up" @pointercancel="up">
        <img v-if="real" :src="real" :alt="alt + ' — ảnh thi công thực tế'">
        <div v-else class="panel" style="position:absolute;inset:0;display:grid;place-items:center;
             border-radius:0;text-align:center;padding:24px">
          <p class="small" style="max-width:24ch">Ảnh thi công thực tế của góc này đang cập nhật.</p>
        </div>
        <img class="ba-top" :src="concept" :alt="alt + ' — phối cảnh concept'">
        <span class="ba-tag l">Concept</span>
        <span class="ba-tag r">Thực tế</span>
        <div class="ba-handle">
          <button class="ba-knob" type="button" role="slider" tabindex="0"
                  aria-label="Kéo để so sánh concept và thực tế"
                  aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(pos)"
                  @keydown="key">↔</button>
        </div>
      </div>`
  };

  /* ─── Ảnh có điểm nóng (M7) ──────────────────────────────────────── */
  const HotspotImage = {
    props: { space: Object },
    setup() {
      const active = ref(-1);
      return { active };
    },
    methods: {
      cardStyle(h) {
        const right = h.x > 58;
        return {
          left: right ? 'auto' : 'min(' + h.x + '%, calc(100% - 280px))',
          right: right ? 'min(' + (100 - h.x) + '%, calc(100% - 280px))' : 'auto',
          top: h.y > 62 ? 'auto' : 'calc(' + h.y + '% + 26px)',
          bottom: h.y > 62 ? 'calc(' + (100 - h.y) + '% + 26px)' : 'auto'
        };
      }
    },
    template: `
      <div class="hs-wrap">
        <div class="media" :class="space.ratio">
          <img :src="space.img" :alt="space.projectName + ' — ' + space.space">
        </div>
        <button v-for="(h, i) in space.hotspots" :key="i" class="hs" type="button"
                :style="{ left: h.x + '%', top: h.y + '%' }"
                :aria-expanded="String(active === i)" :aria-label="'Xem món đồ: ' + h.label"
                @click="active = active === i ? -1 : i">{{ active === i ? '×' : '+' }}</button>
        <div v-for="(h, i) in space.hotspots" :key="'c' + i" v-show="active === i"
             class="hs-card" :style="cardStyle(h)">
          <span class="meta" style="font-size:11px">{{ h.kind }}</span>
          <b>{{ h.label }}</b>
          <span class="small">Giá tham khảo: {{ h.price || '—' }}</span>
          <a class="btn btn-secondary" style="min-height:38px;padding:8px 12px"
             :href="'cong-trinh.html#phongcach=' + space.phongcach">Xem không gian tương tự</a>
        </div>
      </div>`
  };

  /* ─── Dải màu chủ đạo (M9) ───────────────────────────────────────── */
  const PaletteRow = {
    props: { palette: Array },
    template: `
      <div class="palette">
        <div class="sw" v-for="c in palette" :key="c.hex">
          <i :style="{ background: c.hex }" :title="c.hex"></i>
          <span>{{ c.name }}<br><span class="num">{{ c.pct }}%</span></span>
        </div>
      </div>`
  };

  /* ─── Đăng ký ─────────────────────────────────────────────────────── */
  window.D3UI = {
    store,
    register(app) {
      app.component('BrandMark', BrandMark);
      app.component('SiteNav', SiteNav);
      app.component('SiteFoot', SiteFoot);
      app.component('SpaceCard', SpaceCard);
      app.component('FacetPanel', FacetPanel);
      app.component('Lightbox', Lightbox);
      app.component('BeforeAfter', BeforeAfter);
      app.component('HotspotImage', HotspotImage);
      app.component('PaletteRow', PaletteRow);
      return app;
    },
    /* Lọc đa chiều + đếm kết quả thời gian thực + đồng bộ URL (M1) */
    useBrowse() {
      const D = window.D3;
      const selected = reactive({});
      D.FACETS.forEach(f => { selected[f.id] = [] });

      const readHash = () => {
        const h = location.hash.replace(/^#/, '');
        if (!h) return;
        h.split('&').forEach(part => {
          const [k, v] = part.split('=');
          if (selected[k] && v) selected[k] = v.split(',').filter(Boolean);
        });
      };
      const writeHash = () => {
        const s = Object.entries(selected)
          .filter(([, v]) => v.length)
          .map(([k, v]) => k + '=' + v.join(','))
          .join('&');
        const url = location.pathname + (s ? '#' + s : '');
        history.replaceState(null, '', url);
      };
      readHash();
      watch(selected, writeHash, { deep: true });

      const matches = (s, sel) => Object.entries(sel).every(([k, vals]) => {
        if (!vals.length) return true;
        const v = s[k];
        return Array.isArray(v) ? v.some(x => vals.includes(x)) : vals.includes(v);
      });

      const results = computed(() => D.SPACES.filter(s => matches(s, selected)));

      /* Đếm kiểu facet: với mỗi ô, đếm như thể chỉ ô đó được thêm vào */
      const counts = computed(() => {
        const out = {};
        D.FACETS.forEach(f => {
          out[f.id] = {};
          f.options.forEach(o => {
            const probe = {};
            Object.keys(selected).forEach(k => { probe[k] = selected[k] });
            probe[f.id] = selected[f.id].includes(o.id) ? selected[f.id] : selected[f.id].concat(o.id);
            out[f.id][o.id] = D.SPACES.filter(s => matches(s, probe)).length;
          });
        });
        return out;
      });

      const activeChips = computed(() =>
        Object.entries(selected).flatMap(([fid, vals]) => {
          const f = D.FACETS.find(x => x.id === fid);
          return vals.map(v => ({
            fid, vid: v, label: (f.options.find(o => o.id === v) || {}).label || v
          }));
        }));

      return {
        selected, results, counts, activeChips,
        toggle(fid, oid) {
          const a = selected[fid], i = a.indexOf(oid);
          if (i === -1) a.push(oid); else a.splice(i, 1);
        },
        clear(fid) { selected[fid] = [] },
        clearAll() { Object.keys(selected).forEach(k => { selected[k] = [] }) }
      };
    }
  };
})();
