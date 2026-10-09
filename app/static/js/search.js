    let allCourses = [];
    const coursesMap = new Map();

    const categoryBadges = {
      "ge": "badge-ge",
      "core_math": "badge-core-math",
      "core_cs": "badge-core-cs",
      "elective": "badge-elective",
      "free": "badge-free",
      "alternative": "badge-alt"
    };

    async function loadCourses() {
      try {
        const data = await requestJson('/api/curriculum');
        
        let courses = [];
        data.forEach(term => {
          term.courses.forEach(c => {
            courses.push(c);
          });
        });
        
        // Remove duplicates if any
        coursesMap.clear();
        courses.forEach(c => {
          coursesMap.set(c.course_code, c);
        });
        allCourses = Array.from(coursesMap.values());

        document.getElementById('loadingBox').style.display = 'none';
        document.getElementById('coursesTable').style.display = 'table';
        
        renderTable();
      } catch (err) {
        document.getElementById('loadingBox').textContent = 'เกิดข้อผิดพลาดในการโหลดข้อมูล';
      }
    }

    function renderTable() {
      const search = document.getElementById('searchInput').value.trim().toLowerCase();
      const cat = document.getElementById('categorySelect').value;
      
      const filtered = allCourses.filter(c => {
        const matchSearch = (c.course_code.toLowerCase().includes(search) || 
                             (c.course_name_th && c.course_name_th.toLowerCase().includes(search)) || 
                             (c.course_name_en && c.course_name_en.toLowerCase().includes(search)));
        
        let matchCat = false;
        if (cat === 'all') {
          matchCat = true;
        } else if (cat === 'has_prereq') {
          matchCat = (c.prerequisites && c.prerequisites.length > 0);
        } else if (cat === 'free') {
          matchCat = ['free', 'ge', 'elective'].includes(c.category);
        } else {
          matchCat = (c.category === cat);
        }

        return matchSearch && matchCat;
      });

      const tbody = document.getElementById('coursesBody');
      tbody.innerHTML = '';
      
      // Update info text if 'free' is selected
      let infoText = document.getElementById('freeElectiveInfo');
      if (!infoText) {
        infoText = document.createElement('div');
        infoText.id = 'freeElectiveInfo';
        infoText.style.marginBottom = '16px';
        infoText.style.fontSize = '14px';
        infoText.style.color = 'var(--text-muted)';
        document.querySelector('.filter-bar').after(infoText);
      }
      
      if (filtered.length === 0) {
        document.getElementById('coursesTable').style.display = 'none';
        document.getElementById('noResultBox').style.display = 'block';
        return;
      }
      
      document.getElementById('coursesTable').style.display = 'table';
      document.getElementById('noResultBox').style.display = 'none';

      filtered.forEach(c => {
        const tr = document.createElement('tr');
        const badgeClass = categoryBadges[c.category] || "badge-free";
        const badgeLabel = c.category_label || "วิชาเลือกเสรี";
        const hasPrereq = c.prerequisites && c.prerequisites.length > 0;
        
        const prereqHtml = hasPrereq 
          ? `<button type="button" class="btn-prereq" onclick="openPrereqModal(${jsArg(c.course_code)})">มีวิชาบังคับก่อน (${c.prerequisites.length})</button>`
          : `<span class="no-prereq">-</span>`;

        tr.innerHTML = `
          <td style="font-family: monospace; color: var(--text-muted);">${escapeHtml(c.course_code)}</td>
          <td style="color: var(--navy-800); font-weight: 500;">
            ${c.url ? `<a href="${escapeHtml(c.url)}" target="_blank" style="color: var(--kmitl-orange); text-decoration: underline;">${escapeHtml(c.course_name_th)}</a>` : escapeHtml(c.course_name_th)}<br>
            <span style="font-size: 13px; color: var(--text-muted); font-weight: 400;">${escapeHtml(c.course_name_en || '')}</span>
          </td>
          <td style="text-align: center; font-weight: 500;">${escapeHtml(c.credit)}</td>
          <td><span class="badge ${badgeClass}">${escapeHtml(badgeLabel)}</span></td>
          <td style="text-align: center;">${prereqHtml}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    function openPrereqModal(courseCode) {
      const course = coursesMap.get(courseCode);
      if (!course) return;

      const targetBox = document.getElementById('modalTargetCourse');
      const badgeClass = categoryBadges[course.category] || "badge-free";
      const badgeLabel = course.category_label || "วิชาเลือกเสรี";

      let planInfo = '';
      if (course.year && course.semester) {
        planInfo = ` • ชั้นปีที่ ${escapeHtml(course.year)} เทอม ${escapeHtml(course.semester)}`;
      }

      targetBox.innerHTML = `
        <div class="target-course-code">${escapeHtml(course.course_code)}</div>
        <div class="target-course-name">${escapeHtml(course.course_name_th)}</div>
        <div class="target-course-en">${escapeHtml(course.course_name_en || '')}</div>
        <div class="target-course-meta">
          <span class="badge ${badgeClass}">${escapeHtml(badgeLabel)}</span>
          <span style="font-size: 13px; color: var(--navy-700); font-weight: 500;">${escapeHtml(course.credit)} หน่วยกิต${planInfo}</span>
        </div>
      `;

      const prereqs = course.prerequisites || [];
      document.getElementById('prereqCountBadge').textContent = `${prereqs.length} รายวิชา`;

      const listContainer = document.getElementById('prereqListContainer');
      listContainer.innerHTML = '';

      if (prereqs.length === 0) {
        listContainer.innerHTML = `<div style="color: var(--text-muted); font-size: 14px; padding: 12px 0;">ไม่มีรายวิชาบังคับก่อน</div>`;
      } else {
        prereqs.forEach(prereqCode => {
          const prereqCourse = coursesMap.get(prereqCode);
          const item = document.createElement('div');
          item.className = 'prereq-item';

          if (prereqCourse) {
            const pBadgeClass = categoryBadges[prereqCourse.category] || "badge-free";
            const pBadgeLabel = prereqCourse.category_label || "วิชาเลือกเสรี";
            item.innerHTML = `
              <div class="prereq-item-header">
                <span class="prereq-code">${escapeHtml(prereqCourse.course_code)}</span>
                <span class="badge ${pBadgeClass}">${escapeHtml(pBadgeLabel)}</span>
              </div>
              <div class="prereq-name-th">${escapeHtml(prereqCourse.course_name_th)}</div>
              <div class="prereq-name-en">${escapeHtml(prereqCourse.course_name_en || '')}</div>
              <div style="font-size: 12px; color: var(--navy-700); margin-top: 4px;">จำนวน ${escapeHtml(prereqCourse.credit)} หน่วยกิต</div>
            `;
          } else {
            item.innerHTML = `
              <div class="prereq-item-header">
                <span class="prereq-code">${escapeHtml(prereqCode)}</span>
                <span class="badge badge-free">รายวิชาในหลักสูตร</span>
              </div>
              <div class="prereq-name-th">รหัสวิชา: ${escapeHtml(prereqCode)}</div>
            `;
          }
          listContainer.appendChild(item);
        });
      }

      document.getElementById('prereqModal').classList.add('show');
      document.addEventListener('keydown', handleEscKey);
    }

    function closePrereqModal() {
      document.getElementById('prereqModal').classList.remove('show');
      document.removeEventListener('keydown', handleEscKey);
    }

    function handleBackdropClick(event) {
      if (event.target.id === 'prereqModal') {
        closePrereqModal();
      }
    }

    function handleEscKey(event) {
      if (event.key === 'Escape') {
        closePrereqModal();
      }
    }

    document.getElementById('searchInput').addEventListener('input', renderTable);
    document.getElementById('categorySelect').addEventListener('change', renderTable);

    window.onload = loadCourses;
