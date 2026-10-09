  /* ===================================================
     STATE
  =================================================== */
  let parsedCourses = [];    // raw from /review
  let parsedStudent = null;
  let planTermData = [];
  let dragCourseId = null;
  let nextCustomId = 1;
  let fileObj = null;
  let baselineStats = { ge:0, elective:0, free:0 };
  let selectedEnglishElectiveCode = null;

  const NON_PASS = new Set(['F','W','WU','U']);
  const CAT_COLORS = {
    ge:'#64748B', core_math:'#0284C7', core_cs:'#E65525',
    elective:'#D97706', free:'#DB2777', alternative:'#7C3AED'
  };

  document.addEventListener('DOMContentLoaded', () => {
    const savedEng = sessionStorage.getItem('smartgrad_english_elective');
    if (savedEng !== null && savedEng !== '') {
      selectedEnglishElectiveCode = savedEng;
    }
    const saved = sessionStorage.getItem('smartgrad_state');
    if (saved) {
      try {
        const state = JSON.parse(saved);
        parsedCourses = state.parsedCourses;
        parsedStudent = state.parsedStudent;
        renderDashboard(state.dashboardData);
        goToStep(3);
      } catch (e) {
        sessionStorage.removeItem('smartgrad_state');
      }
    }
  });

  /* ===================================================
     FILE INPUT
  =================================================== */
  const fileInput = document.getElementById('file-input');
  const uploadZone = document.getElementById('upload-zone');

  fileInput.addEventListener('change', function() {
    if (this.files[0]) selectFile(this.files[0]);
  });

  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('drag-over'); });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault(); uploadZone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f && f.type === 'application/pdf') selectFile(f);
    else showUploadError('กรุณาเลือกไฟล์เอกสารนามสกุล .pdf เท่านั้น');
  });

  function selectFile(f) {
    fileObj = f;
    document.getElementById('file-name-display').textContent = f.name;
    document.getElementById('selected-file').classList.add('show');
    document.getElementById('parse-btn').disabled = false;
    hideUploadError();
  }

  function showUploadError(msg) {
    const el = document.getElementById('upload-error');
    el.textContent = msg; el.style.display = 'block';
  }
  function hideUploadError() {
    document.getElementById('upload-error').style.display = 'none';
  }

  /* ===================================================
     STEP 1 → 2: Parse PDF
  =================================================== */
  async function uploadAndReview() {
    if (!fileObj) return;
    hideUploadError();
    const parseBtn = document.getElementById('parse-btn');
    parseBtn.disabled = true;
    document.getElementById('upload-spinner').classList.add('show');

    try {
      const reviewFd = new FormData();
      reviewFd.append('file', fileObj);
      let data;
      try {
        data = await requestJson('/review', { method: 'POST', body: reviewFd });
      } catch (e) {
        if (!(e instanceof ApiError) || e.status === 0) throw e;
        showUploadError(e.message || 'เกิดข้อผิดพลาดในการอ่านไฟล์');
        parseBtn.disabled = false;
        return;
      }
      parsedCourses = (data.courses || []).map(c => ({
        ...c,
        original_code: (c.code || '').trim(),
        original_grade: (c.grade || '').trim().toUpperCase(),
        original_credit: c.credit !== undefined ? Number(c.credit) : 3,
        is_overridden: Boolean(c.is_overridden),
      }));
      parsedStudent = data.student;
      if (!parsedStudent || !/^\d{8}$/.test(parsedStudent.student_id || '') || !parsedStudent.name) {
        showUploadError('ไม่พบชื่อหรือรหัสนักศึกษา 8 หลักใน Transcript กรุณาใช้ไฟล์ฉบับที่ออกจากสำนักทะเบียน');
        parseBtn.disabled = false;
        return;
      }

      const saveFd = new FormData();
      saveFd.append('file', fileObj);
      saveFd.append('student_name', parsedStudent.name || '');
      let saveData;
      try {
        saveData = await requestJson(`/api/students/${parsedStudent.student_id}/transcript`, { method: 'POST', body: saveFd });
      } catch (e) {
        if (!(e instanceof ApiError) || e.status === 0) throw e;
        showUploadError(e.message || 'ไม่สามารถบันทึก Transcript ได้');
        parseBtn.disabled = false;
        return;
      }
      if (saveData.detail) {
        showUploadError(saveData.detail);
        parseBtn.disabled = false;
        return;
      }
      renderReviewTable(parsedCourses);
      goToStep(2);
    } catch(e) {
      showUploadError('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
      parseBtn.disabled = false;
    } finally {
      document.getElementById('upload-spinner').classList.remove('show');
    }
  }

  /* ===================================================
     RENDER REVIEW TABLE
  =================================================== */
  function syncReviewInputs() {
    document.querySelectorAll('.review-row').forEach(tr => {
      const idx = parseInt(tr.dataset.idx);
      if (!isNaN(idx) && idx >= 0 && idx < parsedCourses.length) {
        const codeInp = tr.querySelector('.code-input');
        const nameInp = tr.querySelector('.name-input');
        const creditInp = tr.querySelector('.credit-input');
        const gradeInp = tr.querySelector('.grade-val-input');

        const currentCode = codeInp ? codeInp.value.trim() : (parsedCourses[idx].code || '');
        const currentName = nameInp ? nameInp.value.trim() : (parsedCourses[idx].name_en || '');
        const currentCredit = creditInp ? (parseFloat(creditInp.value.trim()) || 0) : (parsedCourses[idx].credit || 0);
        const currentGrade = gradeInp ? (gradeInp.value.trim().toUpperCase() || null) : parsedCourses[idx].grade;

        parsedCourses[idx].code = currentCode;
        parsedCourses[idx].name_en = currentName;
        parsedCourses[idx].credit = currentCredit;
        parsedCourses[idx].grade = currentGrade;

        const origCode = (parsedCourses[idx].original_code || '').trim();
        const origGrade = (parsedCourses[idx].original_grade || '').trim().toUpperCase() || null;
        const origCredit = parsedCourses[idx].original_credit !== undefined ? Number(parsedCourses[idx].original_credit) : null;

        const isManuallyAdded = Boolean(parsedCourses[idx].is_manually_added);
        const codeChanged = origCode ? (currentCode !== origCode) : Boolean(currentCode);
        const gradeChanged = (currentGrade || '') !== (origGrade || '');
        const creditChanged = (origCredit !== null) && (currentCredit !== origCredit);

        parsedCourses[idx].is_overridden = isManuallyAdded || codeChanged || gradeChanged || creditChanged;
      }
    });
  }

  function renderReviewTable(courses) {
    const tbody = document.getElementById('review-tbody');
    tbody.innerHTML = '';

    // group by semester
    const groups = {};
    for (let i = 0; i < courses.length; i++) {
      const c = courses[i];
      const key = `${c.semester || '0'}_${c.academic_year || ''}`;
      const label = c.semester && c.academic_year
        ? `ภาคเรียนที่ ${c.semester} ปีการศึกษา ${c.academic_year}`
        : 'เทียบโอน / ไม่ระบุภาคการศึกษา';
      if (!groups[key]) {
        groups[key] = {
          key: key,
          label: label,
          semester: c.semester,
          academic_year: c.academic_year,
          is_current: c.is_current,
          items: []
        };
      }
      groups[key].items.push({ course: c, idx: i });
    }

    let total = 0, passedCredit = 0;

    for (const group of Object.values(groups)) {
      // semester header row with add course button
      const hr = document.createElement('tr');
      hr.className = 'sem-header';
      const semParam = group.semester === null || group.semester === undefined ? 'null' : jsArg(group.semester);
      const yrParam = group.academic_year ? jsArg(group.academic_year) : 'null';
      const isCurParam = group.is_current ? 'true' : 'false';

      hr.innerHTML = `
        <td colspan="3">${escapeHtml(group.label)}</td>
        <td colspan="2" style="text-align:right;">
          <button type="button" class="btn-add-row" onclick="addCourseToSemester(${semParam}, ${yrParam}, ${isCurParam})">
            + เพิ่มวิชาในเทอมนี้
          </button>
        </td>
      `;
      tbody.appendChild(hr);

      for (const item of group.items) {
        const c = item.course;
        const i = item.idx;
        total++;
        const isCurrent = c.is_current;
        const grade = c.grade || '';
        const isFail = NON_PASS.has(grade.toUpperCase());
        const isPass = grade && !isFail;
        if (isPass) passedCredit += c.credit;

        const tr = document.createElement('tr');
        tr.className = 'review-row';
        tr.dataset.idx = i;
        const isOverridden = Boolean(c.is_overridden);
        const originalGrade = c.original_grade !== undefined ? c.original_grade : (grade || '');

        tr.innerHTML = `
          <td>
            <input class="grade-input code-input" type="text" value="${escapeHtml(c.code || '')}" placeholder="รหัสวิชา"
                   onchange="onReviewCodeChange(this, ${i})"
                   style="width:100px; text-align:left; font-family:monospace;" />
          </td>
          <td>
            <div style="display:flex; align-items:center; gap:8px;">
              <input class="grade-input name-input" type="text" value="${escapeHtml(c.name_en || '')}" placeholder="ชื่อวิชา" style="width:100%; text-align:left;" />
              ${isCurrent ? '<span class="badge-current" style="flex-shrink:0;">กำลังเรียน</span>' : ''}
            </div>
          </td>
          <td style="text-align:center">
            <input class="grade-input credit-input" type="number" min="0" max="15" value="${escapeHtml(c.credit !== undefined ? c.credit : 3)}" style="width:55px;" />
          </td>
          <td style="text-align:center">
            ${isCurrent
              ? '<span style="color:var(--gray-400);font-size:14px">–</span>'
              : `<input class="grade-input grade-val-input ${isOverridden ? 'overridden' : ''}" type="text" value="${escapeHtml(grade)}"
                   data-original="${escapeHtml(originalGrade)}"
                   oninput="onGradeChange(this)"
                   placeholder="–">`
            }
          </td>
          <td style="text-align:center">
            <button type="button" class="btn-del-row" onclick="removeReviewCourse(${i})" title="ลบวิชานี้">&times;</button>
          </td>
        `;
        tbody.appendChild(tr);
      }
    }

    // summary badges
    document.getElementById('review-info').innerHTML = `
      <div class="review-badge">จำนวนรายวิชาที่พบ: <strong>${courses.length}</strong> วิชา</div>
      <div class="review-badge">หน่วยกิตที่ผ่านการประเมิน: <strong>${passedCredit}</strong> หน่วยกิต</div>
      <div class="review-badge">ชื่อไฟล์เอกสาร: <strong style="color:var(--navy-700)">${escapeHtml(fileObj ? fileObj.name : 'Transcript')}</strong></div>
    `;

    setupEnglishElectiveUI(courses);
  }

  function addCourseToSemester(semester, academic_year, is_current) {
    syncReviewInputs();
    parsedCourses.push({
      code: '',
      name_en: '',
      credit: 3,
      grade: is_current ? null : '',
      semester: semester,
      academic_year: academic_year || null,
      is_current: is_current,
      is_manually_added: true,
      is_overridden: true,
      original_code: '',
      original_grade: is_current ? null : '',
      original_credit: 3,
    });
    renderReviewTable(parsedCourses);
    const rows = document.querySelectorAll('.review-row');
    if (rows.length > 0) {
      const lastCodeInput = rows[rows.length - 1].querySelector('.code-input');
      if (lastCodeInput) lastCodeInput.focus();
    }
  }

  function removeReviewCourse(idx) {
    syncReviewInputs();
    parsedCourses.splice(idx, 1);
    renderReviewTable(parsedCourses);
  }

  async function onReviewCodeChange(input, idx) {
    const code = input.value.trim();
    if (!code) return;
    try {
      const data = await requestJson(`/api/curriculum/courses/${code}`);
      const row = input.closest('tr');
      if (row) {
        const nameInput = row.querySelector('.name-input');
        const creditInput = row.querySelector('.credit-input');
        if (nameInput && (!nameInput.value.trim() || nameInput.value === code)) {
          nameInput.value = data.course_name_en || data.course_name_th;
          if (idx >= 0 && idx < parsedCourses.length) {
            parsedCourses[idx].name_en = nameInput.value;
          }
        }
        if (creditInput && (!creditInput.value || creditInput.value === '0')) {
          creditInput.value = data.credit;
          if (idx >= 0 && idx < parsedCourses.length) {
            parsedCourses[idx].credit = data.credit;
          }
        }
      }
    } catch(e) {}
  }

  function openAddSemesterModal() {
    document.getElementById('new-year-input').value = '';
    document.getElementById('new-sem-is-current').checked = false;
    document.getElementById('add-semester-modal').classList.add('show');
  }
  function closeAddSemesterModal() {
    document.getElementById('add-semester-modal').classList.remove('show');
  }
  function confirmAddSemester() {
    const semVal = document.getElementById('new-sem-select').value;
    const yrVal = document.getElementById('new-year-input').value.trim();
    const isCurrent = document.getElementById('new-sem-is-current').checked;

    let semester = null;
    let academic_year = null;

    if (semVal !== 'transfer') {
      semester = parseInt(semVal);
      if (!yrVal) {
        alert('กรุณาระบุปีการศึกษา (เช่น 2024-2025)');
        return;
      }
      academic_year = yrVal;
    }

    closeAddSemesterModal();
    addCourseToSemester(semester, academic_year, isCurrent);
  }

  function onGradeChange(input) {
    const val = input.value.trim().toUpperCase();
    const original = (input.dataset.original || '').trim().toUpperCase();
    if (val !== original) {
      input.classList.add('overridden');
    } else {
      input.classList.remove('overridden');
    }
  }

  /* ===================================================
     ENGLISH ELECTIVE DETECTION & UI
  =================================================== */
  function detectEnglishElective(courses) {
    const candidates = [];
    const excludeCodes = new Set(['90644007', '90644008', '90101001', '90101002']);
    const nonEngKeywords = ['THAI', 'CHINESE', 'JAPANESE', 'KOREAN', 'FRENCH', 'GERMAN', 'ภาษาไทย', 'ภาษาจีน', 'ภาษาญี่ปุ่น', 'ภาษาเกาหลี', 'ภาษาฝรั่งเศส', 'ภาษาเยอรมัน'];

    for (const c of courses) {
      const code = (c.code || '').trim();
      const name = (c.name_en || c.name_th || '').toUpperCase();
      const grade = (c.grade || '').toUpperCase();
      const isPassOrCurrent = c.is_current || (grade && !NON_PASS.has(grade));

      if (!isPassOrCurrent) continue;
      if (excludeCodes.has(code)) continue;

      const hasNonEng = nonEngKeywords.some(kw => name.includes(kw));
      if (hasNonEng) continue;

      const isGeLangCode = code.startsWith('90644') || code.startsWith('90101');
      const hasEngKeyword = name.includes('ENGLISH') || name.includes('WRITING') || 
                            name.includes('SPEAKING') || name.includes('LISTENING') || 
                            name.includes('READING') || name.includes('COMMUNICATION') || 
                            name.includes('CONVERSATION') || name.includes('PRESENTATION') ||
                            name.includes('TOEIC') || name.includes('TOEFL') || name.includes('IELTS');

      if (isGeLangCode || hasEngKeyword) {
        candidates.push(c);
      }
    }
    return candidates;
  }

  function englishCourseOption(c) {
    const label = `${c.code} ${c.name_en || c.name_th} (${c.credit} นก.) ${c.is_current ? '[กำลังเรียน]' : (c.grade ? `[เกรด ${c.grade}]` : '')}`;
    return `<option value="${escapeHtml(c.code)}">${escapeHtml(label)}</option>`;
  }

  function setupEnglishElectiveUI(courses) {
    const selectEl = document.getElementById('ge-english-course-select');
    const hintEl = document.getElementById('ge-english-hint');
    const radioNotTaken = document.getElementById('ge-eng-radio-not-taken');
    const radioTaken = document.getElementById('ge-eng-radio-taken');
    const wrapEl = document.getElementById('ge-english-select-wrap');
    if (!selectEl) return;

    const candidates = detectEnglishElective(courses);

    let optionsHtml = '<option value="">-- กรุณาเลือกวิชาภาษาอังกฤษจาก Transcript --</option>';

    if (candidates.length > 0) {
      optionsHtml += '<optgroup label="วิชาที่ตรวจพบเข้าข่ายวิชาภาษาอังกฤษ">';
      candidates.forEach(c => {
        optionsHtml += englishCourseOption(c);
      });
      optionsHtml += '</optgroup>';
    }

    const candCodes = new Set(candidates.map(c => c.code));
    candCodes.add('90644007');
    candCodes.add('90644008');
    const otherCourses = courses.filter(c => c.code && !candCodes.has(c.code));
    if (otherCourses.length > 0) {
      optionsHtml += '<optgroup label="รายวิชาอื่นๆ ใน Transcript">';
      otherCourses.forEach(c => {
        optionsHtml += englishCourseOption(c);
      });
      optionsHtml += '</optgroup>';
    }

    selectEl.innerHTML = optionsHtml;

    if (selectedEnglishElectiveCode) {
      radioTaken.checked = true;
      wrapEl.style.display = 'block';
      selectEl.value = selectedEnglishElectiveCode;
      if (hintEl) hintEl.style.display = 'none';
    } else if (candidates.length > 0) {
      radioTaken.checked = true;
      wrapEl.style.display = 'block';
      selectEl.value = candidates[0].code;
      selectedEnglishElectiveCode = candidates[0].code;
      if (hintEl) {
        hintEl.style.display = 'block';
        hintEl.textContent = `ระบบตรวจพบวิชา "${candidates[0].code} ${candidates[0].name_en || candidates[0].name_th}" และเลือกให้อัตโนมัติ`;
      }
    } else {
      radioNotTaken.checked = true;
      wrapEl.style.display = 'none';
      selectedEnglishElectiveCode = null;
      if (hintEl) hintEl.style.display = 'none';
    }
  }

  function toggleGeEnglishSelect(isTaken) {
    const wrapEl = document.getElementById('ge-english-select-wrap');
    const selectEl = document.getElementById('ge-english-course-select');
    const hintEl = document.getElementById('ge-english-hint');
    if (isTaken) {
      wrapEl.style.display = 'block';
      selectedEnglishElectiveCode = selectEl.value || null;
    } else {
      wrapEl.style.display = 'none';
      selectedEnglishElectiveCode = null;
      if (hintEl) hintEl.style.display = 'none';
    }
  }

  function onGeEnglishCourseSelectChange() {
    const selectEl = document.getElementById('ge-english-course-select');
    const hintEl = document.getElementById('ge-english-hint');
    selectedEnglishElectiveCode = selectEl.value || null;
    if (hintEl) hintEl.style.display = 'none';
  }

  /* ===================================================
     STEP 2 → 3: Confirm & Compute
  =================================================== */
  async function confirmAndCompute() {
    const radioTaken = document.getElementById('ge-eng-radio-taken');
    const radioNotTaken = document.getElementById('ge-eng-radio-not-taken');

    if (radioTaken && radioNotTaken) {
      if (!radioTaken.checked && !radioNotTaken.checked) {
        alert('กรุณาตอบคำถาม: ท่านได้ลงเรียนหรือสอบผ่านวิชาเลือกภาษาอังกฤษ (GE English Elective) แล้วหรือไม่');
        const card = radioNotTaken.closest('.card');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      if (radioTaken.checked) {
        const selectEl = document.getElementById('ge-english-course-select');
        if (!selectEl.value) {
          alert('กรุณาเลือกรายวิชาภาษาอังกฤษที่ท่านได้ลงเรียนจากรายการ');
          selectEl.focus();
          return;
        }
        selectedEnglishElectiveCode = selectEl.value;
      } else {
        selectedEnglishElectiveCode = null;
      }
      sessionStorage.setItem('smartgrad_english_elective', selectedEnglishElectiveCode || '');
    }

    document.getElementById('confirm-btn').disabled = true;
    document.getElementById('confirm-spinner').style.display = 'inline-flex';

    syncReviewInputs();

    // filter out empty course rows if any
    parsedCourses = parsedCourses.filter(c => (c.code && c.code.trim()) || (c.name_en && c.name_en.trim()));

    try {
      const data = await requestJson('/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          courses: parsedCourses,
          curriculum_id: parsedStudent?.curriculum_id || null,
          student_id: parsedStudent?.student_id || null,
        }),
      });
      renderDashboard(data);
      goToStep(3);
    } catch(e) {
      if (e instanceof ApiError && e.status !== 0) {
        alert('เกิดข้อผิดพลาดในการประมวลผล: ' + (e.message || 'ไม่ทราบสาเหตุ'));
      } else {
        alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
      }
    } finally {
      document.getElementById('confirm-btn').disabled = false;
      document.getElementById('confirm-spinner').style.display = 'none';
    }
  }

  /* ===================================================
     RENDER DASHBOARD
  =================================================== */
  function renderDashboard(d) {
    window.dashboardData = d;
    sessionStorage.setItem('smartgrad_state', JSON.stringify({
        parsedCourses: parsedCourses,
        parsedStudent: parsedStudent,
        dashboardData: d
    }));
    // Overview cards
    const hasInProg = (d.in_progress_credits && d.in_progress_credits > 0);
    document.getElementById('overview-cards').innerHTML = `
      <div class="ov-card success">
        <div class="ov-label">หน่วยกิตสะสมทั้งหมด (รวมกำลังเรียน)</div>
        <div class="ov-value">${d.completed_credits} <span>/ ${d.total_credits}</span></div>
        <div class="ov-sub">${hasInProg ? `ผ่านแล้ว ${d.passed_credits} หน่วยกิต + กำลังเรียน ${d.in_progress_credits} หน่วยกิต` : 'หน่วยกิต'}</div>
      </div>
    `;

    // Progress bar
    document.getElementById('progress-card').innerHTML = `
      <div class="card-title"> ภาพรวมความก้าวหน้าการศึกษา</div>
      <div class="prog-bar-wrap">
        <div class="prog-bar-top">
          <span>ความคืบหน้าคิดเป็นเปอร์เซ็นต์ (อ้างอิงจาก ${d.total_credits} หน่วยกิต${hasInProg ? ' รวมภาคเรียนปัจจุบัน' : ''})</span>
          <strong>${d.progress_percent}%</strong>
        </div>
        <div class="prog-track">
          <div class="prog-fill" style="width: 0%"></div>
        </div>
      </div>
    `;
    // animate progress
    setTimeout(() => {
      const fill = document.querySelector('.prog-fill');
      if (fill) fill.style.width = d.progress_percent + '%';
    }, 100);

    // In-progress
    if (d.in_progress && d.in_progress.length > 0) {
      document.getElementById('inprog-card').style.display = 'block';
      document.getElementById('inprog-list').innerHTML = d.in_progress.map(c => `
        <div class="inprog-chip">
          <span class="code">${escapeHtml(c.code)}</span>
          <span class="name">${escapeHtml(c.name_en)}</span>
        </div>
      `).join('');
    } else {
      document.getElementById('inprog-card').style.display = 'none';
    }

    // Categories
    document.getElementById('cat-grid').innerHTML = d.categories.map(cat => {
      const c = CAT_COLORS[cat.key] || '#94a3b8';
      const isComplete = cat.earned_credits >= cat.target_credits;
      
      let html = `
        <div class="cat-card" onclick="toggleCat(${jsArg(cat.key)})" id="cat-card-${escapeHtml(cat.key)}">
          <div class="cat-header">
            <div class="cat-name">${escapeHtml(cat.label)}</div>
            <div class="cat-credits" style="color: ${isComplete ? 'var(--success)' : 'var(--navy-900)'}">
              ${cat.earned_credits} <small>/ ${cat.target_credits}</small>
            </div>
          </div>
          <div class="cat-track">
            <div class="cat-fill" style="width: 0%; background-color: ${c}" data-w="${cat.percent}%"></div>
          </div>
          <div class="cat-pct">${cat.percent}% ${isComplete ? '' : ''}</div>
          <div class="cat-detail" id="cat-detail-${escapeHtml(cat.key)}">
      `;
      
      if (cat.courses.length === 0) {
        html += `<div style="color:var(--text-muted);font-size:13px;padding:8px 0;text-align:center;">ไม่มีข้อมูลรายวิชาในหมวดนี้</div>`;
      } else {
        const sortedCourses = (cat.courses || []).slice().sort((a, b) => (b.credit || 0) - (a.credit || 0));
        sortedCourses.forEach(crs => {
          html += `
            <div class="cat-course-item">
              <div class="cat-course-left">
                <div class="cat-course-code">${escapeHtml(crs.code)}</div>
                <div class="cat-course-name">${escapeHtml(crs.name_en)}</div>
              </div>
              <div class="cat-course-right">
                <span class="cat-grade ${crs.is_current ? 'in-prog' : ''}">${crs.is_current ? 'กำลังเรียน' : escapeHtml(crs.grade || '-')}</span>
                <span class="cat-cr">${crs.credit} นก.</span>
              </div>
            </div>
          `;
        });
      }
      html += `</div></div>`;
      return html;
    }).join('');

    // Generate formal summary for print
    let summaryHtml = `
      <h3 style="margin-top:0; margin-bottom:8px; border-bottom:2px solid #000; padding-bottom:4px; font-family:'Sarabun',sans-serif; font-size:18px;">สรุปหน่วยกิตแยกตามหมวดวิชา</h3>
      <table style="width:100%; border-collapse:collapse; font-size:14px; font-family:'Sarabun',sans-serif;">
        <thead>
          <tr style="border-bottom:1px solid #000; text-align:left;">
            <th style="padding:4px 0; background:none;">หมวดวิชา</th>
            <th style="padding:4px 0; text-align:center; background:none;">ที่ต้องเรียน</th>
            <th style="padding:4px 0; text-align:center; background:none;">ผ่าน/กำลังเรียน</th>
            <th style="padding:4px 0; text-align:right; background:none;">สถานะ</th>
          </tr>
        </thead>
        <tbody>
    `;
    d.categories.forEach(cat => {
      const isComplete = cat.earned_credits >= cat.target_credits;
      const statusText = isComplete ? 'ครบถ้วน' : `ขาด ${cat.target_credits - cat.earned_credits}`;
      summaryHtml += `
        <tr style="border-bottom:1px dashed #ccc;">
          <td style="padding:6px 0;">${escapeHtml(cat.label)}</td>
          <td style="padding:6px 0; text-align:center;">${cat.target_credits}</td>
          <td style="padding:6px 0; text-align:center;">${cat.earned_credits}</td>
          <td style="padding:6px 0; text-align:right; font-weight:${isComplete ? 'bold' : 'normal'}; color:${isComplete ? '#000' : '#444'};">${statusText}</td>
        </tr>
      `;
    });
    summaryHtml += `</tbody></table>`;
    document.getElementById('print-cat-summary').innerHTML = summaryHtml;

    // animate category bars
    setTimeout(() => {
      document.querySelectorAll('.cat-fill').forEach(el => {
        el.style.width = el.getAttribute('data-w');
      });
    }, 100);

    // Timeline
    if (d.timeline.length === 0) {
      document.getElementById('timeline-list').innerHTML = '<p style="color:var(--text-muted);font-size:14px;text-align:center;padding:20px;">ไม่พบประวัติการศึกษา</p>';
    } else {
      document.getElementById('timeline-list').innerHTML = d.timeline.map((tl, i) => {
        let totalCr = tl.courses.reduce((sum, c) => sum + (c.credit || 0), 0);
        return `
          <div class="timeline-item">
            <div class="timeline-header" onclick="toggleTl(${i})">
              <div class="timeline-header-left">
                <div class="timeline-dot"></div>
                <div>
                  <div class="timeline-label">${escapeHtml(tl.label)}</div>
                  <div class="timeline-meta">${tl.courses.length} รายวิชา | ${totalCr} หน่วยกิต</div>
                </div>
              </div>
              <div class="timeline-chevron" id="tl-chev-${i}">▼</div>
            </div>
            <div class="timeline-body" id="tl-body-${i}">
              ${tl.courses.map(c => `
                <div class="tl-row">
                  <div class="tl-code">${escapeHtml(c.code)}</div>
                  <div class="tl-name">${escapeHtml(c.name_en)}</div>
                  <div class="tl-cr">${c.credit} นก.</div>
                  <div class="tl-grade">${escapeHtml(c.grade)}</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }).join('');
    }

    // Remaining table
    if (d.remaining_list.length === 0) {
      document.getElementById('remaining-tbody').innerHTML = `<tr><td colspan="4" style="text-align:center;color:var(--success);padding:32px;">ยินดีด้วย! คุณผ่านรายวิชาบังคับตามหลักสูตรครบถ้วนแล้ว </td></tr>`;
    } else {
      document.getElementById('remaining-tbody').innerHTML = d.remaining_list.map(c => {
        const isBlock = c.prereq_status.includes('ติดวิชา');
        return `
          <tr>
            <td class="code-cell">${escapeHtml(c.code)}</td>
            <td style="font-weight:500; color:var(--navy-800)">${escapeHtml(c.name_en)}</td>
            <td class="credit-cell">${c.credit}</td>
            <td>
              ${isBlock
                ? `<span class="prereq-block">${escapeHtml(c.prereq_status)}</span>`
                : `<span class="prereq-ok">พร้อมลงทะเบียนได้</span>`
              }
            </td>
          </tr>
        `;
      }).join('');
    }
  }

  /* ===================================================
     TOGGLES
  =================================================== */
  function toggleCat(key) {
    const el = document.getElementById(`cat-detail-${key}`);
    const card = document.getElementById(`cat-card-${key}`);
    if (el.classList.contains('show')) {
      el.classList.remove('show');
      card.classList.remove('active');
    } else {
      el.classList.add('show');
      card.classList.add('active');
    }
  }

  function toggleTl(idx) {
    const body = document.getElementById(`tl-body-${idx}`);
    const chev = document.getElementById(`tl-chev-${idx}`);
    if (body.classList.contains('show')) {
      body.classList.remove('show');
      chev.classList.remove('open');
    } else {
      body.classList.add('show');
      chev.classList.add('open');
    }
  }

  /* ===================================================
     NAVIGATION
  =================================================== */
  function goToStep(step) {
    document.getElementById('upload-section').style.display = (step === 1) ? 'block' : 'none';
    document.getElementById('review-section').style.display = (step === 2) ? 'block' : 'none';
    document.getElementById('dashboard-section').style.display = (step === 3) ? 'block' : 'none';

    if (step === 3) {
      document.getElementById('dashboard-content-wrapper').style.display = 'block';
      document.getElementById('plan-section').classList.remove('show');
      document.body.classList.remove('print-plan-mode');
    }

    // update dots
    [1,2,3].forEach(i => {
      const dot = document.getElementById(`step${i}-dot`);
      const lbl = document.getElementById(`step${i}-lbl`);
      const line = document.getElementById(`line${i}`);
      
      if (i < step) {
        dot.className = 'step-dot done'; dot.innerHTML = '✓';
        lbl.className = 'step-label active';
        if (line) line.className = 'step-line done';
      } else if (i === step) {
        dot.className = 'step-dot active'; dot.innerHTML = i;
        lbl.className = 'step-label active';
        if (line) line.className = 'step-line';
      } else {
        dot.className = 'step-dot'; dot.innerHTML = i;
        lbl.className = 'step-label';
        if (line) line.className = 'step-line';
      }
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetToUpload() {
    sessionStorage.removeItem('smartgrad_state');
    sessionStorage.removeItem('smartgrad_english_elective');
    selectedEnglishElectiveCode = null;
    fileObj = null;
    parsedCourses = [];
    parsedStudent = null;
    fileInput.value = '';
    document.getElementById('file-name-display').textContent = '';
    document.getElementById('selected-file').classList.remove('show');
    document.getElementById('parse-btn').disabled = true;
    const rNotTaken = document.getElementById('ge-eng-radio-not-taken');
    const rTaken = document.getElementById('ge-eng-radio-taken');
    if (rNotTaken) rNotTaken.checked = false;
    if (rTaken) rTaken.checked = false;
    const wEl = document.getElementById('ge-english-select-wrap');
    if (wEl) wEl.style.display = 'none';
    const hEl = document.getElementById('ge-english-hint');
    if (hEl) hEl.style.display = 'none';
    hideUploadError();
    goToStep(1);
  }

  /* ===================================================
     STUDY PLAN
  =================================================== */
  let selectedPlanType = 'normal';

  function setPlanType(type) {
    selectedPlanType = type;
    document.querySelectorAll('.plan-toggle-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.plan === type);
    });
    // If plan is already showing, regenerate
    if (document.getElementById('plan-section').classList.contains('show')) {
      generatePlan();
    }
  }

  async function generatePlan() {
    const btn = document.getElementById('plan-btn');
    const spinner = document.getElementById('plan-spinner');
    btn.disabled = true;
    spinner.classList.add('show');

    try {
      const data = await requestJson('/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          courses: parsedCourses,
          plan_type: selectedPlanType,
          curriculum_id: parsedStudent?.curriculum_id || null,
        }),
      });
      renderStudyPlan(data);
      document.getElementById('dashboard-content-wrapper').style.display = 'none';
      document.getElementById('plan-section').classList.add('show');
      document.body.classList.add('print-plan-mode');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (e) {
      if (e instanceof ApiError && e.status !== 0) {
        alert('เกิดข้อผิดพลาด: ' + (e.message || 'ไม่ทราบสาเหตุ'));
      } else {
        alert('ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้');
      }
    } finally {
      btn.disabled = false;
      spinner.classList.remove('show');
    }
  }

  function closePlan() {
    document.getElementById('plan-section').classList.remove('show');
    document.getElementById('dashboard-content-wrapper').style.display = 'block';
    document.body.classList.remove('print-plan-mode');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderStudyPlan(d) {
    planTermData = d.plan_terms;
    baselineStats = {
      ge: d.remaining_ge_credits,
      elective: d.remaining_elective_credits,
      free: d.remaining_free_credits
    };
    
    // Process planTermData to extract non-core and deferred core courses into draggable ones
    let sysPlannedGe = 0, sysPlannedElective = 0, sysPlannedFree = 0;
    planTermData.forEach((term, i) => {
        const fixedCore = [];
        const draggableCourses = [];
        if (term.is_locked) {
            // Keep all courses locked in current enrolled term
            term.core_courses.forEach(c => fixedCore.push(c));
        } else {
            term.core_courses.forEach(c => {
                const isCore = (c.category === 'core_cs' || c.category === 'core_math' || c.category === 'alternative');
                if (isCore && !c.is_deferred) {
                    fixedCore.push(c);
                } else {
                    draggableCourses.push(c);
                    if(c.category === 'ge') sysPlannedGe += (c.credit || 0);
                    if(c.category === 'elective') sysPlannedElective += (c.credit || 0);
                    if(c.category === 'free') sysPlannedFree += (c.credit || 0);
                }
            });
        }
        term.fixed_core_courses = fixedCore;
        term.draggable_courses = draggableCourses;
        term.fixed_core_credits = fixedCore.reduce((sum, c) => sum + (c.credit || 0), 0);

        // Initial core credits = fixed core credits + deferred core credits in this term
        const deferredCoreCredits = draggableCourses.reduce((sum, c) => {
            const isCore = (c.category === 'core_cs' || c.category === 'core_math' || c.category === 'alternative');
            return sum + (isCore ? (c.credit || 0) : 0);
        }, 0);
        term.core_credits = term.fixed_core_credits + deferredCoreCredits;
        term.available_credits = term.max_credits - term.core_credits;
    });

    // Warnings
    const warningsEl = document.getElementById('plan-warnings');
    if (d.warnings.length > 0) {
      warningsEl.innerHTML = d.warnings.map(w => {
        return `<div class="plan-alert warning"><div class="plan-alert-icon">!</div><div class="plan-alert-content">${escapeHtml(w)}</div></div>`;
      }).join('');
    } else {
      warningsEl.innerHTML = '';
    }

    // Summary
    document.getElementById('plan-summary').innerHTML = `
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:16px; margin-bottom:24px;">
        <div class="plan-stat">
          <div class="plan-stat-value" id="ui-rem-elec" style="font-size:24px"><span style="color:var(--kmitl-orange)">0</span> / ${d.remaining_elective_credits}</div>
          <div class="plan-stat-label">หน่วยกิตเลือกเฉพาะสาขา</div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-value" id="ui-rem-free" style="font-size:24px"><span style="color:var(--kmitl-orange)">0</span> / ${d.remaining_free_credits}</div>
          <div class="plan-stat-label">หน่วยกิตเลือกเสรี</div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-value" id="ui-rem-ge" style="font-size:24px"><span style="color:var(--kmitl-orange)">0</span> / ${d.remaining_ge_credits}</div>
          <div class="plan-stat-label">หน่วยกิต GE </div>
        </div>
        <div class="plan-stat">
          <div class="plan-stat-value ${d.can_graduate_on_time ? 'ok' : 'warn'}" id="ui-total-avail">${d.total_available_slots}</div>
          <div class="plan-stat-label">หน่วยกิตว่างในตาราง</div>
        </div>
      </div>
    `;

    // Populate Unplanned Pool
    const pool = document.getElementById('unplanned-pool');
    pool.innerHTML = '';
    
    const addBlocks = (credits, label, cat) => {
        let remaining = credits;
        while(remaining > 0) {
            let cr = Math.min(3, remaining);
            let id = 'gen_' + cat + '_' + nextCustomId++;
            pool.innerHTML += `
              <div class="plan-course-row draggable-course sys-course" draggable="true" id="${id}" data-cat="${cat}" data-credit="${cr}" ondragstart="dragStart(event)" ondragend="dragEnd(event)" style="position:relative;">
                <div class="plan-course-code" style="color:var(--kmitl-orange); font-weight:600;"><span style="position:absolute; left:0; color:var(--text-muted);">⋮⋮</span> ${cat.toUpperCase()}</div>
                <div class="plan-course-name">${label}</div>
                <span class="plan-badge deferred">รอลงตาราง</span>
                <div class="plan-course-credit">${cr} นก.</div>
              </div>`;
            remaining -= cr;
        }
    };

    let remainingGeForPool = Math.max(0, d.remaining_ge_credits - sysPlannedGe);
    if (!selectedEnglishElectiveCode && remainingGeForPool > 0) {
      let cr = Math.min(3, remainingGeForPool);
      let engId = 'gen_ge_eng_' + nextCustomId++;
      pool.innerHTML += `
        <div class="plan-course-row draggable-course sys-course" draggable="true" id="${engId}" data-cat="ge" data-credit="${cr}" ondragstart="dragStart(event)" ondragend="dragEnd(event)" style="position:relative; border-left:4px solid var(--kmitl-orange);">
          <div class="plan-course-code" style="color:var(--kmitl-orange); font-weight:600;"><span style="position:absolute; left:0; color:var(--text-muted);">⋮⋮</span> GE ENG</div>
          <div class="plan-course-name">วิชาเลือกทางภาษา (English Elective)</div>
          <span class="plan-badge required" style="background:#FFF7ED; color:#C2410C; border:1px solid #FDBA74;">บังคับ 1 วิชา</span>
          <div class="plan-course-credit">${cr} นก.</div>
        </div>`;
      remainingGeForPool = Math.max(0, remainingGeForPool - cr);
    }

    addBlocks(remainingGeForPool, 'วิชาศึกษาทั่วไป (GE)', 'ge');
    addBlocks(d.remaining_elective_credits - sysPlannedElective, 'วิชาเลือกเฉพาะสาขา', 'elective');
    addBlocks(d.remaining_free_credits - sysPlannedFree, 'วิชาเลือกเสรี', 'free');
    
    if(pool.innerHTML === '') {
        pool.innerHTML = '<div style="color:var(--gray-400); font-size:14px; width:100%; text-align:center;">ไม่มีวิชาที่ต้องลงเพิ่ม</div>';
    }

    // Plan terms
    const termsEl = document.getElementById('plan-terms-list');
    if (d.plan_terms.length === 0) {
      termsEl.innerHTML = '<p style="color:var(--text-muted);font-size:14px;text-align:center;padding:24px;">ไม่มีเทอมที่เหลือในแผนการศึกษา</p>';
      return;
    }

    termsEl.innerHTML = d.plan_terms.map((term, i) => {
      let fixedCoursesHtml = '';
      if (term.fixed_core_courses && term.fixed_core_courses.length > 0) {
        fixedCoursesHtml = term.fixed_core_courses.map(c => {
          let prereqHtml = '';
          if (c.unpassed_prereqs && c.unpassed_prereqs.length > 0) {
            prereqHtml = c.unpassed_prereqs.map(p => `
              <div class="prereq-warning" style="font-size:12px; margin-top:4px; display:inline-flex; align-items:center; gap:6px; background:${p.is_current ? '#FFFBEB' : '#FEF2F2'}; color:${p.is_current ? '#92400E' : '#991B1B'}; border:1px solid ${p.is_current ? '#FDE68A' : '#FECACA'}; border-radius:4px; padding:2px 8px;">
                <span>วิชาบังคับก่อนที่ยังไม่ได้เรียน: <strong>${escapeHtml(p.name || p.code)}</strong> (${escapeHtml(p.code)}) ${p.is_current ? '<span style="color:#d97706; font-weight:600;">[กำลังเรียน]</span>' : '<span style="color:#dc2626; font-weight:600;">[ยังไม่ได้เรียน]</span>'}</span>
              </div>
            `).join('');
          }
          return `
            <div class="plan-course-row">
              <div class="plan-course-code">${escapeHtml(c.code)}</div>
              <div class="plan-course-name">
                <div>${escapeHtml(c.name_en || c.name_th)}</div>
                ${prereqHtml}
              </div>
              <span class="plan-badge required">
                ${term.is_locked ? 'กำลังเรียน' : 'บังคับ'}
              </span>
              <div class="plan-course-credit">${c.credit} นก.</div>
            </div>
          `;
        }).join('');
      }

      const hasCore = (term.fixed_core_courses && term.fixed_core_courses.length > 0) ||
                      (term.draggable_courses && term.draggable_courses.some(c => (c.category === 'core_cs' || c.category === 'core_math' || c.category === 'alternative' || c.is_deferred)));
      const emptyMsgHtml = `<div class="empty-core-msg" style="padding:16px 20px;color:var(--text-muted);font-size:14px;text-align:center; ${hasCore ? 'display:none;' : ''}">ไม่มีวิชาบังคับในเทอมนี้ — สามารถลงวิชาเลือก/เสรีได้</div>`;

      const draggableCoursesHtml = (term.draggable_courses || []).map(c => {
        const isCore = (c.category === 'core_cs' || c.category === 'core_math' || c.category === 'alternative');
        const badgeLabel = c.is_deferred ? 'บังคับ (ค้างเรียน)' :
                           (c.category === 'ge' ? 'ศึกษาทั่วไป' :
                           (c.category === 'elective' ? 'เลือกเฉพาะ' :
                           (c.category === 'free' ? 'เลือกเสรี' : 'วิชาเลือก')));
        const badgeClass = c.is_deferred ? 'deferred' : (isCore ? 'required' : 'deferred');

        let prereqHtml = '';
        if (c.unpassed_prereqs && c.unpassed_prereqs.length > 0) {
          prereqHtml = c.unpassed_prereqs.map(p => `
            <div class="prereq-warning" style="font-size:12px; margin-top:4px; display:inline-flex; align-items:center; gap:6px; background:${p.is_current ? '#FFFBEB' : '#FEF2F2'}; color:${p.is_current ? '#92400E' : '#991B1B'}; border:1px solid ${p.is_current ? '#FDE68A' : '#FECACA'}; border-radius:4px; padding:2px 8px;">
              <span>วิชาบังคับก่อนที่ยังไม่ได้เรียน: <strong>${escapeHtml(p.name || p.code)}</strong> (${escapeHtml(p.code)}) ${p.is_current ? '<span style="color:#d97706; font-weight:600;">[กำลังเรียน]</span>' : '<span style="color:#dc2626; font-weight:600;">[ยังไม่ได้เรียน]</span>'}</span>
            </div>
          `).join('');
        }

        const unpassedJson = escapeHtml(JSON.stringify(c.unpassed_prereqs || []));
        const prereqsJson = escapeHtml(JSON.stringify(c.prereqs || []));

        return `
          <div class="plan-course-row draggable-course sys-course" 
               draggable="true" 
               id="sys_${escapeHtml(c.code)}_${i}" 
               data-code="${escapeHtml(c.code)}"
               data-cat="${escapeHtml(c.category || 'core')}" 
               data-credit="${escapeHtml(c.credit)}" 
               data-is-core="${isCore ? 'true' : 'false'}"
               data-deferred="${c.is_deferred ? 'true' : 'false'}"
               data-unpassed="${unpassedJson}"
               data-prereqs="${prereqsJson}"
               ondragstart="dragStart(event)" 
               ondragend="dragEnd(event)" 
               style="position:relative;">
            <div class="plan-course-code" style="color:var(--kmitl-orange); font-weight:600;"><span style="position:absolute; left:0; color:var(--text-muted); cursor:grab;">⋮⋮</span> ${escapeHtml(c.code)}</div>
            <div class="plan-course-name">
              <div>${escapeHtml(c.name_en || c.name_th)}</div>
              <div class="course-prereq-container">${prereqHtml}</div>
            </div>
            <span class="plan-badge ${badgeClass}">${badgeLabel}</span>
            <div class="plan-course-credit">${c.credit} นก.</div>
          </div>
        `;
      }).join('');

      return `
        <div class="plan-term ${term.is_locked ? 'locked' : ''}">
          <div class="plan-term-header" onclick="togglePlanTerm(${i})" style="${term.is_locked ? 'background-color: var(--gray-100);' : ''}">
            <div class="plan-term-left">
              <div class="plan-term-dot" style="${term.is_locked ? 'background-color: var(--gray-400);' : ''}"></div>
              <div class="plan-term-label">${escapeHtml(term.label)}</div>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
              <div class="plan-term-meta">
                ${term.is_locked ? `
                  <span style="color:var(--kmitl-orange); font-weight:600;">ลงทะเบียน: <strong>${term.core_credits} นก. (กำลังเรียน)</strong></span>
                ` : `
                  <span>บังคับ: <strong id="term-core-${i}">${term.core_credits} นก.</strong></span>
                  <span>ว่าง: <strong id="term-avail-${i}" style="color:${term.available_credits > 0 ? 'var(--success)' : 'var(--danger)'}">${term.available_credits} นก.</strong></span>
                `}
              </div>
              <div class="plan-term-chevron" id="plan-chev-${i}">▼</div>
            </div>
          </div>
          <div class="plan-term-body show" id="plan-body-${i}">
            <div class="plan-term-dropzone" id="dropzone-${i}" data-idx="${i}" ${term.is_locked ? '' : `ondragover="allowDrop(event)" ondragleave="dragLeave(event)" ondrop="drop(event, ${i})"`}>
                ${fixedCoursesHtml}
                ${emptyMsgHtml}
                ${draggableCoursesHtml}
            </div>
            ${term.is_locked ? '' : `<button class="btn-add-course" onclick="openAddCourseModal(${i})">+ เพิ่มวิชาอื่นๆ</button>`}
            <div class="plan-term-footer">
              <span>หน่วยกิตรวม (รวมที่ลากมา): <strong id="term-total-${i}">${term.core_credits}</strong> / ${term.max_credits}</span>
              <div class="plan-credits-bar">
                <div class="plan-credits-fill" id="term-fill-${i}" style="width:${(term.core_credits / term.max_credits)*100}%"></div>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Suggestions
    const sugEl = document.getElementById('plan-suggestions');
    const sugListEl = document.getElementById('plan-suggestions-list');
    let finalSuggestions = [...(d.suggestions || [])];
    if (!selectedEnglishElectiveCode) {
      finalSuggestions.push('ตามเกณฑ์หลักสูตรหมวด GE นักศึกษาต้องเลือกเรียนวิชาเลือกภาษาอังกฤษเพิ่มอีกอย่างน้อย 1 วิชา (3 หน่วยกิต)');
    }
    if (finalSuggestions.length > 0) {
      sugEl.style.display = 'block';
      sugListEl.innerHTML = finalSuggestions.map(s => `<li>${escapeHtml(s)}</li>`).join('');
    } else {
      sugEl.style.display = 'none';
    }

    // Recalculate on initial render so summary card and term counters match perfectly
    recalculateAllTerms();
  }

  // ===== DRAG AND DROP LOGIC =====
  function dragStart(e) {
      dragCourseId = e.target.id;
      e.target.classList.add('dragging');
  }
  function dragEnd(e) {
      e.target.classList.remove('dragging');
  }
  function allowDrop(e) {
      e.preventDefault();
      const zone = e.target.closest('.plan-term-dropzone, .unplanned-pool');
      if(zone) zone.classList.add('drag-over');
  }
  function dragLeave(e) {
      const zone = e.target.closest('.plan-term-dropzone, .unplanned-pool');
      if(zone) zone.classList.remove('drag-over');
  }
  function drop(e, termIdx) {
      e.preventDefault();
      const zone = e.target.closest('.plan-term-dropzone, .unplanned-pool');
      if(zone) zone.classList.remove('drag-over');
      
      if(!dragCourseId) return;
      const el = document.getElementById(dragCourseId);
      if(!el) return;
      
      // If pool was empty msg
      const pool = document.getElementById('unplanned-pool');
      if(pool && pool.querySelector('div[style*="ไม่มีวิชา"]')) {
          pool.innerHTML = '';
      }
      
      if(termIdx === 'pool') {
          if (pool) pool.appendChild(el);
      } else {
          const dropzone = document.getElementById(`dropzone-${termIdx}`);
          if (dropzone) dropzone.appendChild(el);
      }
      
      recalculateAllTerms();
  }

  function recalculateAllTerms() {
      if(!planTermData) return;
      
      let poolGe = 0, poolElective = 0, poolFree = 0;
      const pool = document.getElementById('unplanned-pool');
      if(pool) {
          pool.querySelectorAll('.draggable-course').forEach(el => {
              if (el.dataset.isCore === "true") return;
              const cr = parseInt(el.dataset.credit || 0);
              const cat = el.dataset.cat;
              if(cat === 'ge') poolGe += cr;
              if(cat === 'elective') poolElective += cr;
              if(cat === 'free') poolFree += cr;
          });
      }
      
      // Calculate custom added courses (which bypass the pool)
      let customGe = 0, customElective = 0, customFree = 0;
      planTermData.forEach((term, i) => {
          const dropzone = document.getElementById(`dropzone-${i}`);
          if(!dropzone) return;
          dropzone.querySelectorAll('.custom-course').forEach(el => {
              const cr = parseInt(el.dataset.credit || 0);
              const cat = el.dataset.cat;
              if(cat === 'custom-ge') customGe += cr;
              if(cat === 'custom-elective') customElective += cr;
              if(cat === 'custom-free' || cat === 'custom') customFree += cr;
          });
      });
      
      poolGe -= customGe;
      poolElective -= customElective;
      poolFree -= customFree;
      
      // Spillover logic: if they take extra GE, it counts as Free Elective
      if(poolGe < 0) {
          poolFree += poolGe; // poolGe is negative, so this reduces poolFree
          poolGe = 0;
      }
      if(poolElective < 0) {
          poolFree += poolElective;
          poolElective = 0;
      }
      if(poolFree < 0) {
          poolFree = 0; // cannot go below 0
      }
      
      const uiGe = document.getElementById('ui-rem-ge');
      const uiElec = document.getElementById('ui-rem-elec');
      const uiFree = document.getElementById('ui-rem-free');
      
      if(uiGe) uiGe.innerHTML = `<span style="color:var(--kmitl-orange)">${baselineStats.ge - poolGe}</span> / ${baselineStats.ge}`;
      if(uiElec) uiElec.innerHTML = `<span style="color:var(--kmitl-orange)">${baselineStats.elective - poolElective}</span> / ${baselineStats.elective}`;
      if(uiFree) uiFree.innerHTML = `<span style="color:var(--kmitl-orange)">${baselineStats.free - poolFree}</span> / ${baselineStats.free}`;

      // Build map of where each course is currently located across terms
      const courseTermMap = {};
      planTermData.forEach((term, i) => {
          if (term.is_locked) {
              (term.fixed_core_courses || term.core_courses || []).forEach(c => {
                  courseTermMap[c.code] = { termIdx: i, label: term.label };
              });
          } else {
              (term.fixed_core_courses || []).forEach(c => {
                  courseTermMap[c.code] = { termIdx: i, label: term.label };
              });
              const dropzone = document.getElementById(`dropzone-${i}`);
              if (dropzone) {
                  dropzone.querySelectorAll('.draggable-course').forEach(el => {
                      const code = el.dataset.code;
                      if (code) courseTermMap[code] = { termIdx: i, label: term.label };
                  });
              }
          }
      });
      
      let totalAvailableSlots = 0;
      planTermData.forEach((term, i) => {
          const dropzone = document.getElementById(`dropzone-${i}`);
          if(!dropzone) return;
          
          let draggedCoreCredits = 0;
          let draggedNonCoreCredits = 0;
          let draggableCoreCount = 0;

          dropzone.querySelectorAll('.draggable-course').forEach(el => {
              const cr = parseInt(el.dataset.credit || 0);
              if (el.dataset.isCore === "true") {
                  draggedCoreCredits += cr;
                  draggableCoreCount++;
              } else {
                  draggedNonCoreCredits += cr;
              }

              // Dynamic prerequisite notice update
              const container = el.querySelector('.course-prereq-container');
              const rawUnpassed = el.dataset.unpassed;
              if (container && rawUnpassed) {
                  try {
                      const unpassedList = JSON.parse(rawUnpassed);
                      if (unpassedList && unpassedList.length > 0) {
                          container.innerHTML = unpassedList.map(p => {
                              const planLoc = courseTermMap[p.code];
                              let statusTag = '';
                              let warningBg = '#FEF2F2';
                              let warningColor = '#991B1B';
                              let warningBorder = '#FECACA';

                              if (p.is_current) {
                                  statusTag = '<span style="color:#d97706; font-weight:600;">[กำลังเรียนในเทอมนี้]</span>';
                                  warningBg = '#FFFBEB';
                                  warningColor = '#92400E';
                                  warningBorder = '#FDE68A';
                              } else if (planLoc) {
                                  if (planLoc.termIdx >= i) {
                                      statusTag = `<span style="color:#dc2626; font-weight:600;">ต้องเรียนก่อนเทอมนี้! (ปัจจุบันอยู่ใน ${escapeHtml(planLoc.label)})</span>`;
                                  } else {
                                      statusTag = `<span style="color:#16a34a; font-weight:600;">[วางแผนเรียนใน ${escapeHtml(planLoc.label)}]</span>`;
                                      warningBg = '#F0FDF4';
                                      warningColor = '#166534';
                                      warningBorder = '#BBF7D0';
                                  }
                              } else {
                                  statusTag = '<span style="color:#dc2626; font-weight:600;">[ยังไม่ได้เรียน]</span>';
                              }

                              return `
                                <div class="prereq-warning" style="font-size:12px; margin-top:4px; display:inline-flex; align-items:center; gap:6px; background:${warningBg}; color:${warningColor}; border:1px solid ${warningBorder}; border-radius:4px; padding:2px 8px;">
                                  <span>วิชาบังคับก่อน: <strong>${escapeHtml(p.name || p.code)}</strong> (${escapeHtml(p.code)}) ${statusTag}</span>
                                </div>
                              `;
                          }).join('');
                      }
                  } catch (e) {
                      // ignore parse errors
                  }
              }
          });
          
          const currentCoreCredits = (term.fixed_core_credits || 0) + draggedCoreCredits;
          const total = currentCoreCredits + draggedNonCoreCredits;
          const avail = term.max_credits - total;

          if (!term.is_locked) {
              totalAvailableSlots += Math.max(0, avail);
          }
          
          const coreEl = document.getElementById(`term-core-${i}`);
          const totalEl = document.getElementById(`term-total-${i}`);
          const availEl = document.getElementById(`term-avail-${i}`);
          const fill = document.getElementById(`term-fill-${i}`);
          
          if(coreEl) {
              coreEl.textContent = `${currentCoreCredits} นก.`;
          }
          if(totalEl) {
              totalEl.textContent = total;
              totalEl.style.color = total > term.max_credits ? 'var(--danger)' : 'var(--navy-800)';
          }
          if(availEl) {
              availEl.textContent = avail + ' นก.';
              availEl.style.color = avail >= 0 ? 'var(--success)' : 'var(--danger)';
          }
          if(fill) {
              fill.style.width = Math.min((total / term.max_credits) * 100, 100) + '%';
              fill.style.background = total > term.max_credits ? 'var(--danger)' : 'var(--kmitl-orange)';
          }

          // Toggle empty message
          const emptyMsg = dropzone.querySelector('.empty-core-msg');
          if (emptyMsg) {
              const hasCore = (term.fixed_core_courses && term.fixed_core_courses.length > 0) || draggableCoreCount > 0;
              emptyMsg.style.display = hasCore ? 'none' : 'block';
          }
      });

      const uiTotalAvail = document.getElementById('ui-total-avail');
      if (uiTotalAvail) {
          uiTotalAvail.textContent = totalAvailableSlots;
          uiTotalAvail.className = `plan-stat-value ${totalAvailableSlots >= 0 ? 'ok' : 'warn'}`;
      }
  }

  // ===== CUSTOM COURSE MODAL =====
  function openAddCourseModal(idx) {
      document.getElementById('add-course-term-idx').value = idx;
      document.getElementById('add-course-name').value = '';
      document.getElementById('add-course-cat').disabled = false;
      document.getElementById('add-course-modal').classList.add('show');
  }
  function closeAddCourseModal() {
      document.getElementById('add-course-modal').classList.remove('show');
  }
  function confirmAddCourse() {
      const idx = document.getElementById('add-course-term-idx').value;
      const name = document.getElementById('add-course-name').value.trim();
      const credit = parseInt(document.getElementById('add-course-credit').value);
      const catSelect = document.getElementById('add-course-cat');
      const cat = catSelect.value;
      
      if(!name) { alert('กรุณาระบุชื่อวิชา'); return; }
      
      const dropzone = document.getElementById(`dropzone-${idx}`);
      const emptyMsg = dropzone.querySelector('.empty-core-msg');
      if(emptyMsg) emptyMsg.style.display = 'none';
      
      const id = 'custom_' + nextCustomId++;
      const html = `
          <div class="plan-course-row draggable-course sys-course custom-course" draggable="true" id="${id}" data-cat="${escapeHtml(cat)}" data-credit="${credit}" ondragstart="dragStart(event)" ondragend="dragEnd(event)" style="position:relative; border-left:4px solid var(--success);">
            <div class="plan-course-code" style="color:var(--success); font-weight:600;"><span style="position:absolute; left:0; color:var(--text-muted);">⋮⋮</span> เพิ่มเอง</div>
            <div class="plan-course-name">${escapeHtml(name)}</div>
            <span class="plan-badge deferred" style="background:#DCFCE7; color:#166534; border:1px solid #86EFAC;">เพิ่มพิเศษ</span>
            <div class="plan-course-credit">${credit} นก.</div>
            <button class="course-del-btn" onclick="removeCustomCourse(${jsArg(id)})" style="position:static; opacity:1; margin-left:8px; font-size:14px; padding:4px;">ลบ</button>
          </div>
      `;
      dropzone.insertAdjacentHTML('beforeend', html);
      closeAddCourseModal();
      catSelect.disabled = false;
      recalculateAllTerms();
  }
  function removeCustomCourse(id) {
      const el = document.getElementById(id);
      if(el) el.remove();
      recalculateAllTerms();
  }

  function togglePlanTerm(idx) {
    const body = document.getElementById(`plan-body-${idx}`);
    const chev = document.getElementById(`plan-chev-${idx}`);
    if (body.classList.contains('show')) {
      body.classList.remove('show');
      chev.classList.remove('open');
    } else {
      body.classList.add('show');
      chev.classList.add('open');
    }
  }

  // ===== AUTOCOMPLETE LOGIC =====
  let debounceTimer;
  document.addEventListener('DOMContentLoaded', function() {
      const courseInput = document.getElementById('add-course-name');
      if(courseInput) {
          courseInput.addEventListener('input', function(e) {
              clearTimeout(debounceTimer);
              document.getElementById('add-course-cat').disabled = false;
              const val = e.target.value.trim();
              const resultsBox = document.getElementById('autocomplete-results');
              if(val.length < 2) {
                  resultsBox.style.display = 'none';
                  return;
              }
              debounceTimer = setTimeout(() => {
                  requestJson('/api/curriculum/courses?search=' + encodeURIComponent(val))
                      .then(data => {
                          if(!data || data.length === 0) {
                              resultsBox.style.display = 'none';
                              return;
                          }
                          const filteredData = data.filter(c => c.year === null);
                          if(filteredData.length === 0) {
                              resultsBox.style.display = 'none';
                              return;
                          }
                          resultsBox.innerHTML = filteredData.slice(0, 10).map(c => {
                              let catValue = 'custom-elective';
                              if (c.course_code.startsWith('045') || c.course_code.startsWith('145') || c.course_code.startsWith('90')) {
                                  catValue = 'custom-ge';
                              }
                              return `<div class="autocomplete-item" onclick="selectAutocomplete(${jsArg(c.course_code)}, ${jsArg(c.course_name_th)}, ${jsArg(c.course_name_en || '')}, ${c.credit}, ${jsArg(catValue)})">
                                   <strong>${escapeHtml(c.course_code)}</strong> ${escapeHtml(c.course_name_en || c.course_name_th)} (${escapeHtml(c.credit)} นก.)
                                </div>`;
                          }).join('');
                          resultsBox.style.display = 'block';
                      })
                      .catch(e => console.error(e));
              }, 300);
          });
      }
  });

  function selectAutocomplete(code, nameTh, nameEn, credit, catValue) {
      document.getElementById('add-course-name').value = `${code} ${nameEn || nameTh}`;
      document.getElementById('add-course-credit').value = credit;
      const catSelect = document.getElementById('add-course-cat');
      catSelect.value = catValue;
      catSelect.disabled = true;
      document.getElementById('autocomplete-results').style.display = 'none';
  }


/* ===== Withdrawal Impact Modal ===== */
  function openWithdrawModal() {
    const d = window.dashboardData;
    if (!d || !d.in_progress || d.in_progress.length === 0) {
      alert("ไม่มีรายวิชาที่กำลังศึกษาในภาคเรียนปัจจุบัน");
      return;
    }
    const listEl = document.getElementById('withdraw-course-list');
    listEl.innerHTML = d.in_progress.map((c, i) => `
      <button class="course-list-btn" onclick="selectWithdrawCourse(${i})">
        <strong>${escapeHtml(c.code)}</strong> - ${escapeHtml(c.name_en || c.name_th)} (${escapeHtml(c.credit)} นก.)
      </button>
    `).join('');
    document.getElementById('withdraw-impact-result').style.display = 'none';
    document.getElementById('withdraw-modal').classList.add('show');
  }

  function closeWithdrawModal() {
    document.getElementById('withdraw-modal').classList.remove('show');
  }

  function selectWithdrawCourse(idx) {
    const d = window.dashboardData;
    const course = d.in_progress[idx];
    const resEl = document.getElementById('withdraw-impact-result');
    
    let html = `<h4 style="margin-bottom:12px; font-family:'Prompt', sans-serif;">ผลกระทบการถอนวิชา ${escapeHtml(course.code)}</h4>`;
    
    if (course.impacts && course.impacts.length > 0) {
      html += `
        <div class="impact-alert">
          <strong> คำเตือน:</strong> วิชานี้เป็นวิชาบังคับก่อน (Prerequisite) ของรายวิชาต่อไปนี้:
          <ul class="impact-course-list">
            ${course.impacts.map(imp => `<li><strong>${escapeHtml(imp.code)}</strong> - ${escapeHtml(imp.name_en || imp.name_th)}</li>`).join('')}
          </ul>
          <div style="margin-top: 12px; font-size: 14px;">
            หากท่านถอนวิชานี้ ท่านจะไม่สามารถลงทะเบียนวิชาเหล่านี้ได้จนกว่าจะสอบผ่านวิชานี้ในภาคการศึกษาถัดไป ซึ่งอาจส่งผลให้จบการศึกษาล่าช้า
          </div>
        </div>
      `;
    } else {
      html += `
        <div class="impact-safe">
          <strong> ไม่พบผลกระทบต่อเนื่อง:</strong> วิชานี้ไม่ได้เป็นวิชาบังคับก่อน (Prerequisite) ของรายวิชาอื่นในโครงสร้างหลักสูตร 
          <div style="margin-top: 8px; font-size: 14px;">
            ท่านสามารถถอนวิชานี้ได้โดยไม่ปิดกั้นการลงทะเบียนวิชาอื่น อย่างไรก็ตามกรุณาตรวจสอบหน่วยกิตรวมและแผนการศึกษาของท่านอีกครั้ง
          </div>
        </div>
      `;
    }
    
    resEl.innerHTML = html;
    resEl.style.display = 'block';
  }
