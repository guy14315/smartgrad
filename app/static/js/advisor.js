let advisor, students = [], selected, currentDetail = null, groupByCategory = false;
const api = '/api/advisors';

// สร้าง progress bar: แถบสี = ผ่านแล้ว, แถบเทา (เหมือนปุ่ม disable) = กำลังเรียน
// catKey ใช้กำหนดสีผ่าน [data-cat] ใน advisor.css
function progressBarHtml({ label, passed, inProgress = 0, target, catKey = '', large = false }) {
    const t = Number(target) || 0;
    const pas = Number(passed) || 0;
    const ip = Number(inProgress) || 0;
    const passedPct = t > 0 ? Math.min(100, (pas / t) * 100) : 0;
    const ipPct = t > 0 ? Math.min(100 - passedPct, (ip / t) * 100) : 0;
    const round1 = n => Math.round(n * 10) / 10;
    const done = t > 0 && pas >= t;
    return `
      <div class="adv-bar" data-cat="${escapeHtml(catKey)}">
        <div class="adv-bar-top">
          <span>${escapeHtml(label)}</span>
          <strong class="${done ? 'done' : ''}">${escapeHtml(pas)} / ${escapeHtml(t)} นก. (${escapeHtml(round1(passedPct))}%)</strong>
        </div>
        <div class="adv-track ${large ? 'lg' : ''}">
          <div class="adv-fill" data-w="${passedPct}%"></div>
          <div class="adv-fill ip" data-w="${ipPct}%"></div>
        </div>
        ${ip > 0 ? `<div class="adv-bar-sub"><span class="adv-dot"></span>กำลังเรียน ${escapeHtml(ip)} นก. (ยังไม่นับรวมในแถบสี)</div>` : ''}
      </div>`;
}

function animateBars(root) {
    setTimeout(() => {
        (root || document).querySelectorAll('.adv-fill').forEach(el => {
            el.style.width = el.getAttribute('data-w');
        });
    }, 50);
}

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
    const [list, ready, summary] = await Promise.all([
        requestJson(`${api}/${advisor.advisor_id}/students`),
        requestJson(`${api}/${advisor.advisor_id}/ready-to-graduate`),
        requestJson(`${api}/${advisor.advisor_id}/summary`),
    ]);
    students = list.students;
    document.getElementById('welcome').textContent = `ภาพรวมนักศึกษา: ${advisor.name}`;
    document.getElementById('total-students').textContent = summary.total_students + ' คน';
    document.getElementById('student-count').textContent = summary.students_with_transcript + ' คน';
    document.getElementById('avg-credits').textContent = summary.average_passed_credits + ' นก.';
    document.getElementById('graduate-count').textContent = ready.total + ' คน';
    renderStudents(students);
}

function renderStudents(items) {
    const container = document.getElementById('student-table');
    if (!items.length) {
        container.innerHTML = '<div class="empty">ยังไม่มีนักศึกษาที่อัปโหลด Transcript</div>';
        return;
    }
    container.innerHTML = `<table><thead><tr><th>รหัสนักศึกษา</th><th>ชื่อ</th><th>หน่วยกิตผ่าน</th><th>อัปโหลดล่าสุด</th></tr></thead><tbody>${items.map(s => `<tr onclick="selectStudent(${jsArg(s.student_id)})"><td>${escapeHtml(s.student_id)}</td><td>${escapeHtml(s.name)}</td><td><span class="pill">${escapeHtml(s.passed_credits)} / ${escapeHtml(s.max_credits)} นก.</span></td><td>${escapeHtml(formatThaiDateTime(s.last_uploaded_at))}</td></tr>`).join('')}</tbody></table>`;
}

function filterStudents() {
    const term = document.getElementById('search').value.trim().toLowerCase();
    renderStudents(students.filter(s => s.student_id.includes(term) || s.name.toLowerCase().includes(term)));
}

function courseRowHtml(c) {
    const ip = !!c.in_progress;
    return `
      <div class="course${ip ? ' is-ip' : ''}">
        <div>
          <span class="course-text"><b>${escapeHtml(c.code)}</b> · ${escapeHtml(c.name)} <span class="muted">(${escapeHtml(c.credit)} นก.)</span></span>
          ${c.category_label ? `<div class="course-cat"><span class="tag tag-cat">${escapeHtml(c.category_label)}</span></div>` : ''}
        </div>
        ${ip
            ? `<span class="tag tag-ip">กำลังเรียน</span>`
            : `<b class="course-grade">${escapeHtml(c.grade)}</b>`}
      </div>`;
}

function renderPassedCourses() {
    const box = document.getElementById('passed-courses');
    if (!box || !currentDetail) return;
    const courses = currentDetail.passed_courses || [];
    const progress = currentDetail.progress;
    const inProgress = ((progress && progress.in_progress) || []).map(c => ({ ...c, in_progress: true }));
    if (!courses.length && !inProgress.length) {
        box.innerHTML = '<p class="muted">ไม่มีข้อมูล</p>';
        return;
    }

    const sumCredits = items => items.reduce((sum, c) => sum + (Number(c.credit) || 0), 0);

    if (!groupByCategory) {
        let html = courses.map(courseRowHtml).join('');
        if (inProgress.length) {
            html += `
              <div class="ip-title">
                กำลังเรียน <small class="muted">(${inProgress.length} วิชา · ${sumCredits(inProgress)} นก.)</small>
              </div>
              ${inProgress.map(courseRowHtml).join('')}`;
        }
        box.innerHTML = html;
        return;
    }

    const cats = (progress && progress.categories) || [];
    const catByKey = Object.fromEntries(cats.map(c => [c.key, c]));

    // จัดวิชาเข้าหมวด: ถ้าตรงกับหมวดใน dashboard ใช้ key, ไม่ตรงใช้ label
    const groups = {};
    const others = {};
    [...courses, ...inProgress].forEach(c => {
        if (c.category && catByKey[c.category]) {
            (groups[c.category] = groups[c.category] || []).push(c);
        } else {
            const label = c.category_label || 'ไม่ระบุหมวดหมู่';
            (others[label] = others[label] || []).push(c);
        }
    });

    const groupHeader = (label, items, barHtml) => {
        const passedItems = items.filter(c => !c.in_progress);
        const ipItems = items.filter(c => c.in_progress);
        return `
          <div class="group-head">
            ${barHtml || `<div class="group-title">${escapeHtml(label)}</div>`}
            <div class="muted group-sub">ผ่าน ${passedItems.length} วิชา · ${sumCredits(passedItems)} นก.${ipItems.length ? ` | กำลังเรียน ${ipItems.length} วิชา · ${sumCredits(ipItems)} นก.` : ''}</div>
          </div>`;
    };

    // หมวดตามหลักสูตร (แสดงทุกหมวด แม้ยังไม่มีวิชา) ตามด้วยหมวดอื่นๆ
    let html = cats.map(cat => {
        const items = groups[cat.key] || [];
        const bar = progressBarHtml({
            label: cat.label,
            passed: cat.passed_credits ?? cat.earned_credits,
            inProgress: cat.in_progress_credits || 0,
            target: cat.target_credits,
            catKey: cat.key,
        });
        return groupHeader(cat.label, items, bar)
            + (items.length ? items.map(courseRowHtml).join('') : '<p class="muted empty-note">ยังไม่มีวิชาในหมวดนี้</p>');
    }).join('');

    const otherKeys = Object.keys(others).sort((a, b) => {
        if (a === 'ไม่ระบุหมวดหมู่') return 1;   // ไว้ท้ายสุด
        if (b === 'ไม่ระบุหมวดหมู่') return -1;
        return a.localeCompare(b, 'th');
    });
    html += otherKeys.map(label => groupHeader(label, others[label]) + others[label].map(courseRowHtml).join('')).join('');

    box.innerHTML = html;
    animateBars(box);
}

function toggleCategorySort() {
    groupByCategory = !groupByCategory;
    const btn = document.getElementById('sort-category-btn');
    if (btn) {
        btn.textContent = groupByCategory ? 'ยกเลิกการเรียงตามหมวดหมู่' : 'เรียงตามหมวดหมู่';
        btn.classList.toggle('active', groupByCategory);
    }
    renderPassedCourses();
}

async function selectStudent(id) {
    selected = students.find(s => s.student_id === id);
    const data = await requestJson(`${api}/${advisor.advisor_id}/students/${id}`);
    currentDetail = data;
    groupByCategory = false
    document.getElementById('student-detail').classList.remove('hidden');
    document.getElementById('upload-date').textContent = 'อัปโหลดล่าสุด: ' + formatThaiDateTime(data.transcript_uploaded_at);

    const fCourses = data.f_courses || [];
    const passedCourses = data.passed_courses || [];

    const fHtml = fCourses.length ? `
        <h3 class="f-title">
          <span>วิชาที่ติด F (${escapeHtml(data.f_count)} วิชา)</span>
        </h3>
        ${fCourses.map(c => `
          <div class="course f-course">
            <div>
              <div>
                <b>${escapeHtml(c.code)}</b> · ${escapeHtml(c.name)} <span class="muted">(${escapeHtml(c.credit)} นก.)</span>
                <b class="course-grade f">[${escapeHtml(c.grade)}]</b>
              </div>
              <div class="course-tags">
                ${c.is_core ? `<span class="tag tag-core">[วิชาหลักตามแผน] ${escapeHtml(c.category_label || '')} ${c.plan_text ? `(${escapeHtml(c.plan_text)})` : ''}</span>` : (c.category_label ? `<span class="tag tag-cat">${escapeHtml(c.category_label)} ${c.plan_text ? `(${escapeHtml(c.plan_text)})` : ''}</span>` : '')}
                ${c.is_retaken_passed ? `<span class="tag tag-retaken">ลงเรียนใหม่และผ่านแล้ว</span>` : `<span class="tag tag-unpassed">ยังไม่ผ่านใน Transcript</span>`}
              </div>
            </div>
            <span class="course-term">${escapeHtml(c.academic_year || '')} ${c.semester ? `เทอม ${escapeHtml(c.semester)}` : ''}</span>
          </div>
        `).join('')}
      ` : '';

    const passedHtml = `
    <div class="list-head">
      <h3 class="list-title">รายวิชาที่ผ่าน (${passedCourses.length} วิชา)</h3>
      <button type="button" id="sort-category-btn" class="btn-sort" onclick="toggleCategorySort()">
        ${groupByCategory ? 'ยกเลิกการเรียงตามหมวดหมู่' : 'เรียงตามหมวดหมู่'}
      </button>
    </div>
    <div id="passed-courses"></div>
    `;

    const p = data.progress;
    const maxCr = Number(data.max_credits) || 135;
    const overallBarHtml = progressBarHtml({
        label: 'ความคืบหน้าตลอดหลักสูตร',
        passed: data.passed_credits,
        inProgress: p ? p.in_progress_credits : 0,
        target: maxCr, large: true,
    });

    document.getElementById('report').innerHTML = `
        <div class="summary-box">
          <div class="summary-name">${escapeHtml(data.student_id)} ${escapeHtml(data.name)}</div>
          <div class="summary-row">
            <span class="pill pill-lg">ผ่านแล้ว ${escapeHtml(data.passed_credits)} / ${escapeHtml(data.max_credits)} นก.</span>
            <span class="f-pill${data.f_count ? ' has-f' : ''}">
              ติด F: ${escapeHtml(data.f_count)} วิชา
            </span>
          </div>
          <div class="summary-bar">${overallBarHtml}</div>
        </div>
        ${fHtml}
        ${passedHtml}
      `;

    renderPassedCourses();
    animateBars(document.getElementById('report'));

    document.getElementById('note-area').className = '';
    document.getElementById('note-area').innerHTML = `<div class="note-box"><p><b>${escapeHtml(selected.student_id)} ${escapeHtml(selected.name)}</b></p><p class="muted">ผู้รับ: ${escapeHtml(selected.student_id)}@kmitl.ac.th</p><form onsubmit="sendNote(event)"><label>หัวข้อ</label><input id="note-subject" required value="คำแนะนำการวางแผนการเรียน"><label>คำแนะนำ</label><textarea id="note-message" required placeholder="พิมพ์คำแนะนำสำหรับนักศึกษา"></textarea><button id="send-btn" class="btn-note">เปิด Gmail เพื่อส่งคำแนะนำ</button><p id="note-result" class="hidden"></p></form></div>`;
    window.scrollTo({ top: document.getElementById('student-detail').offsetTop - 20, behavior: 'smooth' });
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
    } catch (_) { }
})();
