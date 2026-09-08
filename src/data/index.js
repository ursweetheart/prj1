/* ═══════════════════════════════════════════════════════════════════════
 * D3 Studio · lớp dữ liệu prototype (ES module)
 *
 * Port từ js/data.js — text content đã thay bằng lorem ipsum.
 * Cấu trúc dữ liệu, IDs, facet values giữ nguyên 100%.
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── Năm bộ lọc ─────────────────────────────────────────────────── */
export const FACETS = [
  {
    id: 'loai', label: 'Loại công trình',
    options: [
      { id: 'chung-cu', label: 'Chung cư' },
      { id: 'nha-pho',  label: 'Nhà phố' },
      { id: 'villa',    label: 'Villa' },
      { id: 'lounge',   label: 'Lounge / F&B' }
    ]
  },
  {
    id: 'khonggian', label: 'Không gian',
    options: [
      { id: 'phong-khach', label: 'Phòng khách' },
      { id: 'phong-ngu',   label: 'Phòng ngủ' },
      { id: 'bep',         label: 'Bếp' },
      { id: 'phong-an',    label: 'Phòng ăn' },
      { id: 'sanh',        label: 'Sảnh' },
      { id: 'quay-bar',    label: 'Quầy bar' }
    ]
  },
  {
    id: 'phongcach', label: 'Phong cách',
    options: [
      { id: 'toi-gian',    label: 'Minimalism' },
      { id: 'hien-dai',    label: 'Modern' },
      { id: 'indochine',   label: 'Indochine' },
      { id: 'tan-co-dien', label: 'Tân cổ điển' },
      { id: 'mid-century', label: 'Mid-century Modern' },
      { id: 'luxury',      label: 'Luxury' },
      { id: 'wabi-sabi',   label: 'Wabi-sabi' },
      { id: 'japandi',     label: 'Japandi' },
      { id: 'zen',         label: 'Japanese / Zen' },
      { id: 'scandi',      label: 'Scandinavian' },
      { id: 'art-deco',    label: 'Art Deco' },
      { id: 'industrial',  label: 'Industrial' },
      { id: 'rustic',      label: 'Rustic' },
      { id: 'bohemian',    label: 'Bohemian' }
    ]
  },
  {
    id: 'tongmau', label: 'Tông màu',
    options: [
      { id: 'sang', label: 'Sáng' },
      { id: 'toi',  label: 'Tối' },
      { id: 'am',   label: 'Ấm' },
      { id: 'lanh', label: 'Lạnh' }
    ]
  },
  {
    id: 'dientich', label: 'Diện tích',
    locked: 'Chưa lọc được — thông số diện tích của công trình chưa nhập.',
    options: [
      { id: 'd60',     label: 'Dưới 60 m²' },
      { id: 'd60-80',  label: '60–80 m²' },
      { id: 'd80-120', label: '80–120 m²' },
      { id: 'd120',    label: 'Trên 120 m²' }
    ]
  }
]

/* ─── Dự án · mỗi dự án chứa một hay nhiều không gian ─────────────── */
export const PROJECTS = [
  {
    id: 'PRJ-01', slug: 'the-linen-suite', name: 'Ipsum Dolor Suite',
    loai: 'chung-cu', year: 2026,
    brief: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vel massa nec enim facilisis fermentum. Vivamus tincidunt velit at sapien ultrices, non dapibus nulla convallis.',
    spaces: [
      {
        id: 'SP-0101', img: '/img/pic1.jpg', ratio: 'sq',
        space: 'Cubiculum et armarium',
        khonggian: 'phong-ngu', phongcach: 'toi-gian', tongmau: ['sang', 'am'],
        note: 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.',
        palette: [
          { hex: '#4c4138', pct: 32, name: 'Gỗ sồi rang' },
          { hex: '#897d71', pct: 19, name: 'Vải bố' },
          { hex: '#695749', pct: 12, name: 'Nâu trầm' },
          { hex: '#796758', pct: 11, name: 'Gỗ ấm' },
          { hex: '#c7c1ba', pct: 8,  name: 'Xám sáng' }
        ],
        hotspots: [
          { x: 71, y: 46, label: 'Armarium vitreum cum aluminio nigro', kind: 'Nội thất đóng theo thiết kế', price: null },
          { x: 45, y: 61, label: 'Sella linteo tecta', kind: 'Đồ rời', price: null },
          { x: 38, y: 50, label: 'Lucerna parietis duabus lucernis', kind: 'Chiếu sáng', price: null }
        ]
      },
      {
        id: 'SP-0102', img: '/img/pic2.jpg', ratio: 'sq',
        space: 'Culina et insula',
        khonggian: 'bep', phongcach: 'hien-dai', tongmau: ['am'],
        note: 'Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.',
        palette: [
          { hex: '#8c8885', pct: 30, name: 'Xám đá' },
          { hex: '#4a423d', pct: 20, name: 'Nâu tối' },
          { hex: '#c3bab3', pct: 20, name: 'Kem xám' },
          { hex: '#ab9288', pct: 6,  name: 'Đất nhạt' },
          { hex: '#14120f', pct: 4,  name: 'Gần đen' }
        ],
        hotspots: []
      }
    ]
  },
  {
    id: 'PRJ-02', slug: 'the-olive-room', name: 'Viridis Conclave',
    loai: 'chung-cu', year: 2026,
    brief: 'Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur.',
    spaces: [
      {
        id: 'SP-0201', img: '/img/pic3.jpg', ratio: 'p45',
        space: 'Angulus ornatus cubiculi',
        khonggian: 'phong-ngu', phongcach: 'mid-century', tongmau: ['am', 'toi'],
        note: 'Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur.',
        palette: [
          { hex: '#443f2f', pct: 33, name: 'Xanh ô liu tối' },
          { hex: '#c4bfba', pct: 13, name: 'Kem' },
          { hex: '#372b1b', pct: 12, name: 'Nâu gỗ đậm' },
          { hex: '#715136', pct: 10, name: 'Gỗ xương cá' },
          { hex: '#a89889', pct: 8,  name: 'Be xám' }
        ],
        hotspots: [
          { x: 33, y: 63, label: 'Sella boucle viridis, cruribus metallis', kind: 'Đồ rời', price: null },
          { x: 50, y: 45, label: 'Speculum rotundum margine metallico', kind: 'Đồ rời', price: null },
          { x: 81, y: 70, label: 'Tabula nucis tria receptacula', kind: 'Đồ rời', price: null }
        ]
      }
    ]
  },
  {
    id: 'PRJ-03', slug: 'the-stone-atrium', name: 'Atrium Lapideum',
    loai: 'villa', year: 2026,
    brief: 'At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi.',
    spaces: [
      {
        id: 'SP-0301', img: '/img/pic6.jpg', ratio: 'sq',
        space: 'Atrium per tabulata',
        khonggian: 'sanh', phongcach: 'hien-dai', tongmau: ['toi'],
        note: 'Temporibus autem quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet.',
        palette: [
          { hex: '#474038', pct: 43, name: 'Đá vân thô' },
          { hex: '#16130f', pct: 15, name: 'Gần đen' },
          { hex: '#898174', pct: 9,  name: 'Xám ấm' },
          { hex: '#faf7ef', pct: 6,  name: 'Trần sáng' },
          { hex: '#2b241d', pct: 5,  name: 'Gỗ sẫm' }
        ],
        hotspots: []
      }
    ]
  },
  {
    id: 'PRJ-04', slug: 'the-lotus-chamber', name: 'Camera Loti',
    loai: 'villa', year: 2026,
    brief: 'Itaque earum rerum hic tenetur a sapiente delectus, ut aut reiciendis voluptatibus maiores alias consequatur aut perferendis doloribus asperiores repellat.',
    spaces: [
      {
        id: 'SP-0401', img: '/img/pic9.jpg', ratio: 'p45',
        space: 'Cubiculum principale',
        khonggian: 'phong-ngu', phongcach: 'indochine', tongmau: ['toi', 'am'],
        note: 'Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit quo minus.',
        palette: [
          { hex: '#4a3e35', pct: 23, name: 'Gỗ sơn đen' },
          { hex: '#161411', pct: 19, name: 'Gần đen' },
          { hex: '#69574a', pct: 17, name: 'Nâu đất' },
          { hex: '#7e7269', pct: 12, name: 'Xám ấm' },
          { hex: '#7a6857', pct: 10, name: 'Đồng mờ' }
        ],
        hotspots: [
          { x: 55, y: 63, label: 'Mensa consolatoria ligno nigro picta', kind: 'Đồ rời', price: null },
          { x: 53, y: 52, label: 'Vas ceramicum flore caeruleo', kind: 'Trang trí', price: null },
          { x: 55, y: 32, label: 'Pictura olei vestis longae', kind: 'Tranh', price: null }
        ]
      }
    ]
  },
  {
    id: 'PRJ-05', slug: 'the-green-arches', name: 'Arcus Virides',
    loai: 'nha-pho', year: 2026,
    brief: 'Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.',
    spaces: [
      {
        id: 'SP-0501', img: '/img/pic7.jpg', ratio: 'sq',
        space: 'Cenaculum',
        khonggian: 'phong-an', phongcach: 'tan-co-dien', tongmau: ['toi'],
        note: 'Sunt in culpa qui officia deserunt mollit anim id est laborum sed ut perspiciatis.',
        palette: [
          { hex: '#8a7d74', pct: 21, name: 'Xám ấm' },
          { hex: '#3c3831', pct: 21, name: 'Xanh rêu tối' },
          { hex: '#ccbfb2', pct: 15, name: 'Kem' },
          { hex: '#aa9a8e', pct: 10, name: 'Be' },
          { hex: '#100e0b', pct: 10, name: 'Gần đen' }
        ],
        hotspots: []
      }
    ]
  },
  {
    id: 'PRJ-06', slug: 'the-copper-table', name: 'Mensa Cuprea',
    loai: 'chung-cu', year: 2026,
    brief: 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam eaque ipsa.',
    spaces: [
      {
        id: 'SP-0601', img: '/img/pic8.jpg', ratio: 'sq',
        space: 'Cenaculum obscurum',
        khonggian: 'phong-an', phongcach: 'luxury', tongmau: ['toi'],
        note: 'Neque porro quisquam est qui dolorem ipsum quia dolor sit amet consectetur adipisci velit.',
        palette: [
          { hex: '#413b34', pct: 30, name: 'Nâu tối' },
          { hex: '#8b857e', pct: 27, name: 'Xám ấm' },
          { hex: '#12100d', pct: 15, name: 'Gần đen' },
          { hex: '#2d261d', pct: 4,  name: 'Gỗ sẫm' },
          { hex: '#6c5546', pct: 4,  name: 'Đồng' }
        ],
        hotspots: []
      }
    ]
  }
]

/* ─── Thông số công trình ─────────────────────────────────────────────
 * `null` = chưa cung cấp. Giao diện hiển thị "—" chứ không đoán. */
export const SPECS = {
  'PRJ-01': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-02': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-03': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-04': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-05': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-06': { dientich: null, sophong: null, thoigian: null, mucdautu: null }
}

export const SPEC_LABELS = [
  ['loai',     'Loại hình'],
  ['dientich', 'Diện tích'],
  ['sophong',  'Số phòng'],
  ['phongcach','Phong cách'],
  ['tongmau',  'Tông màu chủ đạo'],
  ['thoigian', 'Thời gian thi công'],
  ['mucdautu', 'Mức đầu tư']
]

/* ─── Dịch vụ và quy trình ─────────────────────────────────────────── */
export const SERVICES = [
  { name: 'Lorem Ipsum Design',
    desc: 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium totam rem aperiam.' },
  { name: 'Dolor Sit Amet',
    desc: 'Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit sed quia consequuntur magni.' },
  { name: 'Consectetur Adipiscing',
    desc: 'Ut enim ad minima veniam quis nostrum exercitationem ullam corporis suscipit laboriosam nisi ut aliquid.' },
  { name: 'Tempor Incididunt',
    desc: 'Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur.' }
]

export const PROCESS = [
  { n: '01', name: 'Primum occursum',
    desc: 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vel massa nec enim facilisis.' },
  { n: '02', name: 'Conceptus et planum',
    desc: 'Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam.' },
  { n: '03', name: 'Imago tridimensiva',
    desc: 'Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.' },
  { n: '04', name: 'Fasciculus technicus',
    desc: 'Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque.' },
  { n: '05', name: 'Constructio et custodia',
    desc: 'At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium.' },
  { n: '06', name: 'Traditio',
    desc: 'Itaque earum rerum hic tenetur a sapiente delectus ut aut reiciendis voluptatibus maiores.' }
]

/* ─── Tra cứu nhanh ───────────────────────────────────────────────── */
export const LOAI_LABEL = {}
export const KG_LABEL = {}
export const PC_LABEL = {}
export const TM_LABEL = {}
FACETS.forEach(f => {
  const map = { loai: LOAI_LABEL, khonggian: KG_LABEL, phongcach: PC_LABEL, tongmau: TM_LABEL }[f.id]
  if (map) f.options.forEach(o => { map[o.id] = o.label })
})

/* Danh sách phẳng các không gian */
export const SPACES = PROJECTS.flatMap(p =>
  p.spaces.map(s => ({
    ...s,
    projectId: p.id, projectSlug: p.slug, projectName: p.name,
    loai: p.loai, year: p.year
  }))
)

export const bySlug = slug => PROJECTS.find(p => p.slug === slug) || null
export const spacesOf = projectId => SPACES.filter(s => s.projectId === projectId)

/* Không gian tương tự */
export function similarTo(space, limit = 3) {
  const score = s => {
    if (s.id === space.id) return -1
    let n = 0
    if (s.phongcach === space.phongcach) n += 3
    if (s.khonggian === space.khonggian) n += 2
    n += s.tongmau.filter(t => space.tongmau.includes(t)).length
    if (s.loai === space.loai) n += 1
    return n
  }
  return SPACES.filter(s => s.id !== space.id)
    .map(s => ({ s, n: score(s) }))
    .sort((a, b) => b.n - a.n)
    .slice(0, limit)
    .map(o => o.s)
}
