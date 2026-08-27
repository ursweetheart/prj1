# TÀI LIỆU PHÂN TÍCH YÊU CẦU

## Website Giới thiệu Dịch vụ & Portfolio Thiết kế Nội thất tích hợp AI

|  |  |
| :---- | :---- |
| **Mã dự án** | PRJ1-INTERIOR-WEB |
| **Phiên bản** | 1.0 (Draft) |
| **Ngày lập** | 27/08/2026 |
| **Người lập** | Tuấn |
| **Loại tài liệu** | Business Analysis Document (BAD) |
| **Tài liệu liên quan** | `02-Bo-cau-hoi-phong-van.md`, `03-User-story-va-tieu-chi-chap-nhan.md`, `04-Mo-hinh-hoa-yeu-cau.md`, `05-Taxonomy-ngon-ngu-thiet-ke.md` |

---

## MỤC LỤC

1. [Bối cảnh & phát biểu vấn đề](#1-bối-cảnh--phát-biểu-vấn-đề)  
2. [Phạm vi và mục tiêu dự án](#2-phạm-vi-và-mục-tiêu-dự-án)  
3. [Xác định các bên liên quan (Stakeholders)](#3-xác-định-các-bên-liên-quan-stakeholders)  
4. [Kế hoạch thu thập yêu cầu (Elicitation Plan)](#4-kế-hoạch-thu-thập-yêu-cầu-elicitation-plan)  
5. [Danh mục tài liệu cần thu thập](#5-danh-mục-tài-liệu-cần-thu-thập)  
6. [Danh mục chức năng & quy trình nghiệp vụ mở rộng](#6-danh-mục-chức-năng--quy-trình-nghiệp-vụ-mở-rộng)  
7. [Lộ trình triển khai & phạm vi đề xuất cho Project 1](#7-lộ-trình-triển-khai--phạm-vi-đề-xuất-cho-project-1)  
8. [Yêu cầu phi chức năng](#8-yêu-cầu-phi-chức-năng)  
9. [Giả định, ràng buộc, rủi ro](#9-giả-định-ràng-buộc-rủi-ro)  
10. [Chỉ số đo lường thành công](#10-chỉ-số-đo-lường-thành-công)

---

## 1\. BỐI CẢNH & PHÁT BIỂU VẤN ĐỀ

### 1.1 Bối cảnh

Công ty hoạt động trong lĩnh vực thiết kế – thi công nội thất. Tài sản giá trị nhất của công ty là **thư viện hình ảnh các công trình đã thực hiện** (concept 3D \+ ảnh thực tế thi công). Hiện tại tài sản này đang nằm rải rác ở page của công ty (facebook D3 Studio), Behance (có thể hiểu như là linkedin cho các công ty thiết kế), trên máy của các nhân phiên thi công dịch vụ.

Yêu cầu ban đầu từ phía khách hàng (sếp) qua trao đổi:

> *"nó chỉ giới thiệu như này thôi… đúng rồi kiểu show ảnh thiết kế vậy thôi"* *"anh chỉ muốn nó tìm được theo danh mục"* *"như  cái mẫu có gửi nó chia các tag này mà muốn chia kĩ hơn, ví dụ phòng khách – phong cách gì"*

### 1.2 Phân tích hiện trạng hai trang tham khảo (trang mẫu do khách hàng đưa)

**Elemental Studio (elemental.com.vn)** – trang khách hàng đưa làm chuẩn thẩm mỹ:

| Khía cạnh | Hiện trạng | Nhận xét |
| :---- | :---- | :---- |
| Bộ lọc danh mục | Chứa 4 nhãn dẫn tới các trang khác nhau, một chiều: `All`, `Concept`, `Công trình Thực tế`, `Nổi bật`, `Studio` | Không lọc được theo phòng, phong cách, vật liệu, diện tích |
| Trang chi tiết dự án | Gần như chỉ là chuỗi ảnh \+ tiêu đề \+ nút share \+ mô tả  | Không có dữ liệu để SEO (search engine optimization), khách không tự đánh giá được sự phù hợp nếu chỉ đọc brief |
| Đặt tên dự án | `project no.08 The Fauvisim`, `project no.32 The Resonance` | Thẩm mỹ cao nhưng vô nghĩa với người tìm kiếm ("thiết kế chung cư 70m2 Scandinavian") |
| Nền tảng | WordPress \+ WPBakery | Khó mở rộng nghiệp vụ, khó gắn hệ thống tracking/AI |

**Nội Thất Sao Kim (noithatsaokim.vn)** – đối thủ mạnh về SEO:

- Phân loại theo **2 chiều**: loại công trình (chung cư / biệt thự / nhà phố / nhà liền kề) và loại phòng (khách / bếp / ngủ / trẻ em).  
- Phong cách (Scandinavian, Korea Chic, Wabi-sabi, Japanese, Hiện đại…) **chỉ nằm trong tiêu đề bài viết**, không phải là thuộc tính lọc được.  
- Hệ quả: khách muốn tìm *"phòng khách chung cư phong cách Wabi-sabi tông gỗ sáng dưới 800 triệu"* thì không có cách nào ngoài đọc thủ công từng bài.

### 1.3 Phát biểu vấn đề

> Thư viện thiết kế của công ty là dữ liệu **phi cấu trúc** (ảnh \+ văn bản mô tả tự do). Vì không được cấu trúc hóa, nó không thể: **(a)** tìm kiếm/lọc theo đúng cách khách hàng suy nghĩ, **(b)** cho công ty biết khách hàng đang thực sự thích cái gì, **(c)** được máy đọc để tự động tư vấn và gợi ý.  
>   
> Kết quả: đội kinh doanh phải tự xác nhận yêu cầu của khách qua tin nhắn trực tiếp đa nền tảng: Zalo; ban lãnh đạo ra quyết định về xu hướng thị trường dựa trên cảm tính.

### 1.4 Định vị lại quy mô dự án

Nếu chỉ làm "website giới thiệu \+ gallery" thì đây là bài tập CRUD, không đủ. Đề tài được nâng tầm theo **ba trục**, và ba trục này khóa vào nhau tạo thành một vòng lặp dữ liệu khép kín:

        \[1\] CẤU TRÚC HÓA DỮ LIỆU  
     Phân loại đa chiều \+ Auto-tagging AI (Tự động gán nhãn)  
                  |  
                  v  
        \[2\] KHAI THÁC NGHIỆP VỤ  
   Tìm kiếm, gợi ý, chatbot  
                  |  
                  v  
        \[3\] VÒNG LẶP PHẢN HỒI  
    Tracking hành vi khách hàng \-\> Phân tích xu hướng  
                  |  
                  \+----\> quay lại nuôi \[1\] và \[2\]

**Cách hiểu đơn giản:** thay vì coi website là một **quyển catalogue thông thường** (in ra là xong, ai xem cũng như nhau), ta coi nó là một **cửa hàng có nhân viên bán hàng**. Nhân viên đó biết phân loại hàng trên kệ (trục 1), biết tư vấn "anh thích bộ sofa này thì em có mấy mẫu tương tự" (trục 2), và cuối ngày biết báo cáo cho Boss "hôm nay 20 khách vào đều dừng lại ở góc Wabi-sabi" (trục 3).

Điểm đã được mở rộng: **website không chỉ là kênh trưng bày mà là một cảm biến (sensor) thu thập dữ liệu thị hiếu thiết kế**.

---

## 2\. PHẠM VI VÀ MỤC TIÊU DỰ ÁN

### 2.1 Mục tiêu kinh doanh (Business Objectives)

| ID | Mục tiêu | Chỉ số đo | Mục tiêu số |
| :---- | :---- | :---- | :---- |
| BO-01 | Tăng số lượng khách hàng tiềm năng (lead) từ kênh website | Số lượng khách hàng tiềm năng(lead)/tháng | Có sự tăng trưởng về khách hàng tiềm năng sau khi áp dụng |
| BO-02 | Rút ngắn thời gian tư vấn vòng đầu | Thời gian TB từ liên hệ → gửi được bộ ảnh phù hợp | Giảm thời gian tư vấn  |
| BO-03 | Giảm công sức quản trị nội dung | Thời gian đăng 1 dự án (30–50 ảnh) | Giảm thời gian thao tác đa nền tảng xuống nhiều nhất có thể |
| BO-04 | Có dữ liệu định lượng về xu hướng thị hiếu | Báo cáo xu hướng | Tự động, định kỳ hàng tuần |

### 2.2 Mục tiêu hệ thống (System Goals)

- **SG-01**: Cho phép lọc Danh mục theo tối thiểu **6 chiều đồng thời** (loại công trình, không gian, phong cách, tông màu, vật liệu, mức đầu tư).  
- **SG-02**: Tự động gợi ý nhãn (tag) cho ảnh mới tải lên với độ chính xác ≥ 85% ở các chiều chính.  
- **SG-03**: Cho phép tìm "dự án/không gian tương tự"từ tương tác của người dùng với các sản phẩm của công ty.  
- **SG-04**: Trợ lý ảo trả lời câu hỏi tư vấn dựa trên chính dữ liệu công ty (RAG), có dẫn nguồn.  
- **SG-05**: Ghi nhận và phân tích hành vi tương tác để phát hiện xu hướng.

### 2.3 Trong phạm vi / Ngoài phạm vi

| Trong phạm vi (In-scope) | Ngoài phạm vi (Out-of-scope) |
| :---- | :---- |
| Website public (portfolio, dịch vụ, blog, liên hệ) | Sàn thương mại điện tử bán đồ nội thất, thanh toán online |
| Hệ quản trị nội dung nội bộ (CMS) có phân quyền | Phần mềm quản lý thi công/công nợ/kế toán |
| Module AI: auto-tagging, tìm kiếm hình ảnh, RAG chatbot | Công cụ dựng 3D/render trên web, AR đặt đồ vào phòng thật |
| Hệ thống tracking \+ dashboard xu hướng | Ứng dụng di động native |

---

## 3\. XÁC ĐỊNH CÁC BÊN LIÊN QUAN (STAKEHOLDERS)

### 3.1 Danh sách đầy đủ

#### A. Nhóm nội bộ – Người ra quyết định

| ID | Vai trò | Mối quan tâm chính | Ảnh hưởng | Quan tâm | Chiến lược |
| :---- | :---- | :---- | :---- | :---- | :---- |
| SH-01 | **Giám đốc / Chủ doanh nghiệp** (Sponsor) | Chi phí, hình ảnh thương hiệu, số hợp đồng ký được, "web trông có sang không" | Cao | Cao | **Quản lý sát**. Họp duyệt từng mốc, luôn quy đổi tính năng ra tiền/lead |

#### B. Nhóm nội bộ – Người sử dụng hằng ngày

| ID | Vai trò | Mối quan tâm chính | Ảnh hưởng | Quan tâm | Chiến lược |
| :---- | :---- | :---- | :---- | :---- | :---- |
| SH-02 | **Nhân viên Marketing** | SEO, đăng bài, ảnh có mô tả để viết bài | TB | Cao | Giữ hài lòng |
| SH-03 | **Quản trị viên hệ thống** | Phân quyền, sao lưu, khôi phục | Thấp | TB | Thông báo |

#### C. Nhóm bên ngoài

| ID | Vai trò | Mối quan tâm chính | Ảnh hưởng | Quan tâm | Chiến lược |
| :---- | :---- | :---- | :---- | :---- | :---- |
| SH-04 | **Khách hàng cuối – Chủ nhà** (B2C) | Tìm được không gian đúng "gu", ước lượng chi phí, tin tưởng năng lực công ty | Thấp (cá nhân) / Cao (tập thể) | Cao | Khảo sát diện rộng \+ usability test |
| SH-05 | **Khách hàng doanh nghiệp** (chủ đầu tư, showroom, F\&B) | Năng lực triển khai quy mô lớn, hồ sơ năng lực | TB | TB | Phỏng vấn 1–2 đại diện |
| SH-06 | **Công cụ tìm kiếm (Google)** | Dữ liệu có cấu trúc, tốc độ tải, Core Web Vitals | Cao (gián tiếp) | — | Ràng buộc kỹ thuật: schema.org, sitemap, SSR |

### 3.3 Chân dung người dùng (Personas)

> Personas dùng để viết User Story ở tài liệu `03`.

**P1 — Chị Linh, 32 tuổi, "Người mua căn hộ đầu tiên"** Lưu 200 ảnh trên Pinterest nhưng **không gọi tên được phong cách mình thích**, chỉ biết "kiểu ấm ấm, nhiều gỗ, sáng sủa". Sợ bị hớ giá. Duyệt web bằng điện thoại lúc 22h–24h. → *Nhu cầu: lọc theo cảm giác/hình ảnh chứ không theo thuật ngữ; tham chiếu chi phí; xem được đúng dự án cùng tòa nhà.*

**P2 — Anh Dũng, 45 tuổi, "Chủ biệt thự"** Quan tâm **năng lực thực thi**: ảnh thực tế thi công có giống concept không, vật liệu dùng hãng nàoi. → *Nhu cầu: đối chiếu concept vs thực tế (before/after), hồ sơ năng lực, chi tiết vật liệu.*

**P3 — Bạn Mai, 26 tuổi, KTS của công ty** Mỗi tuần hoàn thành 1–2 concept, xuất 40–60 ảnh render. Hiện đăng bài bằng cách kéo ảnh vào WordPress và gõ tay tiêu đề. **Ghét việc gắn tag thủ công**, thường bỏ qua khiến dữ liệu thiếu. → *Nhu cầu: upload hàng loạt, AI gợi ý tag sẵn, chỉ cần bấm xác nhận.*

**P4 — Anh Sơn, 30 tuổi, Nhân viên tư vấn** Ngày chat với 20–30 khách qua Zalo/Messenger. Câu hỏi lặp lại: "báo giá chung cư 70m2?", "có mẫu Indochine không?", "làm bao lâu xong?". → *Nhu cầu: chatbot gánh vòng hỏi đầu; tra cứu ảnh mẫu bằng bộ lọc trong 10 giây; biết khách đã xem những gì trước khi nhắn.*

**P5 — Chị Hà, 38 tuổi, Giam doc** Cần biết tháng này khách hỏi nhiều về phong cách nào để phân bổ nhân sự thiết kế và đặt bài marketing. → *Nhu cầu: dashboard xu hướng, báo cáo tự động.*  
---

## 4\. KẾ HOẠCH THU THẬP YÊU CẦU (ELICITATION PLAN)

### 4.1 Lựa chọn kỹ thuật theo đối tượng

| Kỹ thuật | Áp dụng cho | Mục tiêu | Sản phẩm đầu ra |
| :---- | :---- | :---- | :---- |
| Bảng hỏi trực tuyến | SH-09 (mẫu ≥ 80\) | Hành vi tìm kiếm, thuật ngữ khách dùng, kỳ vọng chức năng | Thống kê định lượng |
| Quan sát tại chỗ (Observation) | SH-04, SH-06 | Xem thật cách họ đăng bài / tư vấn khách | Bản đồ quy trình AS-IS \+ điểm đau |
| Phân tích tài liệu | Toàn bộ mục 5 | Trích xuất luật nghiệp vụ, thuật ngữ, cấu trúc dữ liệu | Glossary \+ Business Rules |
| Đối sánh đối thủ (Benchmarking) | Trang trong & ngoài nước | Học nghiệp vụ hay, tránh lỗi phổ biến | Bảng so sánh chức năng |

---

## 5\. DANH MỤC CHỨC NĂNG & QUY TRÌNH NGHIỆP VỤ MỞ RỘNG

> Đây là phần trả lời trực tiếp cho yêu cầu "khai thác thêm chức năng, quy trình nghiệp vụ mới".

### 5.1 Bản đồ module

\+---------------------------------------------------------------+

|                    LỚP TRẢI NGHIỆM KHÁCH HÀNG                  |

|  M1 Danh mục đa chiều  |  M3 RAG Chatbot     |

|  M2 Chi tiết dự án      |  M4 Gợi ý             |

\+---------------------------------------------------------------+

|                    LỚP NGHIỆP VỤ NỘI BỘ                        |

|  M5 Quản trị nội dung & Quy trình xuất bản  |  M6 Quản lý thông tin Lead              |

|  M7 Thư viện vật liệu/sản phẩm                     |

|  M8 Quản trị người dùng & phân quyền                          |

\+---------------------------------------------------------------+

|                    LỚP DỮ LIỆU & TRÍ TUỆ                       |

|  M9 Auto-tagging AI  |  M10 Vector Index  |                   |

|  M12 Tracking hành vi |  M11 Phân tích xu hướng & Dashboard   |

\+---------------------------------------------------------------+

### 5.2 Mô tả module

#### M1 — Danh mục đa chiều (Multi-facet Portfolio)

Trái tim của hệ thống. Thay vì tag phẳng, mỗi **không gian** (không phải mỗi dự án) được gắn nhãn theo 10+ chiều độc lập (xem `05-Taxonomy`). Bộ lọc cho phép kết hợp chồng nhiều điều kiện, hiển thị số kết quả theo thời gian thực, và mỗi tổ hợp phổ biến sinh ra một URL riêng để SEO (ví dụ `/portfolio/phong-khach/chung-cu/wabi-sabi`).

**Điểm mấu chốt về mô hình dữ liệu:** một dự án biệt thự có phòng khách Indochine nhưng phòng ngủ trẻ em lại Scandinavian. Nếu gắn tag ở cấp dự án thì sai. → **Đơn vị gắn nhãn phải là `Space` (không gian), không phải `Project`.** Đây là quyết định thiết kế quan trọng nhất của toàn hệ thống.

#### M2 — Trang chi tiết dự án chuẩn hóa

Ngoài ảnh, bổ sung: bảng thông số (loại hình, diện tích, số phòng, thời gian thi công, mức đầu tư theo khoảng), thuyết minh ý tưởng, dải màu chủ đạo (color palette hiển thị trực quan), danh sách vật liệu chính, chế độ so sánh **Concept ↔ Thực tế** (slider before/after), và khối "Dự án tương tự".

#### M3 — Gợi ý tương tự

Ba luồng:

- **Món đồ → dịch vụ**: khách bấm vào sản phẩm "sofa module vải bố" → hiện các không gian khác dùng kiểu sofa tương tự \+ gói dịch vụ tương ứng. (Đây chính là kịch bản bạn đề xuất.)  
- **Văn bản → ảnh**: "phòng ngủ tông gỗ ấm có giường bọc nệm" — tìm được cả những ảnh không chứa đúng từ khóa đó, nhờ tìm kiếm ngữ nghĩa.

*Cơ sở kỹ thuật:* nhúng ảnh và văn bản vào cùng một không gian vector bằng mô hình đa phương thức. Kỹ thuật này biểu diễn ảnh thành các vector "dấu vân tay" sao cho ảnh giống nhau có vector gần nhau về mặt hình học, và vì embedding của ảnh và của câu chữ so sánh trực tiếp được với nhau, hệ thống có thể tìm ảnh theo mô tả kiểu "đồ nội thất Scandinavian tối giản" ngay cả khi ảnh không hề có từ khóa đó trong metadata.

#### M4 — RAG Chatbot tư vấn

Trợ lý trả lời dựa trên chính kho tri thức công ty (mô tả dự án, bảng giá, quy trình, FAQ, blog), **có dẫn chiếu nguồn và kèm ảnh dự án minh họa**. Điểm nâng cao so với chatbot thông thường:

- **Lọc theo metadata**: khi khách nói "em ở chung cư 70m2", hệ thống chỉ truy hồi trong các dự án có facet tương ứng.  
- **Trả lời đa phương thức**: câu trả lời kèm 3 ảnh dự án thật \+ link.  
- **Bàn giao cho người thật**: khi phát hiện ý định nghiêm túc (hỏi giá cụ thể, xin lịch hẹn) → tạo lead và chuyển cho sale, kèm toàn bộ ngữ cảnh hội thoại.  
- **Chống bịa đặt**: bắt buộc trả lời "em chưa có thông tin này, để em chuyển anh/chị cho KTS" khi độ tương đồng truy hồi dưới ngưỡng.

#### M5 — CMS & Quy trình xuất bản dự án (`QT-01`)

Luồng có trạng thái, có phân quyền:

KTS tải ảnh hàng loạt

   \-\> AI tự gợi ý tag \+ sinh mô tả nháp

   \-\> KTS xác nhận/sửa tag (Draft)

   \-\> Content biên tập lời \+ SEO (In Review)

   \-\> KTS trưởng duyệt chuyên môn (Approved)

   \-\> Kiểm tra quyền công bố ảnh khách hàng (Cleared)

   \-\> Xuất bản (Published)

   \-\> Theo dõi hiệu quả sau 30 ngày

#### M6 — Quản lý Lead (`QT-02`)

Vòng đời: `Mới → Đã liên hệ → Đủ điều kiện → Đã hẹn khảo sát → Đã báo giá → Ký HĐ / Thất bại`. Điểm khác biệt: **chấm điểm lead dựa trên hành vi**. Một người xem 15 ảnh biệt thự, lưu 8 ảnh vào moodboard và mở trang bảng giá 3 lần thì có giá trị hơn nhiều một người chỉ điền form. Màn hình chi tiết lead hiển thị "dấu chân" của khách: đã xem gì, thích phong cách nào — sale mở lời trúng đích ngay từ câu đầu.

#### M7 Thư viện vật liệu/sản phẩm \+ Hotspot (`QT-07`)

Mỗi ảnh có thể gắn các điểm nóng (giống thẻ sản phẩm trên Instagram) trỏ tới bản ghi món đồ: `sofa module vải bố xám`, `đèn thả thủy tinh khói`. AI phát hiện vật thể để **gợi ý sẵn vị trí hotspot**, người dùng chỉ xác nhận. Đây là hạ tầng bắt buộc để kịch bản "*tôi thích kiểu sofa A*" hoạt động được.

#### M8 — Quản trị người dùng & phân quyền

Vai trò: `Khách vãng lai`, `Khách đăng ký`, `KTS`, `Content`, `Sale`, `KTS trưởng`, `Quản trị`. Có nhật ký thao tác (audit log).

#### M9 — Auto-tagging AI (`AI-01→AI-03`)

- Phân loại zero-shot theo cây facet trong `05-Taxonomy` (không cần dữ liệu huấn luyện lớn).  
- Trích xuất dải màu chủ đạo bằng phân cụm màu điểm ảnh → tự động gắn facet tông màu.  
- Phát hiện vật thể nội thất → gợi ý hotspot.  
- Sinh mô tả nháp \+ alt text cho SEO.  
- **Luôn có người kiểm duyệt (human-in-the-loop)**: AI đề xuất, KTS bấm duyệt. Không bao giờ tự động xuất bản.

#### M10 — Vector Index

Lưu embedding của ảnh và của mô tả; hỗ trợ tìm kiếm lai (vector \+ lọc theo metadata facet).

#### M11 — Thu thập hành vi (`QT-06`)

Sự kiện được ghi nhận: `xem_trang`, `xem_dự_án`, `phóng_to_ảnh`, `chuyển_ảnh`, `áp_dụng_bộ_lọc`, `bấm_hotspot`, `lưu_moodboard`, `chia_sẻ`, `nhắn_chatbot`, `bấm_CTA`, `gửi_form`. Mỗi sự kiện gắn kèm **các giá trị facet của nội dung đang xem** — đây là mấu chốt để quy đổi hành vi thành thị hiếu thiết kế.

#### M12 — Phân tích xu hướng & Dashboard (`AI-07`)

Tính **Điểm quan tâm** cho từng giá trị facet theo tuần:

InterestScore(f, t) \= w1\*luot\_xem

                    \+ w2\*thoi\_gian\_dung\_chuan\_hoa

                    \+ w3\*luot\_luu\_moodboard

                    \+ w4\*luot\_chia\_se

                    \+ w5\*so\_lead\_phat\_sinh\_tu\_facet\_do

Phát hiện xu hướng: `Trend(f,t) = (IS_t − MA4(IS)) / MA4(IS)`; nếu vượt ngưỡng (ví dụ \+30% trong 4 tuần liên tiếp) thì cảnh báo.

Đầu ra thực tế cho SH-01/SH-05:

> *"4 tuần qua, quan tâm tới Wabi-sabi cho phòng khách chung cư tăng 42%; tông gỗ óc chó giảm 15%. Đề xuất: sản xuất 2 concept Wabi-sabi cho căn 2PN, đặt bài SEO 'thiết kế chung cư Wabi-sabi'."*

Ngoài ra: gom cụm phiên truy cập để phát hiện **chân dung thị hiếu mới** (ví dụ nhóm khách luôn xem đồng thời Japandi \+ phòng trẻ em \+ căn hộ \< 70m² → một phân khúc chưa có sản phẩm phục vụ).  
---

## 7\. YÊU CẦU PHI CHỨC NĂNG

| ID | Loại | Yêu cầu | Cách đo |
| :---- | :---- | :---- | :---- |
| NFR-01 | Hiệu năng | LCP \< 2.5s trên 4G; áp dụng bộ lọc phản hồi \< 500ms | PageSpeed Insights, log server |
| NFR-02 | Hiệu năng | Tìm kiếm vector trên 10.000 ảnh trả kết quả \< 1s | Kiểm thử tải |
| NFR-03 | Khả năng mở rộng | Chịu được 50.000 ảnh, 100 người dùng đồng thời | Kiểm thử tải |
| NFR-04 | Hình thức | **Ảnh hiển thị đúng màu (giữ ICC profile), không nén vỡ**, tỷ lệ khung không bị méo | Duyệt bởi SH-03 |
| NFR-05 | Hình thức | Giao diện tối giản, ảnh là nhân vật chính, không quá 2 font chữ | Duyệt bởi SH-01, SH-03 |
| NFR-06 | Tương thích | Chuẩn mobile-first; hoạt động tốt trên Safari iOS, Chrome Android | Kiểm thử đa thiết bị |
| NFR-07 | SEO | Kết xuất phía máy chủ; có schema.org; mỗi tổ hợp facet chính có URL riêng | Google Search Console |
| NFR-08 | Bảo mật | Phân quyền theo vai trò; chống tải ảnh độc hại; giới hạn tần suất gọi API AI | Kiểm thử thâm nhập cơ bản |
| NFR-09 | Riêng tư | Banner đồng ý cookie; ẩn danh dữ liệu hành vi; tuân thủ NĐ 13/2023 | Rà soát pháp lý |
| NFR-10 | Chất lượng AI | Auto-tagging: độ chính xác ≥ 85% ở facet Phong cách và Không gian | Đối chiếu tập kiểm thử 300 ảnh |
| NFR-11 | Chất lượng AI | Gợi ý "tương tự": precision@5 ≥ 0.7 theo đánh giá của KTS | Đánh giá thủ công 50 truy vấn |
| NFR-12 | Khả dụng | Người quản trị đăng 1 dự án 40 ảnh trong \< 20 phút | Đo thời gian thực tế |
| NFR-13 | Bảo trì | Thêm một phong cách mới vào taxonomy không cần sửa mã nguồn | Kiểm thử cấu hình |

