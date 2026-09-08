/* ═══════════════════════════════════════════════════════════════════════
 * D3 Studio · lớp dữ liệu prototype
 *
 * Quy ước trung thực về dữ liệu:
 *  · Facet (loại hình / không gian / phong cách / tông màu) suy ra từ
 *    chính ảnh render thật của D3 — quan sát được, không suy diễn.
 *  · Dải màu (`palette`) được TRÍCH từ điểm ảnh của từng file bằng phân
 *    cụm màu, đúng như M9 trong tài liệu đặc tả. Không có mã màu tự nghĩ.
 *  · Trường nào chưa có dữ liệu thật thì để `null` và giao diện hiển thị
 *    dấu "—". Không điền số phỏng đoán (diện tích, thời gian, mức đầu tư,
 *    giá món đồ).
 *  · Câu 9 của khảo sát: KHÔNG lưu và KHÔNG hiển thị bản vẽ kỹ thuật,
 *    tên chủ nhà, địa chỉ công trình, nhà cung cấp vật tư, đối tác thi
 *    công. Các trường đó không tồn tại trong mô hình dữ liệu này.
 *  · Tên công trình đặt tiếng Anh theo câu 34; đây là tên tạm để dựng
 *    giao diện, D3 chốt tên thật khi bàn giao nội dung.
 *
 * Quyết định mô hình dữ liệu quan trọng nhất (§5.2 M1): đơn vị gắn nhãn
 * là KHÔNG GIAN (space), không phải dự án. Một dự án có thể chứa nhiều
 * không gian mang phong cách khác nhau — xem PRJ-01.
 * ═══════════════════════════════════════════════════════════════════ */

/* ─── Năm bộ lọc khách hàng đã chọn (câu 16) ──────────────────────── */
const FACETS = [
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
    /* 14 phong cách D3 khai ở câu 12 — giữ đủ để thấy độ rộng của
       taxonomy; ô nào chưa có công trình sẽ hiện số 0 */
    id: 'phongcach', label: 'Phong cách',
    options: [
      { id: 'toi-gian',   label: 'Minimalism' },
      { id: 'hien-dai',   label: 'Modern' },
      { id: 'indochine',  label: 'Indochine' },
      { id: 'tan-co-dien',label: 'Tân cổ điển' },
      { id: 'mid-century',label: 'Mid-century Modern' },
      { id: 'luxury',     label: 'Luxury' },
      { id: 'wabi-sabi',  label: 'Wabi-sabi' },
      { id: 'japandi',    label: 'Japandi' },
      { id: 'zen',        label: 'Japanese / Zen' },
      { id: 'scandi',     label: 'Scandinavian' },
      { id: 'art-deco',   label: 'Art Deco' },
      { id: 'industrial', label: 'Industrial' },
      { id: 'rustic',     label: 'Rustic' },
      { id: 'bohemian',   label: 'Bohemian' }
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
    /* Câu 16 xếp Diện tích vào 5 bộ lọc chính, nhưng thông số diện tích
       của từng công trình chưa được nhập nên chưa lọc được. Giao diện
       vẫn dựng đủ ô để D3 thấy chỗ, và khoá lại thay vì trả 0 kết quả
       một cách im lặng. */
    id: 'dientich', label: 'Diện tích',
    locked: 'Chưa lọc được — thông số diện tích của công trình chưa nhập.',
    options: [
      { id: 'd60',     label: 'Dưới 60 m²' },
      { id: 'd60-80',  label: '60–80 m²' },
      { id: 'd80-120', label: '80–120 m²' },
      { id: 'd120',    label: 'Trên 120 m²' }
    ]
  }
];

/* ─── Dự án · mỗi dự án chứa một hay nhiều không gian ─────────────── */
const PROJECTS = [
  {
    id: 'PRJ-01', slug: 'the-linen-suite', name: 'The Linen Suite',
    loai: 'chung-cu', year: 2026,
    /* Chính dự án này là minh chứng cho quyết định gắn nhãn ở cấp không
       gian: phòng ngủ theo hướng tối giản, bếp lại theo hướng hiện đại. */
    brief: 'Căn hộ của một gia đình trẻ, giữ trần cao và để ánh sáng tự nhiên dẫn dắt toàn bộ căn. Vật liệu chọn theo cảm giác chạm: vải bố thô ở tường, gỗ sồi màu nhạt ở sàn, kính khói cho khối tủ áo để tủ vừa là nơi chứa vừa là vách ngăn nhẹ giữa khu ngủ và khu sinh hoạt.',
    spaces: [
      {
        id: 'SP-0101', img: 'img/pic1.jpg', ratio: 'sq',
        space: 'Phòng ngủ và tủ áo',
        khonggian: 'phong-ngu', phongcach: 'toi-gian', tongmau: ['sang', 'am'],
        note: 'Khối tủ áo kính khói đứng tách khỏi tường, vừa chứa đồ vừa chắn tầm nhìn từ cửa vào giường.',
        palette: [
          { hex: '#4c4138', pct: 32, name: 'Gỗ sồi rang' },
          { hex: '#897d71', pct: 19, name: 'Vải bố' },
          { hex: '#695749', pct: 12, name: 'Nâu trầm' },
          { hex: '#796758', pct: 11, name: 'Gỗ ấm' },
          { hex: '#c7c1ba', pct: 8,  name: 'Xám sáng' }
        ],
        hotspots: [
          { x: 71, y: 46, label: 'Tủ áo kính khói khung nhôm đen', kind: 'Nội thất đóng theo thiết kế', price: null },
          { x: 45, y: 61, label: 'Ghế bành bọc vải bố', kind: 'Đồ rời', price: null },
          { x: 38, y: 50, label: 'Đèn tường hai bóng thân đồng', kind: 'Chiếu sáng', price: null }
        ]
      },
      {
        id: 'SP-0102', img: 'img/pic2.jpg', ratio: 'sq',
        space: 'Bếp và đảo ăn nhanh',
        khonggian: 'bep', phongcach: 'hien-dai', tongmau: ['am'],
        note: 'Ghế đảo bọc nỉ tông terracotta là điểm màu duy nhất trong khu bếp.',
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
    id: 'PRJ-02', slug: 'the-olive-room', name: 'The Olive Room',
    loai: 'chung-cu', year: 2026,
    brief: 'Một phòng ngủ nhỏ được xử lý bằng màu thay vì bằng chi tiết. Tường sơn xanh ô liu đậm kéo chiều sâu cho căn phòng hẹp, sàn gỗ xương cá giữ nhịp cổ điển, còn đồ rời thì cố tình chọn hình khối tròn mềm để phá thế vuông của phòng.',
    spaces: [
      {
        id: 'SP-0201', img: 'img/pic3.jpg', ratio: 'p45',
        space: 'Góc trang điểm phòng ngủ',
        khonggian: 'phong-ngu', phongcach: 'mid-century', tongmau: ['am', 'toi'],
        note: 'Bàn trang điểm mặt đá, chân uốn sơn trắng, đặt sát cửa sổ để dùng sáng tự nhiên.',
        palette: [
          { hex: '#443f2f', pct: 33, name: 'Xanh ô liu tối' },
          { hex: '#c4bfba', pct: 13, name: 'Kem' },
          { hex: '#372b1b', pct: 12, name: 'Nâu gỗ đậm' },
          { hex: '#715136', pct: 10, name: 'Gỗ xương cá' },
          { hex: '#a89889', pct: 8,  name: 'Be xám' }
        ],
        hotspots: [
          { x: 33, y: 63, label: 'Ghế boucle xanh ô liu, chân kim loại đen', kind: 'Đồ rời', price: null },
          { x: 50, y: 45, label: 'Gương tròn viền kim loại đen', kind: 'Đồ rời', price: null },
          { x: 81, y: 70, label: 'Tab gỗ óc chó ba hộc, tay nắm đồng', kind: 'Đồ rời', price: null }
        ]
      }
    ]
  },
  {
    id: 'PRJ-03', slug: 'the-stone-atrium', name: 'The Stone Atrium',
    loai: 'villa', year: 2026,
    brief: 'Sảnh thông tầng của một villa, đóng vai trò nút giao của cả nhà: thang bộ, thang máy và cửa ra sân đều gặp nhau ở đây. Vì là không gian đi qua chứ không phải nơi ngồi lại, vật liệu chọn loại chịu được va chạm và giữ được vẻ tối: đá tự nhiên vân thô, gỗ sẫm và một dải đèn giấu chân tường.',
    spaces: [
      {
        id: 'SP-0301', img: 'img/pic6.jpg', ratio: 'sq',
        space: 'Sảnh thông tầng',
        khonggian: 'sanh', phongcach: 'hien-dai', tongmau: ['toi'],
        note: 'Đèn giấu ở mũi bậc và chân tường thay cho đèn trần, giữ được độ tối chủ ý của sảnh.',
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
    id: 'PRJ-04', slug: 'the-lotus-chamber', name: 'The Lotus Chamber',
    loai: 'villa', year: 2026,
    brief: 'Phòng ngủ chính đi theo hướng Đông Dương nhưng bỏ hết chi tiết rườm rà, chỉ giữ ba thứ làm nên chất Indochine: gỗ sơn đen, hoạ tiết gốm hoa lam và một bức tranh chân dung áo dài đặt làm điểm nhìn khi bước vào phòng.',
    spaces: [
      {
        id: 'SP-0401', img: 'img/pic9.jpg', ratio: 'p45',
        space: 'Phòng ngủ chính',
        khonggian: 'phong-ngu', phongcach: 'indochine', tongmau: ['toi', 'am'],
        note: 'Bàn console gỗ sơn đen và bình gốm hoa lam làm nhóm điểm nhìn ngay lối vào phòng.',
        palette: [
          { hex: '#4a3e35', pct: 23, name: 'Gỗ sơn đen' },
          { hex: '#161411', pct: 19, name: 'Gần đen' },
          { hex: '#69574a', pct: 17, name: 'Nâu đất' },
          { hex: '#7e7269', pct: 12, name: 'Xám ấm' },
          { hex: '#7a6857', pct: 10, name: 'Đồng mờ' }
        ],
        hotspots: [
          { x: 55, y: 63, label: 'Bàn console gỗ sơn đen, chân tiện', kind: 'Đồ rời', price: null },
          { x: 53, y: 52, label: 'Bình gốm hoa lam', kind: 'Trang trí', price: null },
          { x: 55, y: 32, label: 'Tranh sơn dầu chân dung áo dài, khung gỗ sơn đen', kind: 'Tranh', price: null }
        ]
      }
    ]
  },
  {
    id: 'PRJ-05', slug: 'the-green-arches', name: 'The Green Arches',
    loai: 'nha-pho', year: 2026,
    brief: 'Phòng ăn nhà phố với ba hốc tường cuốn vòm ốp nỉ xanh rêu. Hốc vòm vừa che hệ tủ chứa vừa tạo nhịp cho bức tường dài, và đèn thả pha lê chạy dọc bàn giữ trục đối xứng của cả phòng.',
    spaces: [
      {
        id: 'SP-0501', img: 'img/pic7.jpg', ratio: 'sq',
        space: 'Phòng ăn',
        khonggian: 'phong-an', phongcach: 'tan-co-dien', tongmau: ['toi'],
        note: 'Sàn đá lát ô bàn cờ và đèn thả pha lê dài giữ trục đối xứng cho bàn mười ghế.',
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
    id: 'PRJ-06', slug: 'the-copper-table', name: 'The Copper Table',
    loai: 'chung-cu', year: 2026,
    brief: 'Phòng ăn tông tối cho một căn hộ tầng cao, lấy sáng bằng đèn thả đồng thay vì bằng cửa sổ. Bàn ăn đặt lệch khỏi trục phòng để lấy đường đi thông từ bếp ra khu tiếp khách.',
    spaces: [
      {
        id: 'SP-0601', img: 'img/pic8.jpg', ratio: 'sq',
        space: 'Phòng ăn',
        khonggian: 'phong-an', phongcach: 'luxury', tongmau: ['toi'],
        note: 'Ba đèn thả đồng đặt thấp trên mặt bàn, làm nguồn sáng chính cho khu ăn.',
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
];

/* ─── Thông số công trình ─────────────────────────────────────────────
 * `null` = D3 chưa cung cấp. Giao diện hiển thị "—" chứ không đoán. */
const SPECS = {
  'PRJ-01': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-02': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-03': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-04': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-05': { dientich: null, sophong: null, thoigian: null, mucdautu: null },
  'PRJ-06': { dientich: null, sophong: null, thoigian: null, mucdautu: null }
};

const SPEC_LABELS = [
  ['loai',     'Loại hình'],
  ['dientich', 'Diện tích'],
  ['sophong',  'Số phòng'],
  ['phongcach','Phong cách'],
  ['tongmau',  'Tông màu chủ đạo'],
  ['thoigian', 'Thời gian thi công'],
  ['mucdautu', 'Mức đầu tư']
];

/* ─── Dịch vụ và quy trình (câu 36) ───────────────────────────────── */
const SERVICES = [
  { name: 'Thiết kế nội thất',
    desc: 'Từ đo hiện trạng, bố trí mặt bằng, dựng concept 3D tới bộ hồ sơ triển khai để thi công đúng thiết kế.' },
  { name: 'Thi công hoàn thiện',
    desc: 'Nhận thi công phần hoàn thiện và nội thất theo đúng hồ sơ đã duyệt, một đầu mối chịu trách nhiệm.' },
  { name: 'Nội thất đóng theo thiết kế',
    desc: 'Tủ, kệ, giường, vách trang trí đóng riêng theo kích thước thật của căn, không dùng module có sẵn.' },
  { name: 'Không gian thương mại',
    desc: 'Lounge, F&B, showroom — nhóm công trình được tách riêng khỏi khu nhà ở theo yêu cầu của D3.' }
];

const PROCESS = [
  { n: '01', name: 'Gặp và đo hiện trạng',
    desc: 'Nghe nhu cầu sử dụng của từng thành viên, đo lại hiện trạng, chốt ngân sách khung.' },
  { n: '02', name: 'Concept và mặt bằng',
    desc: 'Đề xuất hai hướng bố trí mặt bằng kèm bảng vật liệu, chọn một hướng để phát triển tiếp.' },
  { n: '03', name: 'Phối cảnh 3D',
    desc: 'Dựng phối cảnh từng không gian để chủ nhà thấy trước, chỉnh tới khi duyệt.' },
  { n: '04', name: 'Hồ sơ triển khai',
    desc: 'Bộ hồ sơ kỹ thuật đủ để đội thi công làm đúng: chi tiết đồ đóng, điện chiếu sáng, vật liệu.' },
  { n: '05', name: 'Thi công và giám sát',
    desc: 'Thi công theo hồ sơ, có người của D3 giám sát và báo tiến độ theo tuần.' },
  { n: '06', name: 'Bàn giao',
    desc: 'Nghiệm thu từng không gian, hướng dẫn bảo trì vật liệu, chụp ảnh hoàn thiện.' }
];

/* ─── Tra cứu nhanh ───────────────────────────────────────────────── */
const LOAI_LABEL = {};
const KG_LABEL = {};
const PC_LABEL = {};
const TM_LABEL = {};
FACETS.forEach(f => {
  const map = { loai: LOAI_LABEL, khonggian: KG_LABEL, phongcach: PC_LABEL, tongmau: TM_LABEL }[f.id];
  if (map) f.options.forEach(o => { map[o.id] = o.label });
});

/* Danh sách phẳng các không gian — đơn vị mà lưới và bộ lọc làm việc */
const SPACES = PROJECTS.flatMap(p =>
  p.spaces.map(s => ({
    ...s,
    projectId: p.id, projectSlug: p.slug, projectName: p.name,
    loai: p.loai, year: p.year
  }))
);

const bySlug = slug => PROJECTS.find(p => p.slug === slug) || null;
const spacesOf = projectId => SPACES.filter(s => s.projectId === projectId);

/* Không gian tương tự (M3): cùng phong cách trước, rồi cùng tông màu */
function similarTo(space, limit = 3) {
  const score = s => {
    if (s.id === space.id) return -1;
    let n = 0;
    if (s.phongcach === space.phongcach) n += 3;
    if (s.khonggian === space.khonggian) n += 2;
    n += s.tongmau.filter(t => space.tongmau.includes(t)).length;
    if (s.loai === space.loai) n += 1;
    return n;
  };
  return SPACES.filter(s => s.id !== space.id)
    .map(s => ({ s, n: score(s) }))
    .sort((a, b) => b.n - a.n)
    .slice(0, limit)
    .map(o => o.s);
}

window.D3 = {
  FACETS, PROJECTS, SPACES, SPECS, SPEC_LABELS, SERVICES, PROCESS,
  LOAI_LABEL, KG_LABEL, PC_LABEL, TM_LABEL,
  bySlug, spacesOf, similarTo
};
