/* ═══════════════════════════════════════════════════════════════════════
 * Thông tin D3 Studio cho trang "Về chúng tôi" và "Liên hệ" (change studio-pages).
 *
 * Mỗi giá trị chưa xác nhận có `mau: true`: trang hiện nhãn "Thông tin mẫu" và KHÔNG biến nó thành
 * link gọi / gửi mail / nhắn Zalo / bản đồ, để khách không liên lạc nhầm số của người khác.
 * Khi có thông tin thật: sửa `gia_tri`, đặt `mau: false`. Nhớ sửa cả mục "Quy trình làm việc với D3 Studio"
 * ở /quan-tri/tri-thuc cho trùng với `quy_trinh` bên dưới.
 * ═══════════════════════════════════════════════════════════════════ */

export const STUDIO = {
  ten: 'D3 Studio',
  mo_ta: {
    gia_tri: 'D3 Studio là văn phòng thiết kế kiến trúc, nội thất và diễn hoạ 3D tại Hà Nội. Chúng tôi làm căn hộ, nhà phố, ' +
      'biệt thự và không gian thương mại, từ ý tưởng đầu tiên tới khi bàn giao, với phối cảnh 3D để khách thấy trước ' +
      'không gian của mình.',
    mau: true
  },
  dien_thoai: { gia_tri: '0900 000 000', mau: true },
  zalo: { gia_tri: '0900 000 000', mau: true }, // số điện thoại đăng ký Zalo
  email: { gia_tri: 'lienhe@d3studio.example', mau: true },
  dia_chi: { gia_tri: 'Số 1 phố Mẫu, quận Mẫu, Hà Nội', mau: true },
  gio_lam: { gia_tri: 'Thứ Hai – Thứ Bảy, 8:30 – 17:30', mau: true },
  doi_ngu: [ // tên thật của nhóm; vai trò là mẫu
    { ten: 'Phạm Việt Tùng', vai_tro: { gia_tri: 'Kiến trúc sư', mau: true } },
    { ten: 'Trần Xuân Bằng', vai_tro: { gia_tri: 'Thiết kế nội thất', mau: true } },
    { ten: 'Trần Xuân Tuấn', vai_tro: { gia_tri: 'Diễn hoạ 3D', mau: true } }
  ],
  // trang /dich-vu khi không có backend (GitHub Pages): bản sao 3 gói "service" mẫu của kho tri thức (kb/sample.json).
  // Khi có backend trang đọc GET /services (gói đang dùng ở /quan-tri/tri-thuc), danh sách này không được dùng.
  dich_vu: {
    mau: true,
    goi: [
      { title: 'Dịch vụ thiết kế phòng khách', content: 'Thiết kế phòng khách gồm bố trí công năng, sofa, kệ tivi, đèn và rèm. Có thể đóng riêng sofa và tủ kệ theo kích thước.' },
      { title: 'Dịch vụ thiết kế phòng ngủ', content: 'Thiết kế phòng ngủ master và phòng ngủ phụ: giường, tủ quần áo âm tường, bàn trang điểm, ánh sáng dịu.' },
      { title: 'Dịch vụ thiết kế bếp và phòng ăn', content: 'Thiết kế bếp và phòng ăn: tủ bếp trên dưới, đảo bếp, bàn ăn, lắp đặt thiết bị bếp.' }
    ]
  },
  // cùng 5 bước với mục "Quy trình làm việc với D3 Studio" của trợ lý (cũng là dữ liệu mẫu)
  quy_trinh: {
    mau: true,
    buoc: [
      { ten: 'Tư vấn và khảo sát', mo_ta: 'Nghe nhu cầu, ngân sách và đo đạc hiện trạng.' },
      { ten: 'Ý tưởng mặt bằng', mo_ta: 'Bố trí công năng và hướng phong cách.' },
      { ten: 'Phối cảnh 3D', mo_ta: 'Khách xem trước không gian, chỉnh tới khi ưng ý.' },
      { ten: 'Bản vẽ thi công', mo_ta: 'Hồ sơ kỹ thuật, vật liệu và dự toán.' },
      { ten: 'Thi công và bàn giao', mo_ta: 'Giám sát thi công, nghiệm thu và bàn giao.' }
    ]
  }
}

/* Link chỉ có khi giá trị đã xác nhận; giá trị mẫu trả về null để trang hiện chữ thường */
const real = d => !!d && !d.mau && !!d.gia_tri
export const telHref = d => real(d) ? 'tel:' + d.gia_tri.replace(/[^\d+]/g, '') : null
export const mailHref = d => real(d) ? 'mailto:' + d.gia_tri.trim() : null
export const zaloHref = d => real(d) ? 'https://zalo.me/' + d.gia_tri.replace(/\D/g, '') : null
export const mapHref = d => real(d) ? 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(d.gia_tri) : null
