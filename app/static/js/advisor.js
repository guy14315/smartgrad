    let advisor, students = [], selected;
    const api = '/api/advisors';

    function showError(id, text) {
      const el = document.getElementById(id);
      el.textContent = text;
      el.classList.remove('hidden');
    }

    function showDashboard() {
      document.getElementById('login-view').classList.add('hidden');
      document.getElementById('dashboard-view').classList.remove('hidden');
      document.getElementById('logout').classList.remove('hidden');
    }

    async function login(e) {
      e.preventDefault();
      const btn = document.getElementById('login-btn');
      btn.disabled = true;
      document.getElementById('login-error').classList.add('hidden');
      try {
        advisor = await requestJson(api + '/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            advisor_id: document.getElementById('advisor-id').value.trim(),
            password: document.getElementById('password').value,
          }),
        });
        await loadDashboard();
        showDashboard();
      } catch (err) {
        showError('login-error', err.message || 'เกิดข้อผิดพลาด');
      } finally {
        btn.disabled = false;
      }
    }

    async function loadDashboard() {
      const [list, ready] = await Promise.all([
        requestJson(`${api}/${advisor.advisor_id}/students`),
        requestJson(`${api}/${advisor.advisor_id}/ready-to-graduate`),
      ]);
      students = list.students;
      document.getElementById('welcome').textContent = `ภาพรวมนักศึกษา: ${advisor.name}`;
      document.getElementById('student-count').textContent = list.total;
      document.getElementById('graduate-count').textContent = ready.total + ' คน';
      renderStudents(students);
    }

    function renderStudents(items) {
      const container = document.getElementById('student-table');
      if (!items.length) {
        container.innerHTML = '<div class="empty">ยังไม่มีนักศึกษาที่อัปโหลด Transcript</div>';
        return;
      }
      container.innerHTML = `<table><thead><tr><th>รหัสนักศึกษา</th><th>ชื่อ</th><th>หน่วยกิตผ่าน</th><th>อัปโหลดล่าสุด</th></tr></thead><tbody>${items.map(s => `<tr onclick="selectStudent(${jsArg(s.student_id)})"><td>${escapeHtml(s.student_id)}</td><td>${escapeHtml(s.name)}</td><td><span class="pill">${escapeHtml(s.passed_credits)} นก.</span></td><td>${new Date(s.last_uploaded_at).toLocaleString('th-TH')}</td></tr>`).join('')}</tbody></table>`;
    }

    function filterStudents() {
      const term = document.getElementById('search').value.trim().toLowerCase();
      renderStudents(students.filter(s => s.student_id.includes(term) || s.name.toLowerCase().includes(term)));
    }

    async function selectStudent(id) {
      selected = students.find(s => s.student_id === id);
      const data = await requestJson(`${api}/${advisor.advisor_id}/students/${id}`);
      document.getElementById('student-detail').classList.remove('hidden');
      document.getElementById('upload-date').textContent = 'อัปโหลดล่าสุด: ' + new Date(data.transcript_uploaded_at).toLocaleString('th-TH');

      const fCourses = data.f_courses || [];
      const passedCourses = data.passed_courses || [];

      const fHtml = fCourses.length ? `
        <h3 style="color:#b91c1c; margin:20px 0 10px; display:flex; align-items:center; gap:8px;">
          <span>วิชาที่ติด F (${escapeHtml(data.f_count)} วิชา)</span>
        </h3>
        ${fCourses.map(c => `
          <div class="course" style="align-items:flex-start; padding:10px 0;">
            <div>
              <div>
                <b>${escapeHtml(c.code)}</b> · ${escapeHtml(c.name)} <span class="muted">(${escapeHtml(c.credit)} นก.)</span>
                <b style="color:#b91c1c; margin-left:6px;">[${escapeHtml(c.grade)}]</b>
              </div>
              <div style="margin-top:4px; font-size:12px; display:flex; flex-wrap:wrap; gap:6px;">
                ${c.is_core ? `<span style="background:#fee2e2; color:#991b1b; padding:2px 8px; border-radius:4px; font-weight:600;">[วิชาหลักตามแผน] ${escapeHtml(c.category_label || '')} ${c.plan_text ? `(${escapeHtml(c.plan_text)})` : ''}</span>` : (c.category_label ? `<span style="background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:4px;">${escapeHtml(c.category_label)} ${c.plan_text ? `(${escapeHtml(c.plan_text)})` : ''}</span>` : '')}
                ${c.is_retaken_passed ? `<span style="background:#f1f5f9; color:#334155; border:1px solid #cbd5e1; padding:2px 8px; border-radius:4px; font-weight:600;">ลงเรียนใหม่และผ่านแล้ว</span>` : `<span style="background:#fef2f2; color:#b91c1c; padding:2px 8px; border-radius:4px; font-weight:600;">ยังไม่ผ่านใน Transcript</span>`}
              </div>
            </div>
            <span style="font-size:12px; color:#64748b; white-space:nowrap;">${escapeHtml(c.academic_year || '')} ${c.semester ? `เทอม ${escapeHtml(c.semester)}` : ''}</span>
          </div>
        `).join('')}
      ` : '';

      const passedHtml = `
        <h3 style="color:var(--navy); margin:20px 0 10px;">รายวิชาที่ผ่าน (${passedCourses.length} วิชา)</h3>
        ${passedCourses.length ? passedCourses.map(c => `
          <div class="course">
            <span><b>${escapeHtml(c.code)}</b> · ${escapeHtml(c.name)} <span class="muted">(${escapeHtml(c.credit)} นก.)</span></span>
            <b style="color:var(--navy);">${escapeHtml(c.grade)}</b>
          </div>
        `).join('') : '<p class="muted">ไม่มีข้อมูล</p>'}
      `;

      document.getElementById('report').innerHTML = `
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
          <div style="font-size:16px; font-weight:600; margin-bottom:8px;">${escapeHtml(data.student_id)} ${escapeHtml(data.name)}</div>
          <div style="display:flex; flex-wrap:wrap; gap:8px; font-size:13px; align-items:center;">
            <span class="pill" style="font-size:13px; padding:4px 10px;">ผ่านแล้ว ${escapeHtml(data.passed_credits)} นก.</span>
            <span style="background:${data.f_count ? '#fef2f2' : '#f8fafc'}; color:${data.f_count ? '#b91c1c' : '#64748b'}; border:1px solid ${data.f_count ? '#fca5a5' : '#e2e8f0'}; border-radius:999px; padding:3px 10px; font-weight:600;">
              ติด F: ${escapeHtml(data.f_count)} วิชา
            </span>
          </div>
        </div>
        ${fHtml}
        ${passedHtml}
      `;

      document.getElementById('note-area').className = '';
      document.getElementById('note-area').innerHTML = `<div style="padding:18px"><p><b>${escapeHtml(selected.student_id)} ${escapeHtml(selected.name)}</b></p><p class="muted">ผู้รับ: ${escapeHtml(selected.student_id)}@kmitl.ac.th</p><form onsubmit="sendNote(event)"><label>หัวข้อ</label><input id="note-subject" required value="คำแนะนำการวางแผนการเรียน"><label>คำแนะนำ</label><textarea id="note-message" required placeholder="พิมพ์คำแนะนำสำหรับนักศึกษา"></textarea><button id="send-btn" style="margin-top:16px">เปิด Gmail เพื่อส่งคำแนะนำ</button><p id="note-result" class="hidden"></p></form></div>`;
      window.scrollTo({top: document.getElementById('student-detail').offsetTop - 20, behavior: 'smooth'});
    }
    function sendNote(e) {
      e.preventDefault();
      const subject = encodeURIComponent(document.getElementById('note-subject').value);
      const message = encodeURIComponent(document.getElementById('note-message').value);
      const to = encodeURIComponent(`${selected.student_id}@kmitl.ac.th`);
      const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${subject}&body=${message}`;
      window.open(gmailUrl, '_blank');
      const result = document.getElementById('note-result');
      result.className = 'success';
      result.textContent = `เปิดหน้าต่าง Gmail พร้อมข้อมูลสำหรับส่งแล้ว`;
      result.classList.remove('hidden');
    }

    async function logout() {
      await requestJson(api + '/logout', { method: 'POST' });
      location.reload();
    }

    (async () => {
      try {
        advisor = await requestJson(api + '/me');
        await loadDashboard();
        showDashboard();
      } catch (_) {}
    })();
