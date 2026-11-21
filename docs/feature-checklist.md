# D3 Studio: feature checklist

Tick each box once you have seen the feature work in the browser. UC numbers follow the use-case diagrams in `docs/diagrams/project 1/Use case diagram/`.

## Before you start

- [X] Docker is running: `docker compose up -d`. The site is at http://localhost:8080/prj1/
- [X] An admin account exists. Register at `/dang-nhap`, then run `docker compose exec backend python set_role.py <tranxuantuan1522005@gmail.com> admin`
- [x] One test account per role, set at `/quan-tri/tai-khoan`: architect, lead_architect, content, sales
- [ ] Email: without `D3_SMTP_*` in `backend/.env`, emails (password reset, invites, lead notices, the weekly report) are only written to the log. Read them with `docker compose logs backend | grep -i mail`

Who can open which admin pages:
- **architect**: `/quan-tri`, `/quan-tri/mon-do`, `/quan-tri/hieu-qua`
- **lead_architect**: all architect pages, plus `/quan-tri/phan-loai`, `/quan-tri/tri-thuc`, `/quan-tri/xu-huong`, `/khach-hang`
- **content**: `/quan-tri` (caption and alt text only), `/quan-tri/tri-thuc`, `/quan-tri/hoi-thoai`
- **sales**: `/quan-tri/xu-huong`, `/quan-tri/hieu-qua`, `/quan-tri/hoi-thoai`, `/khach-hang`
- **admin**: everything, including `/quan-tri/tai-khoan`

---

## 1. Accounts and sign-in

- [X] **Sign up with email.** On `/dang-nhap`, choose "Chưa có tài khoản? Đăng ký" and enter a full name, email and password. You end up signed in, with your name shown.
- [X] **Sign in with email.** A wrong password says "Sai email hoặc mật khẩu."; the right one signs you in.
- [X] **Google sign-in.** "Tiếp tục với Google", pick your account, and you are back on the site signed in. Only test users added in Google Cloud can sign in while the app is in Testing.
- [X] **Facebook sign-in.** "Tiếp tục với Facebook", log in, and you are back on the site signed in. Still unchecked: if you see "URL Blocked" or "App not active", the Meta app's settings need fixing.
- [X] **Forgot password.** At `/quen-mat-khau`, enter your email. Open the link from the email (or the log) at `/dat-mat-khau`, set a new password, then sign in with it.
- [X] **Change your own name.** While signed in, open `/dang-nhap` (your account page) and change your full name. Check that it is kept after a reload.
- [X] **Locked account.** An admin locks an account at `/quan-tri/tai-khoan`. That account can no longer sign in, including with Google or Facebook, and is told why.

## 2. Visitor: browsing (usecase-1)

- [X] **UC01: Filter spaces.** At `/khong-gian`, pick room type + style + colour. The list narrows, the counts change, and a reload keeps the filters and sort order (they are in the URL).
- [?] **UC01: Filter projects.** Waiting on Tùng to place `ProjectFilter.vue` on a page; until then it cannot be tested in the UI.
- [?] **UC02: Project detail.** Click a project on `/du-an`. `/du-an/<slug>` shows photos, details and the project's spaces.
- [ ] **UC03: Similar spaces.** Open any `/khong-gian/<id>`. The similar-spaces row shows matches, each with a reason (shared labels).
- [X] **UC04: Search with a photo.** On `/khong-gian`, upload a room photo: you get results plus its detected style and tone.
- [?] **UC04: Not a room.** Upload a photo of a cat or a car: the interior check turns it away with a message.
- [X] **UC05: Search with words.** Type "phòng khách hiện đại tông ấm". The room type and style become filters, and the note under the search explains why.
- [X] **UC05: Weak results.** A vague query gives a hint on how to reword it.
- [X] **UC06: Style quiz.** Finish `/trac-nghiem`. The result shows your style and suggested projects.
- [?] **Home page.** It shows trending spaces and the home suggestions chosen by staff.

## 3. Visitor: interacting (usecase-1)

- [X] **UC07: Save while signed out.** Click a heart on a space: you are invited to sign up.
- [X] **UC07: Save while signed in.** Click a heart: the photo appears in `/bo-suu-tap`, and the counter in the header goes up.
- [X] **Share a collection.** In `/bo-suu-tap`, click share and open the link in a private window. `/bo-suu-tap/xem/<code>` shows a read-only copy.
- [X] **UC08: Collection as a brief.** Send the brief form from `/bo-suu-tap`. As sales, the lead appears at `/khach-hang` with the photos.
- [X] **UC09: Assistant answers.** Open the "Hỏi trợ lý" chat and ask about a style or a project. It answers from the studio's own content.
- [X] **UC09: Off-topic.** Ask about something unrelated (politics, homework). It politely declines.
- [X] **UC09: No prices.** Ask "bao nhiêu tiền?". It gives no amount, offers a call-back, and a lead is created.
- [X] **UC10: Cost estimate (removed).** Price estimates were removed at Tùng's request: `/uoc-tinh` should go to `/lien-he`.
- [X] **UC11: Contact form.** Send the form at `/lien-he`. The lead appears at `/khach-hang`.
- [X] **Outside working hours.** A lead sent outside working hours (`D3_GIO_LAM_VIEC`) is told when the studio will get in touch.

## 4. Visitor: privacy and tracking (UC21, act-7)

- [ ] **Consent banner.** On the first visit you see "Đồng ý / Từ chối / Tùy chỉnh". "Tùy chỉnh" offers analysis only.
- [ ] **Accept.** Browse, zoom a photo, swipe photos, click a hotspot. The next day (after the nightly rollup), these show in `/quan-tri/xu-huong`.
- [ ] **Decline.** After "Từ chối", the browser's Network tab shows no calls to `/api/events` other than a plain page count.
- [ ] **Forget me.** The banner settings have a "forget me" option; after using it, your device's data is deleted.

## 5. Architect / lead architect (usecase-2)

- [ ] **UC12: Bulk upload.** In `/quan-tri`, upload several photos and one PDF. The answer comes at once, the PDF is refused, and each photo goes processing → done (or error).
- [ ] **UC25: AI labels.** An uploaded photo arrives with the AI's room type, style and confidence.
- [ ] **UC26: Draft text.** An uploaded photo arrives with a caption and alt text already written.
- [ ] **UC13: Label a space.** Open a draft and change its room type or style. It saves, and the correction is recorded for the accuracy check (see section 8).
- [ ] **UC17: Hotspots by hand.** Open the hotspot editor on a space, place a point and link an item. The point shows on `/khong-gian/<id>`.
- [ ] **UC17: AI hotspots.** Click "AI gợi ý vật thể": suggested points appear. Accept one and it is saved as an AI point with its confidence.
- [ ] **Item price range.** At `/quan-tri/mon-do`, the price range is visible to staff only and never on the public pages.
- [ ] **UC14: Publish blocked.** Try to publish a space with required fields missing: it is blocked, with the missing fields named.
- [ ] **UC14: Publish.** Move a space draft → editing → published. It appears on the public site with a publish date, and the hand-over notice is sent (in the email or the log).
- [ ] **Take down.** Take a published space down: it disappears from the site and the assistant stops using it.
- [ ] **Project fields.** A project shows its development name, construction days and status.
- [ ] **UC15: Taxonomy.** As lead_architect, at `/quan-tri/phan-loai`, add a value, rename one, and merge two values. The photos using the merged value get their descriptions refreshed.
- [ ] **Value suggestions.** `/quan-tri/phan-loai` shows suggested new values and dimensions. Accept one and reject one.

## 6. Content staff (usecase-3)

- [ ] **UC14 (content).** As content, at `/quan-tri`, you can edit only caption and alt text, not labels.
- [ ] **UC16: Add knowledge.** At `/quan-tri/tri-thuc`, add an entry and set it to active. Ask the chat about it: the answer uses it.
- [ ] **UC16: Price in knowledge.** Add an entry that states a price. The chat never says the amount.
- [ ] **UC16: Knowledge gaps.** Questions the assistant could not answer are listed at `/quan-tri/tri-thuc`. Dismiss one.
- [ ] **Forbidden topics.** At `/quan-tri/tri-thuc`, add a forbidden topic and use "try" to test a sentence against it.
- [ ] **Conversations.** `/quan-tri/hoi-thoai` lists the chats.

## 7. Sales (usecase-4)

- [ ] **Leads list.** `/khach-hang` lists leads from the brief, the chat and the contact form, each with its visitor behaviour.
- [ ] **UC22: Trends dashboard.** `/quan-tri/xu-huong` shows trending spaces, taste groups and behaviour charts.
- [ ] **Project performance.** `/quan-tri/hieu-qua` shows views and saves per project.
- [ ] **Home suggestions.** In `/quan-tri/xu-huong`, change the home suggestions; the home page shows them.
- [ ] **UC23: Weekly report.** In the weekly-report panel, preview the report and send a test. It sends itself on Mondays from 08:00 when `D3_WEEKLY_REPORT` is on.
- [ ] **SMS.** With `D3_SMS_URL` and `D3_SMS_TOKEN` set, a lead with a phone number gets an SMS confirmation, and the log shows the number masked. Not configured yet.

## 8. Admin and the system (usecase-5)

- [ ] **UC24: Invite.** At `/quan-tri/tai-khoan`, invite an email with a role and a full name. The invite link (in the email or the log) lets them set a password.
- [ ] **UC24: Resend and cancel.** Resend an invite, then cancel one.
- [ ] **UC24: Change role.** Change a user's role. On their next request, their menu and pages change.
- [ ] **UC24: Lock and unlock.** Lock a user (they can't sign in), then unlock them.
- [ ] **UC24: Role guard.** Signed in as each role, typing another role's admin URL sends you back to `/`.
- [ ] **UC25: Label accuracy (no UI).** After correcting some labels in `/quan-tri`, run `docker compose exec backend python eval_labels.py`. It prints the AI's accuracy against the human labels.
- [ ] **UC27: Vector index.** After publishing a new space or merging a taxonomy value, similar-space search and the assistant pick up the change within a minute.
- [ ] **Nightly analytics.** After 01:00 (UTC+7), `/quan-tri/xu-huong` shows the previous day's numbers.
- [ ] **Sitemap.** http://localhost:8080/prj1/sitemap.xml lists the published projects and spaces, without `/uoc-tinh`.

## 9. Phone layout

- [ ] At 375px width (DevTools → device toolbar), check the home page, `/khong-gian`, a space page, the chat and `/bo-suu-tap`: no sideways scrolling, and everything can be tapped.
