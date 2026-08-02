-- ===========================================================================
-- SmartGrad Database Schema & Initial Seed Data (SQL Script)
-- Database: SQLite / PostgreSQL / MySQL Compatible
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- 1. TABLES CREATION
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS curriculums (
    curriculum_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    course_code VARCHAR(20) PRIMARY KEY,
    curriculum_id VARCHAR(50),
    course_name_th VARCHAR(255) NOT NULL,
    course_name_en VARCHAR(255) NOT NULL,
    credit_str VARCHAR(20),
    credit INTEGER NOT NULL DEFAULT 0,
    year INTEGER,
    semester INTEGER,
    url VARCHAR(500),
    plan_type VARCHAR(100),
    prereq_source VARCHAR(20),
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(curriculum_id)
);


CREATE TABLE IF NOT EXISTS prerequisites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code VARCHAR(20) NOT NULL,
    prereq_code VARCHAR(20) NOT NULL,
    FOREIGN KEY (course_code) REFERENCES courses(course_code) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS advisors (
    advisor_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    cohort_year INTEGER
);

CREATE TABLE IF NOT EXISTS advisor_credentials (
    advisor_id VARCHAR(20) PRIMARY KEY,
    password_hash VARCHAR(128) NOT NULL,
    FOREIGN KEY (advisor_id) REFERENCES advisors(advisor_id)
);

CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    admission_year INTEGER,
    advisor_id VARCHAR(20),
    curriculum_id VARCHAR(50),
    FOREIGN KEY (advisor_id) REFERENCES advisors(advisor_id),
    FOREIGN KEY (curriculum_id) REFERENCES curriculums(curriculum_id)
);

CREATE TABLE IF NOT EXISTS transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE IF NOT EXISTS transcript_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id INTEGER NOT NULL,
    course_code VARCHAR(20) NOT NULL,
    course_name_raw VARCHAR(255) NOT NULL,
    credit INTEGER NOT NULL,
    grade VARCHAR(10),
    is_overridden BOOLEAN DEFAULT 0,
    FOREIGN KEY (transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE,
    FOREIGN KEY (course_code) REFERENCES courses(course_code)
);

CREATE TABLE IF NOT EXISTS advisor_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advisor_id VARCHAR(20) NOT NULL,
    student_id VARCHAR(20) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (advisor_id) REFERENCES advisors(advisor_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);



-- ---------------------------------------------------------------------------
-- 2. SEED DATA FOR CURRICULUMS & COURSES (หลักสูตร วท.บ. วิทยาการคอมพิวเตอร์ สจล. 2564)
-- ---------------------------------------------------------------------------

INSERT OR IGNORE INTO curriculums (curriculum_id, name, year) VALUES
('CS2564', 'วิทยาการคอมพิวเตอร์', 2564);

INSERT OR IGNORE INTO courses (course_code, curriculum_id, course_name_th, course_name_en, credit_str, credit, year, semester, plan_type, prereq_source) VALUES
-- Year 1 Semester 1
('05506232', 'CS2564', 'คณิตศาสตร์สำหรับวิทยาการคอมพิวเตอร์', 'MATHEMATICS FOR COMPUTER SCIENCE', '3(2-2-5)', 3, 1, 1, NULL, NULL),
('05506231', 'CS2564', 'สถิติและความน่าจะเป็น', 'STATISTICS AND PROBABILITY', '3(3-0-6)', 3, 1, 1, NULL, NULL),
('05506003', 'CS2564', 'การเขียนโปรแกรมขั้นพื้นฐาน', 'PROGRAMMING FUNDAMENTALS', '3(2-2-5)', 3, 1, 1, NULL, NULL),
('05506005', 'CS2564', 'วิทยาการคอมพิวเตอร์', 'COMPUTER SCIENCE', '3(2-2-5)', 3, 1, 1, NULL, NULL),
('90644007', 'CS2564', 'ภาษาอังกฤษพื้นฐาน 1', 'FOUNDATION ENGLISH 1', '3(3-0-6)', 3, 1, 1, NULL, NULL),
('90641007', 'CS2564', 'ความฉลาดทางดิจิทัล', 'DIGITAL CITIZEN', '3(3-0-6)', 3, 1, 1, NULL, NULL),
('90642999', 'CS2564', 'โรงเรียนสร้างเสน่ห์', 'CHARM SCHOOL', '2(1-2-3)', 2, 1, 1, NULL, NULL),

-- Year 1 Semester 2
('05506233', 'CS2564', 'แคลคูลัสสำหรับวิทยาการคอมพิวเตอร์', 'CALCULUS FOR COMPUTER SCIENCE', '3(2-2-5)', 3, 1, 2, NULL, NULL),
('05506001', 'CS2564', 'คณิตศาสตร์ดิสครีต', 'DISCRETE MATHEMATICS', '3(3-0-6)', 3, 1, 2, NULL, NULL),
('05506004', 'CS2564', 'การเขียนโปรแกรมเชิงออบเจกต์', 'OBJECT-ORIENTED PROGRAMMING', '3(2-2-5)', 3, 1, 2, NULL, 'official'),
('05506008', 'CS2564', 'โครงสร้างและสถาปัตยกรรมคอมพิวเตอร์', 'COMPUTER ORGANIZATION AND ARCHITECT', '3(3-0-6)', 3, 1, 2, NULL, NULL),
('05506011', 'CS2564', 'ปฏิสัมพันธ์ระหว่างมนุษย์และคอมพิวเตอร์', 'HUMAN-COMPUTER INTERACTION', '3(3-0-6)', 3, 1, 2, NULL, NULL),
('90644008', 'CS2564', 'ภาษาอังกฤษพื้นฐาน 2', 'FOUNDATION ENGLISH 2', '3(3-0-6)', 3, 1, 2, NULL, 'draft'),

-- Year 2 Semester 1
('05506250', 'CS2564', 'พีชคณิตเชิงเส้นสำหรับวิทยาการคอมพิวเตอร์', 'LINEAR ALGEBRA FOR COMPUTER SCIENCE', '3(3-0-6)', 3, 2, 1, NULL, NULL),
('05506006', 'CS2564', 'โครงสร้างข้อมูลและขั้นตอนวิธี', 'DATA STRUCTURES AND ALGORITHMS', '3(2-2-5)', 3, 2, 1, NULL, 'draft'),
('05506007', 'CS2564', 'ระบบปฏิบัติการ', 'OPERATING SYSTEMS', '3(2-2-5)', 3, 2, 1, NULL, 'draft'),
('05506012', 'CS2564', 'ระบบฐานข้อมูล', 'DATABASE SYSTEMS', '3(2-2-5)', 3, 2, 1, NULL, NULL),
('05506234', 'CS2564', 'การวิเคราะห์และจัดการกระบวนการทางธุรกิจ', 'BUSINESS ANALYSIS AND PROCESS MANAGEMENT', '3(3-0-6)', 3, 2, 1, NULL, NULL),
('05506238', 'CS2564', 'สัมมนาด้านเทคโนโลยีแพลตฟอร์มสมัยใหม่', 'SEMINAR IN MODERN PLATFORM TECHNOLOGIES', '1(0-3-2)', 1, 2, 1, NULL, NULL),

-- Year 2 Semester 2
('05506002', 'CS2564', 'กรรมวิธีคำนวณเชิงตัวเลข', 'METHODS OF NUMERICAL COMPUTATION', '3(2-2-5)', 3, 2, 2, NULL, 'draft'),
('05506236', 'CS2564', 'การวิเคราะห์และการออกแบบขั้นตอนวิธี', 'ANALYSIS AND DESIGN OF ALGORITHMS', '3(2-2-5)', 3, 2, 2, NULL, 'official'),
('05506113', 'CS2564', 'การวิเคราะห์และออกแบบซอฟต์แวร์', 'SOFTWARE ANALYSIS AND DESIGN', '3(3-0-6)', 3, 2, 2, NULL, 'draft'),
('05506235', 'CS2564', 'การจัดการนวัตกรรมดิจิทัลและเทคโนโลยีในยุคการเปลี่ยนแปลงอย่างรวดเร็ว', 'DIGITAL INNOVATION AND TECHNOLOGY MANAGEMENT IN DISRUPTIVE ERA', '3(3-0-6)', 3, 2, 2, NULL, NULL),
('05506014', 'CS2564', 'คอมพิวเตอร์กราฟิกส์', 'COMPUTER GRAPHICS', '3(3-0-6)', 3, 2, 2, NULL, 'draft'),

-- Year 3 Semester 1
('05506210', 'CS2564', 'ปัญญาประดิษฐ์', 'ARTIFICIAL INTELLIGENCE', '3(3-0-6)', 3, 3, 1, NULL, 'draft'),
('05506017', 'CS2564', 'วิศวกรรมซอฟต์แวร์', 'SOFTWARE ENGINEERING', '3(3-0-6)', 3, 3, 1, NULL, 'official'),
('05506016', 'CS2564', 'การสื่อสารข้อมูลและระบบเครือข่าย', 'DATA COMMUNICATION AND NETWORK SYSTEMS', '3(3-0-6)', 3, 3, 1, NULL, 'draft'),
('05506237', 'CS2564', 'แนวคิดและตัวแบบของภาษาโปรแกรม', 'PROGRAMMING LANGUAGE CONCEPTS AND PARADIGMS', '3(2-2-5)', 3, 3, 1, NULL, 'draft'),
('05506239', 'CS2564', 'โครงงานเชิงปฏิบัติ', 'PRACTICAL PROJECT', '1(0-3-2)', 1, 3, 1, NULL, NULL),

-- Year 3 Semester 2
('05506015', 'CS2564', 'จรรยาบรรณทางวิชาชีพและเชิงสังคม', 'COMPUTER ETHICS: SOCIAL AND PROFESSIONAL ISSUES', '3(3-0-6)', 3, 3, 2, NULL, NULL),
('05506018', 'CS2564', 'สัมมนา', 'SEMINAR', '1(0-3-2)', 1, 3, 2, NULL, NULL),

-- Year 4 Semester 1 – Normal Plan
('05506098', 'CS2564', 'ปัญหาพิเศษ 1', 'SPECIAL PROBLEM 1', '3(0-6-3)', 3, 4, 1, 'แผนปกติ (Normal Plan)', 'draft'),

-- Year 4 Semester 1 – Co-op Plan
('05506117', 'CS2564', 'สหกิจศึกษา', 'COOPERATIVE EDUCATION', '6(0-45-0)', 6, 4, 1, 'แผนสหกิจศึกษา/ฝึกงานต่างประเทศ (Co-op / Overseas Training Plan)', NULL),
('05506118', 'CS2564', 'การปฏิบัติการฝึกงานต่างประเทศ', 'OVERSEAS TRAINING', '6(0-45-0)', 6, 4, 1, 'แผนสหกิจศึกษา/ฝึกงานต่างประเทศ (Co-op / Overseas Training Plan)', NULL),

-- Year 4 Semester 2 – Normal Plan
('05506099', 'CS2564', 'ปัญหาพิเศษ 2', 'SPECIAL PROBLEM 2', '3(0-6-3)', 3, 4, 2, 'แผนปกติ (Normal Plan)', 'draft');

-- ---------------------------------------------------------------------------
-- 3. SEED DATA FOR PREREQUISITES
-- ---------------------------------------------------------------------------

INSERT OR IGNORE INTO prerequisites (course_code, prereq_code) VALUES
('05506004', '05506003'), -- Object-Oriented Programming requires Programming Fundamentals
('05506099', '05506098'), -- Special Problem 2 requires Special Problem 1
('05506227', '05506003'), -- Advanced Programming requires Programming Fundamentals
('05506240', '05506012'), -- Data Engineering requires Database Systems
('05506241', '05506003'), -- Data Science Track requires Programming Fundamentals
('05506242', '05506004'); -- Full-Stack Track requires Object-Oriented Programming

-- ---------------------------------------------------------------------------
-- 4. DEMO ADVISOR ACCOUNT
-- ADVISOR001 is responsible for students admitted in academic year 2567
-- Password: smartgrad-demo (SHA-256 hash)
-- ---------------------------------------------------------------------------

INSERT OR IGNORE INTO advisors (advisor_id, name, email, cohort_year) VALUES
('ADVISOR001', 'อาจารย์ที่ปรึกษา Demo', 'advisor.demo@kmitl.ac.th', 2567);

-- update existing demo database created before cohort_year was introduced
UPDATE advisors SET cohort_year = 2567 WHERE advisor_id = 'ADVISOR001';

INSERT OR IGNORE INTO advisor_credentials (advisor_id, password_hash) VALUES
('ADVISOR001', '078ee266aebf60902e9bec6f75496444a0b89324c84f830bc7de7655dea5b557');

-- ---------------------------------------------------------------------------
-- 5. SEED DATA FOR GENED COURSES
-- ---------------------------------------------------------------------------

INSERT OR IGNORE INTO courses (course_code, curriculum_id, course_name_th, course_name_en, credit, url) VALUES
('90642217', 'CS2564', 'การคิดเชิงออกแบบเพื่อความยั่งยืน', 'DESIGN THINKING FOR SUSTAINABILITY', 3, 'https://gened.kmitl.ac.th/subjectge/90642217/'),
('90643049', 'CS2564', 'ปัญญาประดิษฐ์เพื่อทุกคน', 'AI FOR EVERYONE', 3, 'https://gened.kmitl.ac.th/subjectge/90643049/'),
('90644071', 'CS2564', 'ภาษามือเบื้องต้นเพื่อการสื่อสาร', 'Introduction To Sign Language For Communication', 3, 'https://gened.kmitl.ac.th/subjectge/90644071/'),
('90642200', 'CS2564', 'ดาราโหราศาสตร์', 'Astrology', 3, 'https://gened.kmitl.ac.th/subjectge/90642200/'),
('90642199', 'CS2564', 'บูรณาการงานสร้างสรรค์ทางศิลปะและการออกแบบ', 'Integrated Creative Art And Design', 3, 'https://gened.kmitl.ac.th/subjectge/90642199/'),
('90642198', 'CS2564', 'ขับร้องประสานเสียง', 'Chorus', 3, 'https://gened.kmitl.ac.th/subjectge/90642198/'),
('90641006', 'CS2564', 'โครงงานกลุ่ม 3', 'TEAM-PROJECT 3', 1, 'https://gened.kmitl.ac.th/subjectge/90641006/'),
('90641005', 'CS2564', 'โครงงานกลุ่ม 2', 'TEAM-PROJECT 2', 1, 'https://gened.kmitl.ac.th/subjectge/90641005/'),
('90641004', 'CS2564', 'โครงงานกลุ่ม 1', 'TEAM-PROJECT 1', 1, 'https://gened.kmitl.ac.th/subjectge/90641004/'),
('90642211', 'CS2564', 'เขียนโค้ดด้วยไพทอน', 'CODING WITH PYTHON', 3, 'https://gened.kmitl.ac.th/subjectge/90642211/'),
('90644888', 'CS2564', 'พรีเซ้นต์อย่างไร ให้โดนใจผู้ฟัง', 'PRESENT LIKE A PRO', 3, 'https://gened.kmitl.ac.th/subjectge/90644888/'),
('90643888', 'CS2564', 'การเงินและการลงทุนในยุคดิจิทัล', 'Digital Era Finance and Investment', 3, 'https://gened.kmitl.ac.th/subjectge/90643888/'),
('90642888', 'CS2564', 'อินเลิฟ อินไลฟ์', 'IN LOVE & IN LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642888/'),
('90642216', 'CS2564', 'ออกแบบประสบการณ์และส่วนต่อประสานผู้ใช้เชิงสร้างสรรค์', 'CREATIVE UX/UI DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90642216/'),
('90642215', 'CS2564', 'ล้างหนี้', 'DEBT DETOX', 3, 'https://gened.kmitl.ac.th/subjectge/90642215/'),
('90642214', 'CS2564', 'การออกแบบอาหารและโภชนาการเบื้องต้น', 'BASIC FOOD DESIGN AND NUTRITION', 3, 'https://gened.kmitl.ac.th/subjectge/90642214/'),
('90642213', 'CS2564', 'เทคโนโลยีเครื่องดื่มไม่มีแอลกอฮอล์', 'NON ALCOHOLIC BEVERAGE', 3, 'https://gened.kmitl.ac.th/subjectge/90642213/'),
('90642212', 'CS2564', 'วิทยาศาสตร์เบื้องหลังอาหาร', 'SCIENCES BEHIND FOOD', 3, 'https://gened.kmitl.ac.th/subjectge/90642212/'),
('90643048', 'CS2564', 'การคำนวณเชิงธุรกิจและการแสดงข้อมูลเชิงธุรกิจด้วยแผนภาพ', 'BUSINESS COMPUTING AND VISUALIZATION', 3, 'https://gened.kmitl.ac.th/subjectge/90643048/'),
('90643047', 'CS2564', 'กองทุนรวมสำหรับมือใหม่', 'MUTUAL FUND FOR ROOKIE', 3, 'https://gened.kmitl.ac.th/subjectge/90643047/'),
('90643046', 'CS2564', 'การสร้างจิตสำนึกของความยั่งยืน', 'RAISING OF SUSTAINABLE AWARENESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643046/'),
('90642210', 'CS2564', 'น้องแมวที่รัก', 'MY CAT’S MY BOSS', 3, 'https://gened.kmitl.ac.th/subjectge/90642210/'),
('90642209', 'CS2564', 'น้องหมาที่รัก', 'MY DOG’S MY BOSS', 3, 'https://gened.kmitl.ac.th/subjectge/90642209/'),
('90642208', 'CS2564', 'ปั้นเดฟให้เป็นดาว', 'FROM DEV TO THE MOON', 3, 'https://gened.kmitl.ac.th/subjectge/90642208/'),
('90642207', 'CS2564', 'เรียนรู้อยู่กับเพื่อนคู่ใจ', 'A GOOD LIFE PARTNER', 3, 'https://gened.kmitl.ac.th/subjectge/90642207/'),
('90642206', 'CS2564', 'พลังรัก', 'LOVE AND PASSION', 3, 'https://gened.kmitl.ac.th/subjectge/90642206/'),
('90642205', 'CS2564', 'ภัยไซเบอร์และการรักษาความปลอดภัย', 'CYBER THREATS AND SECURITY', 3, 'https://gened.kmitl.ac.th/subjectge/90642205/'),
('90642204', 'CS2564', 'ความสัมพันธ์ที่ดี', 'HEALTHY RELATIONSHIP', 3, 'https://gened.kmitl.ac.th/subjectge/90642204/'),
('90642203', 'CS2564', 'ยิ้มนี้เพื่อเธอ', 'MIRACLE SMILE', 3, 'https://gened.kmitl.ac.th/subjectge/90642203/'),
('90641001', 'CS2564', 'โรงเรียนสร้างเสน่ห์', 'CHARM SCHOOL', 3, 'https://gened.kmitl.ac.th/subjectge/90641001/'),
('90641007', 'CS2564', 'พลเมืองดิจิทัล', 'DIGITAL CITIZEN', 3, 'https://gened.kmitl.ac.th/subjectge/90641007/'),
('90641003', 'CS2564', 'กีฬาและนันทนาการ', 'SPORTS AND RECREATIONAL ACTIVITIES', 1, 'https://gened.kmitl.ac.th/subjectge/90641003/'),
('90641009', 'CS2564', 'ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 1', 'INTERCULTURAL COMMUNICATION  SKILLS IN ENGLISH 1', 3, 'https://gened.kmitl.ac.th/subjectge/90641009/'),
('90641010', 'CS2564', 'ทักษะการสื่อสารภาษาอังกฤษระหว่างวัฒนธรรม 2', 'INTERCULTURAL COMMUNICATION  SKILLS IN ENGLISH 2', 3, 'https://gened.kmitl.ac.th/subjectge/90641010/'),
('90642001', 'CS2564', 'ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 1', 'PRACTICE UNDER PERSONAL AND PROFESSIONAL SKILLS 1', 1, 'https://gened.kmitl.ac.th/subjectge/90642001/'),
('90642002', 'CS2564', 'ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 2', 'PRACTICE UNDER PERSONAL AND PROFESSIONAL SKILLS 2', 2, 'https://gened.kmitl.ac.th/subjectge/90642002/'),
('90642003', 'CS2564', 'ปฏิบัติงานตามทักษะด้านบุคคลและสนับสนุนวิชาชีพ 3', 'PRACTICE UNDER PERSONAL AND PROFESSIONAL SKILLS 3', 3, 'https://gened.kmitl.ac.th/subjectge/90642003/'),
('90642011', 'CS2564', 'การคิดอย่างมีวิจารณญาณ', 'CRITICAL THINKING', 3, 'https://gened.kmitl.ac.th/subjectge/90642011/'),
('90642012', 'CS2564', 'กระบวนการคิดเชิงออกแบบ', 'DESIGN THINKING', 3, 'https://gened.kmitl.ac.th/subjectge/90642012/'),
('90642013', 'CS2564', 'บูรณาการแห่งการคิด', 'INTEGRATED THINKING', 3, 'https://gened.kmitl.ac.th/subjectge/90642013/'),
('90642014', 'CS2564', 'การคิดเชิงระบบและเชิงนวัตกรรม', 'INNOVATIVE AND SYSTEM THINKING', 3, 'https://gened.kmitl.ac.th/subjectge/90642014/'),
('90642015', 'CS2564', 'การคิดสร้างสรรค์และนวัตกรรม', 'CREATIVE THINKING AND INNOVATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642015/'),
('90642017', 'CS2564', 'แกะกล่องนวัตกรรม', 'INNOVATION UNBOXED', 3, 'https://gened.kmitl.ac.th/subjectge/90642017/'),
('90642018', 'CS2564', 'เทคโนโลยีการผลิตงานสร้างสรรค์', 'CREATIVE PRODUCTION TECHNOLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642018/'),
('90642019', 'CS2564', 'การออกแบบสะเต็มอย่างสร้างสรรค์ขั้นพื้นฐาน', 'BASIC CREATIVE STEM DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90642019/'),
('90642020', 'CS2564', 'การออกแบบสะเต็มอย่างสร้างสรรค์ ขั้ั้นสูง', 'ADVANCE CREATIVE STEM DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90642020/'),
('90642021', 'CS2564', 'ไอเดียขยะ', 'JUNK DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90642021/'),
('90642022', 'CS2564', 'ปรัชญาวิทยาศาสตร์', 'PHILOSOPHY OF SCIENCE', 3, 'https://gened.kmitl.ac.th/subjectge/90642022/'),
('90642024', 'CS2564', 'การวิเคราะห์ข้อมูลทางวิชาชีพและการนำเสนอทางวิชาการ', 'PROFESSIONAL INFORMATION ANALYSIS AND ACADEMIC PRESENTATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642024/'),
('90642025', 'CS2564', 'วิเคราะห์ความจริงจากตัวเลข', 'FACTS BEHIND NUMBERS', 3, 'https://gened.kmitl.ac.th/subjectge/90642025/'),
('90642026', 'CS2564', 'การพัฒนาทักษะเชิงวิจัย', 'RESEARCH SKILL DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642026/'),
('90642028', 'CS2564', 'รู้เท่าทันการพนัน', 'GAMBLING LITERACY', 3, 'https://gened.kmitl.ac.th/subjectge/90642028/'),
('90642029', 'CS2564', 'จริยธรรมและกฎหมายว่าด้วยความเป็นมืออาชีพทางการแพทย์', 'MEDICAL ETHICS, LAWS AND PROFESSIONALISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642029/'),
('90642030', 'CS2564', 'จรรยาบรรณและกฎหมายวิศวกรรม', 'ENGINEERING ETHICS AND LAW', 3, 'https://gened.kmitl.ac.th/subjectge/90642030/'),
('90642031', 'CS2564', 'จริยธรรมและกฎหมายแห่งวิชาชีพ', 'PROFESSIONAL ETHICS AND LAWS', 3, 'https://gened.kmitl.ac.th/subjectge/90642031/'),
('90642032', 'CS2564', 'กฎหมายสำหรับผู้ประกอบการ', 'LAW FOR ENTREPRENEURS', 3, 'https://gened.kmitl.ac.th/subjectge/90642032/'),
('90642033', 'CS2564', 'กฎหมายสำหรับคนรุ่นใหม่', 'LAW FOR NEW GENERATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642033/'),
('90642034', 'CS2564', 'กฎหมายและระเบียบในอุตสาหกรรมการบิน', 'LAW AND REGULATION IN AVIATION INDUSTRY', 3, 'https://gened.kmitl.ac.th/subjectge/90642034/'),
('90642035', 'CS2564', 'ประสบการณ์ในอุตสาหกรรมสำหรับวิศวกร', 'INDUSTRIAL EXPERIENCE FOR ENGINEERS', 3, 'https://gened.kmitl.ac.th/subjectge/90642035/'),
('90642036', 'CS2564', 'เตรียมความพร้อมสำหรับวิศวกร', 'PRE-ACTIVITIES FOR ENGINEERS', 1, 'https://gened.kmitl.ac.th/subjectge/90642036/'),
('90642037', 'CS2564', 'ประเด็นและทักษะวิชาชีพ', 'PROFESSIONAL SKILLS AND ISSUES', 3, 'https://gened.kmitl.ac.th/subjectge/90642037/'),
('90642038', 'CS2564', 'ความปลอดภัยในที่ทำงาน', 'OCCUPATIONAL SAFETY AND HEALTH', 3, 'https://gened.kmitl.ac.th/subjectge/90642038/'),
('90642039', 'CS2564', 'ซ่อมได้ภายในบ้าน', 'QUICK-FIX @ HOME', 3, 'https://gened.kmitl.ac.th/subjectge/90642039/'),
('90642040', 'CS2564', 'คอกาแฟ', 'COFFEE MANIA', 3, 'https://gened.kmitl.ac.th/subjectge/90642040/'),
('90642041', 'CS2564', 'ครัวเด็กหอ', 'DORM CHEF', 3, 'https://gened.kmitl.ac.th/subjectge/90642041/'),
('90642042', 'CS2564', 'ศาสตร์และศิลป์ของเนื้อสัตว์', 'SCIENCE AND ART OF MEATS', 3, 'https://gened.kmitl.ac.th/subjectge/90642042/'),
('90642043', 'CS2564', 'ศาสตร์ของเบอร์เกอร์', 'SCIENCE OF BURGER', 3, 'https://gened.kmitl.ac.th/subjectge/90642043/'),
('90642044', 'CS2564', 'โลกของไส้กรอก', 'WORLD OF SAUSAGES', 3, 'https://gened.kmitl.ac.th/subjectge/90642044/'),
('90642045', 'CS2564', 'เรื่องเหล้า', 'BE MY BEV.', 3, 'https://gened.kmitl.ac.th/subjectge/90642045/'),
('90642046', 'CS2564', 'ไร้ซ์-สาระ', 'RICE-SARA', 3, 'https://gened.kmitl.ac.th/subjectge/90642046/'),
('90642047', 'CS2564', 'หมอต้นไม้', 'TREE DOCTOR', 3, 'https://gened.kmitl.ac.th/subjectge/90642047/'),
('90642048', 'CS2564', 'ยาและสมุนไพรพาเพลิน', 'FUN WITH DRUGS AND HERBS', 3, 'https://gened.kmitl.ac.th/subjectge/90642048/'),
('90642049', 'CS2564', 'การใช้ประโยชน์จากจุลินทรีย์ในชีวิตประจำวัน', 'MICROBIAL UTILIZATION FOR DAILY LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642049/'),
('90642050', 'CS2564', 'พืชพรรณที่เป็นยา', 'MEDICINAL PLANTS', 3, 'https://gened.kmitl.ac.th/subjectge/90642050/'),
('90642051', 'CS2564', 'เทคโนโลยีชีวภาพเพื่อความเป็นอยู่ที่ดีขึ้น', 'BIOTECHNOLOGY FOR BETTER LIVING', 3, 'https://gened.kmitl.ac.th/subjectge/90642051/'),
('90642052', 'CS2564', 'จากเส้นสาย DNA สู่พันธุกรรม', 'GENES & GENETICS : FROM HELIX TO HEREDITARY', 3, 'https://gened.kmitl.ac.th/subjectge/90642052/'),
('90642053', 'CS2564', 'สาระน่ารู้อณูพันธุศาสตร์', 'INTERESTING MOLECULAR GENETICS', 3, 'https://gened.kmitl.ac.th/subjectge/90642053/'),
('90642054', 'CS2564', 'สิ่งพิทักษ์ร่างกาย', 'GUARDIANS OF OUR BODIES', 3, 'https://gened.kmitl.ac.th/subjectge/90642054/'),
('90642055', 'CS2564', 'จุลินทรีย์ร่วมชีพ', 'LIVING WITH MICROBES', 3, 'https://gened.kmitl.ac.th/subjectge/90642055/'),
('90642056', 'CS2564', 'โรคระบาดในศตวรรษที่ 21', 'EPIDEMICS IN THE 21st CENTURY', 3, 'https://gened.kmitl.ac.th/subjectge/90642056/'),
('90642057', 'CS2564', 'ภูมิคุ้มกาย', 'IMMUNITY THROUGH MEDIA', 3, 'https://gened.kmitl.ac.th/subjectge/90642057/'),
('90642058', 'CS2564', 'ความเข้าใจในนโยบายสุขภาพและสวัสดิภาพของประชาชน', 'Understanding health policy and public welfare', 3, 'https://gened.kmitl.ac.th/subjectge/90642058/'),
('90642059', 'CS2564', 'การแพทย์และวรรณกรรม', 'MEDICINE AND LITERATURE', 3, 'https://gened.kmitl.ac.th/subjectge/90642059/'),
('90642060', 'CS2564', 'ค้นหาตัวตน', 'SELF-DISCOVERY', 3, 'https://gened.kmitl.ac.th/subjectge/90642060/'),
('90642061', 'CS2564', 'โลกของแมลง', 'WORLD OF INSECTS', 3, 'https://gened.kmitl.ac.th/subjectge/90642061/'),
('90642062', 'CS2564', 'เรื่องกินเรื่องใหญ่', 'ALL ABOUT FOOD', 3, 'https://gened.kmitl.ac.th/subjectge/90642062/'),
('90642063', 'CS2564', 'การพัฒนาสุขภาพแบบองค์รวม', 'HOLISTIC HEALTH DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642063/'),
('90642074', 'CS2564', 'อีสปอร์ต', 'E-SPORTS', 3, 'https://gened.kmitl.ac.th/subjectge/90642074/'),
('90642080', 'CS2564', 'การประพันธ์เพลงเบื้องต้น', 'INTRODUCTION TO MUSIC COMPOSITION', 3, 'https://gened.kmitl.ac.th/subjectge/90642080/'),
('90642081', 'CS2564', 'สุนทรียะเพลงแรป', 'RAP APPRECIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642081/'),
('90642082', 'CS2564', 'สุนทรียะดนตรี', 'MUSIC APPRECIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642082/'),
('90642083', 'CS2564', 'ศิลปะแห่งภาพยนตร์', 'FILM APPRECIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642083/'),
('90642084', 'CS2564', 'สุนทรียะภาพถ่าย', 'PHOTOGRAPHY APPRECIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642084/'),
('90642085', 'CS2564', 'วัฒนธรรมร่วมสมัย', 'CONTEMPORARY CULTURE', 3, 'https://gened.kmitl.ac.th/subjectge/90642085/'),
('90642086', 'CS2564', 'วัฒนธรรมการออกแบบเบื้องต้น', 'INTRODUCTION TO DESIGN CULTURE', 3, 'https://gened.kmitl.ac.th/subjectge/90642086/'),
('90642087', 'CS2564', 'วัฒนธรรมรอบโลก', 'WORLD CULTURE', 3, 'https://gened.kmitl.ac.th/subjectge/90642087/'),
('90642088', 'CS2564', 'วัฒนธรรมจีนดั้งเดิม', 'TRADITIONAL CHINESE CULTURE', 3, 'https://gened.kmitl.ac.th/subjectge/90642088/'),
('90642089', 'CS2564', 'สังคม เศรษฐกิจ และการเมืองจีน', 'CHINESE SOCIETY, ECONOMY AND POLITICS', 3, 'https://gened.kmitl.ac.th/subjectge/90642089/'),
('90642090', 'CS2564', 'เจาะลึกประเด็นโลก', 'GLOBAL INSIDE', 3, 'https://gened.kmitl.ac.th/subjectge/90642090/'),
('90642091', 'CS2564', 'เอเชียนศึกษา', 'ASIAN STUDY', 3, 'https://gened.kmitl.ac.th/subjectge/90642091/'),
('90642092', 'CS2564', 'การศึกษาเพื่อสร้างพลเมือง', 'CIVIC EDUCATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642092/'),
('90642093', 'CS2564', 'สานสัมพันธ์กับชุมชน', 'COMMUNITY ENGAGEMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642093/'),
('90642094', 'CS2564', 'หลักการพัฒนาชุมชน', 'PRINCIPLES OF COMMUNITY DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642094/'),
('90642095', 'CS2564', 'การพัฒนาความมั่นคงแห่งชาติ', 'NATIONAL SECURITY DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642095/'),
('90642096', 'CS2564', 'วิทยาการทางทหาร', 'MILITARY SCIENCE', 3, 'https://gened.kmitl.ac.th/subjectge/90642096/'),
('90642097', 'CS2564', 'ภูมิปัญญาไทยประยุกต์', 'APPLIED THAI WISDOMS', 3, 'https://gened.kmitl.ac.th/subjectge/90642097/'),
('90642098', 'CS2564', 'พลวัตสังคมไทย', 'DYNAMICS OF THAI SOCIETY', 3, 'https://gened.kmitl.ac.th/subjectge/90642098/'),
('90642099', 'CS2564', 'สังคมสูงวัยเชิงรุก', 'ACTIVE AGING SOCIETY', 3, 'https://gened.kmitl.ac.th/subjectge/90642099/'),
('90642101', 'CS2564', 'นักรีวิว', 'REVIEWER', 3, 'https://gened.kmitl.ac.th/subjectge/90642101/'),
('90642102', 'CS2564', 'นักสื่อสารผ่านยูทูบ', 'YOUTUBER', 3, 'https://gened.kmitl.ac.th/subjectge/90642102/'),
('90642103', 'CS2564', 'การดำรงชีพในสังคมดิจิทัล', 'LIVING IN DIGITAL SOCIETY', 3, 'https://gened.kmitl.ac.th/subjectge/90642103/'),
('90642106', 'CS2564', 'เล่าเรื่องการเดินทางแบบดิจิทัล', 'DIGITAL STORYTELLING IN JOURNEY', 3, 'https://gened.kmitl.ac.th/subjectge/90642106/'),
('90642107', 'CS2564', 'การผลิตสื่อดิจิทัล', 'DIGITAL MEDIA PRODUCTION', 3, 'https://gened.kmitl.ac.th/subjectge/90642107/'),
('90642108', 'CS2564', 'เทคโนโลยีการถ่ายภาพดิจิทัล', 'DIGITAL PHOTOGRAPHY TECHNOLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642108/'),
('90642109', 'CS2564', 'การออกแบบอินโฟกราฟิก', 'INFOGRAPHIC DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90642109/'),
('90642110', 'CS2564', 'สนุกกับวิทยาศาสตร์ข้อมูล', 'FUN WITH DATA SCIENCE', 3, 'https://gened.kmitl.ac.th/subjectge/90642110/'),
('90642111', 'CS2564', 'สนุกกับการเขียนโค้ด', 'FUN WITH CODING', 3, 'https://gened.kmitl.ac.th/subjectge/90642111/'),
('90642112', 'CS2564', 'สนุกกับปัญญาประดิษฐ์', 'FUN WITH AI', 3, 'https://gened.kmitl.ac.th/subjectge/90642112/'),
('90642113', 'CS2564', 'หุ่นยนต์และปัญญาประดิษฐ์', 'ROBOTICS AND AI', 3, 'https://gened.kmitl.ac.th/subjectge/90642113/'),
('90642114', 'CS2564', 'ฟาร์มอัจฉริยะ', 'SMART FARMING', 3, 'https://gened.kmitl.ac.th/subjectge/90642114/'),
('90642115', 'CS2564', 'เทคโนโลยีสีเขียวและพลังงานทดแทน', 'GREEN TECHNOLOGY AND ALTERNATIVE ENERGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642115/'),
('90642116', 'CS2564', 'เมืองอัจฉริยะและนวัตกรรมเมือง', 'SMART CITY AND CITY INNOVATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642116/'),
('90642117', 'CS2564', 'ทักษะการรู้สารสนเทศแห่งศตวรรษที่ 21', 'INFORMATION LITERACY SKILLS FOR THE 21st CENTURY', 3, 'https://gened.kmitl.ac.th/subjectge/90642117/'),
('90642118', 'CS2564', 'โปรแกรมคอมพิวเตอร์ประยุกต์ทางธุรกิจ', 'APPLICATION SOFTWARE FOR BUSINESS', 2, 'https://gened.kmitl.ac.th/subjectge/90642118/'),
('90642120', 'CS2564', 'เอ็กเซลเพื่อความเป็นมืออาชีพ', 'FROM EXCEL TO EXCELLENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642120/'),
('90642121', 'CS2564', 'การวิเคราะห์และจัดการข้อมูลด้วยโปรแกรมคอมพิวเตอร์', 'DATA ANALYSIS AND MANAGEMENT WITH COMPUTATIONAL PROGRAM', 3, 'https://gened.kmitl.ac.th/subjectge/90642121/'),
('90642122', 'CS2564', 'การใช้แอปพลิเคชัน ไมโครคอมพิวเตอร์', 'INTRODUCTION TO MICROCOMPUTER APPLICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642122/'),
('90642123', 'CS2564', 'เทคโนโลยี คอมพิวเตอร์ดนตรี', 'TECHNOLOGY IN MUSICAL SEQUENCING', 3, 'https://gened.kmitl.ac.th/subjectge/90642123/'),
('90642124', 'CS2564', 'เทคโนโลยีและนวัตกรรมทางวิทยาศาสตร์สำหรับ SDGs', 'SCIENCE TECHNOLOGY AND SCIENCE INNOVATION FOR SDGS', 3, 'https://gened.kmitl.ac.th/subjectge/90642124/'),
('90642125', 'CS2564', 'การดำรงชีพท่ามกลางภัยพิบัติและวิกฤติในอนาคต', 'LIVING IN FUTURE DISASTER AND CRISIS', 3, 'https://gened.kmitl.ac.th/subjectge/90642125/'),
('90642126', 'CS2564', 'วิชาเอาตัวรอด', 'SURVIVORS', 3, 'https://gened.kmitl.ac.th/subjectge/90642126/'),
('90642127', 'CS2564', 'รักษ์โลก', 'THINK EARTH', 3, 'https://gened.kmitl.ac.th/subjectge/90642127/'),
('90642128', 'CS2564', 'นิเวศวิทยาและการรักษาสิ่งแวดล้อม', 'ECOLOGY, CONSERVATION AND ENVIRONMENTALISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642128/'),
('90642129', 'CS2564', 'การท่องเที่ยวทางเลือก', 'ALTERNATIVE TOURISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642129/'),
('90642130', 'CS2564', 'การท่องเที่ยวเชิงกีฬา', 'SPORTS TOURISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642130/'),
('90642131', 'CS2564', 'วัฒนธรรมไทยกับการท่องเที่ยว', 'THAI CULTURE AND TOURISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642131/'),
('90642132', 'CS2564', 'ชุมพรศึกษาเพื่อการท่องเที่ยว', 'CHUMPHON STUDY FOR TOURISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642132/'),
('90642133', 'CS2564', 'รอบรั้วชุมพรศึกษา', 'CHUMPHON AREA STUDY', 3, 'https://gened.kmitl.ac.th/subjectge/90642133/'),
('90642134', 'CS2564', 'แผ่นดินพระจอมเกล้าฯ ศึกษา', 'KING MONGKUT''S REIGN STUDY', 3, 'https://gened.kmitl.ac.th/subjectge/90642134/'),
('90642135', 'CS2564', 'ปรัชญาเศรษฐกิจพอเพียง', 'PHILOSOPHY OF SUFFICIENCY ECONOMY', 3, 'https://gened.kmitl.ac.th/subjectge/90642135/'),
('90642136', 'CS2564', 'จริยศาสตร์และสุนทรียศาสตร์', 'ETHICS AND AESTHETICS', 3, 'https://gened.kmitl.ac.th/subjectge/90642136/'),
('90642137', 'CS2564', 'ดูละครแล้วย้อนดูตัว', 'SERIES IN DAILY LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642137/'),
('90642138', 'CS2564', 'สมาธิเพื่อพัฒนาชีวิต', 'MEDITATION FOR LIFE DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642138/'),
('90642140', 'CS2564', 'ภูมิคุ้มกันทางใจ', 'IMMUNITY OF MIND', 3, 'https://gened.kmitl.ac.th/subjectge/90642140/'),
('90642141', 'CS2564', 'จิตวิทยาเพื่อการพัฒนาตนเอง', 'PSYCHOLOGY OF SELF-DEVELOPMENT', 2, 'https://gened.kmitl.ac.th/subjectge/90642141/'),
('90642142', 'CS2564', 'จิตวิทยาสำหรับการสื่อสาร', 'PSYCHOLOGY IN COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642142/'),
('90642143', 'CS2564', 'ชีวิตออกแบบได้', 'DESIGNING YOUR LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642143/'),
('90642144', 'CS2564', 'กระจกส่องใจ', 'MAGIC MIRROR', 3, 'https://gened.kmitl.ac.th/subjectge/90642144/'),
('90642145', 'CS2564', 'พลังแห่งบุคลิกภาพ', 'POWER OF PERSONALITY', 3, 'https://gened.kmitl.ac.th/subjectge/90642145/'),
('90642146', 'CS2564', 'เปลี่ยนความคิด ชีวิตเปลี่ยน', 'POWER OF CHANGE', 3, 'https://gened.kmitl.ac.th/subjectge/90642146/'),
('90642147', 'CS2564', 'ทักษะแห่งความสุข', 'HAPPINESS SKILLS', 3, 'https://gened.kmitl.ac.th/subjectge/90642147/'),
('90642148', 'CS2564', 'ศิลปะการพัฒนาอารมณ์', 'ARTS OF EMOTION DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642148/'),
('90642149', 'CS2564', 'ศิลปะสร้างสรรค์เพื่อพัฒนาอารมณ์และจิตวิญญาณ', 'IMAGINATIVE ART', 3, 'https://gened.kmitl.ac.th/subjectge/90642149/'),
('90642150', 'CS2564', 'ศิลปะในชีวิตประจำวัน', 'ART IN EVERYDAY LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642150/'),
('90642151', 'CS2564', 'มนุษย์กับศิลปะ', 'MAN AND ART', 3, 'https://gened.kmitl.ac.th/subjectge/90642151/'),
('90642152', 'CS2564', 'ปันสุข', 'JOY OF SHARING', 3, 'https://gened.kmitl.ac.th/subjectge/90642152/'),
('90642153', 'CS2564', 'ความเข้าใจในพฤติกรรมมนุษย์', 'UNDERSTANDING HUMAN BEHAVIOR', 3, 'https://gened.kmitl.ac.th/subjectge/90642153/'),
('90642154', 'CS2564', 'ล้มให้เป็น', 'FAIL-ABLE', 3, 'https://gened.kmitl.ac.th/subjectge/90642154/'),
('90642156', 'CS2564', 'ฮวงจุ้ย', 'FENG SHUI', 3, 'https://gened.kmitl.ac.th/subjectge/90642156/'),
('90642157', 'CS2564', 'โหราศาสตร์ไทย', 'THAI ASTROLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642157/'),
('90642158', 'CS2564', 'มุมมองวิทยาศาสตร์และเทคโนโลยีร่วมสมัย', 'CONTEMPORARY SCIENCE AND TECHNOLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642158/'),
('90642159', 'CS2564', 'จิตวิทยาเบื้องต้น', 'INTRODUCTION TO PSYCHOLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90642159/'),
('90642161', 'CS2564', 'ดนตรีอิเล็กทรอนิกส์', 'ELECTRONIC MUSIC HISTORY', 3, 'https://gened.kmitl.ac.th/subjectge/90642161/'),
('90642162', 'CS2564', 'พร้อมสู่วัยทำงาน', 'READY TO WORK', 3, 'https://gened.kmitl.ac.th/subjectge/90642162/'),
('90642163', 'CS2564', 'โดดเด่นด้วยจุดแข็ง', 'STAND OUT WITH STRENGTHS', 3, 'https://gened.kmitl.ac.th/subjectge/90642163/'),
('90642164', 'CS2564', 'กฎหมายทรัพย์สินทางปัญญาสำหรับผู้ประกอบการ', 'INTELLECTUAL PROPERTY LAWS FOR ENTREPRENEUR', 3, 'https://gened.kmitl.ac.th/subjectge/90642164/'),
('90642167', 'CS2564', 'จังหวะชีวิต', 'SLICE OF LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642167/'),
('90642168', 'CS2564', 'เรื่องน่ารู้ของพืชสมุนไพรเพื่อสุขภาพและความงาม', 'INTERESTING TOPICS IN MEDICINAL PLANTS FOR WELLNESS AND AESTHETICS', 3, 'https://gened.kmitl.ac.th/subjectge/90642168/'),
('90642169', 'CS2564', 'กัญชาเพื่อชีวิต', 'CANNABIS FOR LIFE', 3, 'https://gened.kmitl.ac.th/subjectge/90642169/'),
('90642170', 'CS2564', 'ตรรกศาสตร์เบื้องต้น', 'INTRODUCTION TO LOGIC', 3, 'https://gened.kmitl.ac.th/subjectge/90642170/'),
('90642175', 'CS2564', 'เปตอง', 'PETANQUE', 3, 'https://gened.kmitl.ac.th/subjectge/90642175/'),
('90642176', 'CS2564', 'รักบี้ฟุตบอล', 'RUGBY FOOTBALL', 3, 'https://gened.kmitl.ac.th/subjectge/90642176/'),
('90642177', 'CS2564', 'ฟุตบอล', 'SOCCER', 3, 'https://gened.kmitl.ac.th/subjectge/90642177/'),
('90642178', 'CS2564', 'ซอฟบอลและเบสบอล', 'SOFTBALL & BASEBALL', 3, 'https://gened.kmitl.ac.th/subjectge/90642178/'),
('90642179', 'CS2564', 'เทนนิส', 'TENNIS', 3, 'https://gened.kmitl.ac.th/subjectge/90642179/'),
('90642180', 'CS2564', 'วอลเลย์บอล', 'VOLLEYBALL', 3, 'https://gened.kmitl.ac.th/subjectge/90642180/'),
('90642181', 'CS2564', 'กอล์ฟ', 'GOLF', 3, 'https://gened.kmitl.ac.th/subjectge/90642181/'),
('90642182', 'CS2564', 'แบดมินตัน', 'BADMINTON', 3, 'https://gened.kmitl.ac.th/subjectge/90642182/'),
('90642183', 'CS2564', 'บาสเกตบอล', 'BASKETBALL', 3, 'https://gened.kmitl.ac.th/subjectge/90642183/'),
('90642184', 'CS2564', 'หมากกระดาน', 'CHESS', 3, 'https://gened.kmitl.ac.th/subjectge/90642184/'),
('90642185', 'CS2564', 'คาราเต้', 'KARATE', 3, 'https://gened.kmitl.ac.th/subjectge/90642185/'),
('90642186', 'CS2564', 'ยิงปืน', 'SHOOTING', 3, 'https://gened.kmitl.ac.th/subjectge/90642186/'),
('90642187', 'CS2564', 'เทเบิลเทนนิส', 'TABLE TENNIS', 3, 'https://gened.kmitl.ac.th/subjectge/90642187/'),
('90642188', 'CS2564', 'เทควันโด', 'TAEKWONDO', 3, 'https://gened.kmitl.ac.th/subjectge/90642188/'),
('90642189', 'CS2564', 'ยูโด', 'JUDO', 3, 'https://gened.kmitl.ac.th/subjectge/90642189/'),
('90642190', 'CS2564', 'วิธีการออกแบบเพื่อสร้างนวัตกรรม', 'DESIGN METHODS FOR INNOVATION', 3, 'https://gened.kmitl.ac.th/subjectge/90642190/'),
('90642191', 'CS2564', 'การตีความและการใช้เหตุและผล', 'INTERPRETATION AND ARGUMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90642191/'),
('90642192', 'CS2564', 'ฟันดาบสากล', 'FENCING', 3, 'https://gened.kmitl.ac.th/subjectge/90642192/'),
('90642193', 'CS2564', 'ฟุตซอล', 'FUTSAL', 3, 'https://gened.kmitl.ac.th/subjectge/90642193/'),
('90642194', 'CS2564', 'ลีลาศ', 'DANCESPORT', 3, 'https://gened.kmitl.ac.th/subjectge/90642194/'),
('90642195', 'CS2564', 'บริดจ์', 'BRIDGE', 3, 'https://gened.kmitl.ac.th/subjectge/90642195/'),
('90642196', 'CS2564', 'ผู้ฝึกสอนการออกกำลังกายส่วนบุคคล', 'PERSONAL TRAINER', 3, 'https://gened.kmitl.ac.th/subjectge/90642196/'),
('90642197', 'CS2564', 'การดำน้ำเพื่อการท่องเที่ยวเชิงอนุรักษ์', 'DIVING FOR ECOTOURISM', 3, 'https://gened.kmitl.ac.th/subjectge/90642197/'),
('90642201', 'CS2564', 'รู้ลักษณ์', 'Enneagram', 3, 'https://gened.kmitl.ac.th/subjectge/90642201/'),
('90643001', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการจัดการ 1', 'PRACTICE UNDER MANAGEMENT SKILLS 1', 1, 'https://gened.kmitl.ac.th/subjectge/90643001/'),
('90643002', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการจัดการ 2', 'PRACTICE UNDER MANAGEMENT SKILLS 2', 2, 'https://gened.kmitl.ac.th/subjectge/90643002/'),
('90643003', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการจัดการ 3', 'PRACTICE UNDER MANAGEMENT SKILLS 3', 3, 'https://gened.kmitl.ac.th/subjectge/90643003/'),
('90643004', 'CS2564', 'ผู้นำพลังบวก', 'POSITIVE POWER LEADER', 3, 'https://gened.kmitl.ac.th/subjectge/90643004/'),
('90643005', 'CS2564', 'นักเปลี่ยนโลก', 'THE DISRUPTOR', 3, 'https://gened.kmitl.ac.th/subjectge/90643005/'),
('90643006', 'CS2564', 'การจัดการและผู้นำสมัยใหม่', 'MODERN MANAGEMENT AND LEADERSHIP', 3, 'https://gened.kmitl.ac.th/subjectge/90643006/'),
('90643007', 'CS2564', 'ภาวะผู้นำสำหรับคนรุ่นใหม่', 'Next Gen Leadership', 3, 'https://gened.kmitl.ac.th/subjectge/90643007/'),
('90643008', 'CS2564', 'ศาสตร์การต่อรอง', 'SCIENCE OF NEGOTIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90643008/'),
('90643010', 'CS2564', 'การตลาดร่วมสมัย', 'CONTEMPORARY MARKETING', 3, 'https://gened.kmitl.ac.th/subjectge/90643010/'),
('90643012', 'CS2564', 'การทำงานเป็นทีม', 'TEAMWORK', 3, 'https://gened.kmitl.ac.th/subjectge/90643012/'),
('90643013', 'CS2564', 'การจัดการเชิงอุตสาหกรรม', 'INDUSTRIAL MANAGEMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90643013/'),
('90643014', 'CS2564', 'ความรู้ทั่วไปเกี่ยวกับธุรกิจ', 'GENERAL BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643014/'),
('90643015', 'CS2564', 'การบัญชีทางธุรกิจสำหรับคนรุ่นใหม่', 'BUSINESS ACCOUNTING FOR NEW GEN', 3, 'https://gened.kmitl.ac.th/subjectge/90643015/'),
('90643016', 'CS2564', 'สนุกกับธุรกิจออนไลน์', 'FUN WITH ONLINE BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643016/'),
('90643018', 'CS2564', 'ธุรกิจระหว่างประเทศ', 'INTERNATIONAL BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643018/'),
('90643019', 'CS2564', 'เศรษฐศาสตร์กับการเป็นผู้ประกอบการ', 'ECONOMICS AND ENTREPRENEURSHIP', 3, 'https://gened.kmitl.ac.th/subjectge/90643019/'),
('90643020', 'CS2564', 'นักพัฒนาธุรกิจสร้างสรรค์', 'INNOVATIVE ENTREPRENEURS', 3, 'https://gened.kmitl.ac.th/subjectge/90643020/'),
('90643021', 'CS2564', 'ผู้ประกอบการสมัยใหม่', 'MODERN ENTREPRENEURS', 3, 'https://gened.kmitl.ac.th/subjectge/90643021/'),
('90643022', 'CS2564', 'ผู้ประกอบการทางสังคม', 'SOCIAL ENTREPRENEURS', 3, 'https://gened.kmitl.ac.th/subjectge/90643022/'),
('90643023', 'CS2564', 'ผู้ประกอบการเทคโนโลยี', 'TECHNOPRENEURS', 3, 'https://gened.kmitl.ac.th/subjectge/90643023/'),
('90643024', 'CS2564', 'ฟาร์มสุข', 'HAPPINESS FARMS', 3, 'https://gened.kmitl.ac.th/subjectge/90643024/'),
('90643025', 'CS2564', 'เส้นทางสู่ IPO', 'ROAD TO IPO', 3, 'https://gened.kmitl.ac.th/subjectge/90643025/'),
('90643026', 'CS2564', 'การวางแผนเพื่อการลงทุน', 'INVESTMENT PLANNING', 3, 'https://gened.kmitl.ac.th/subjectge/90643026/'),
('90643027', 'CS2564', 'มนุษย์ เงิน และคณิตศาสตร์', 'MAN, MONEY AND MATH', 3, 'https://gened.kmitl.ac.th/subjectge/90643027/'),
('90643028', 'CS2564', 'มือใหม่ (หัด) เล่นหุ้น', 'SMART TIPS FOR BEGINNING INVESTERS', 3, 'https://gened.kmitl.ac.th/subjectge/90643028/'),
('90643029', 'CS2564', 'เศรษฐกิจดิจิทัล', 'DIGITAL ECONOMY', 3, 'https://gened.kmitl.ac.th/subjectge/90643029/'),
('90643030', 'CS2564', 'เศรษฐศาสตร์ทั่วไป และการศึกษาความเป็นไปได้ของโครงการ', 'GENERAL ECONOMICS AND PROJECT FEASIBILITY STUDY', 3, 'https://gened.kmitl.ac.th/subjectge/90643030/'),
('90643031', 'CS2564', 'วิถีชีวิตตามแนวคิดเศรษฐกิจหมุนเวียนในศตวรรษที่ 21', 'CIRCULAR ECONOMIC LIFESTYLE FOR 21st  CENTURY', 3, 'https://gened.kmitl.ac.th/subjectge/90643031/'),
('90643032', 'CS2564', 'ปักหมุดเศรษฐกิจ', 'BCG ECONOMY IN ACTION', 3, 'https://gened.kmitl.ac.th/subjectge/90643032/'),
('90643034', 'CS2564', 'การจัดการกับความคิดสร้างสรรค์', 'MANAGEMENT AND CREATIVITY', 3, 'https://gened.kmitl.ac.th/subjectge/90643034/'),
('90643035', 'CS2564', 'การจัดการความรู้เพื่อการพัฒนานวัตกรรม', 'KNOWLEDGE MANAGEMENT FOR INNOVATION DEVELOPMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90643035/'),
('90643036', 'CS2564', 'การจัดการความรู้เพื่อการบริหารโครงการ', 'KNOWLEDGE MANAGEMENT FOR PROJECT MANAGEMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90643036/'),
('90643037', 'CS2564', 'การบริหารงานภาครัฐและนโยบายสาธารณะในศตวรรษที่  21', 'PUBLIC ADMINISTRATION AND PUBLIC POLICY IN THE 21st CENTURY', 3, 'https://gened.kmitl.ac.th/subjectge/90643037/'),
('90643038', 'CS2564', 'ศัลยกรรมชีวิต', 'REBRANDING', 3, 'https://gened.kmitl.ac.th/subjectge/90643038/'),
('90643039', 'CS2564', 'นวัตกรรม สจล.', 'KMITL INNOVATION', 3, 'https://gened.kmitl.ac.th/subjectge/90643039/'),
('90643040', 'CS2564', 'ผู้นำในฐานะโค้ช', 'LEADERSHIP AS A COACH', 3, 'https://gened.kmitl.ac.th/subjectge/90643040/'),
('90643041', 'CS2564', 'ธรรมาภิบาลสากล', 'GLOBAL GOVERNANCE', 3, 'https://gened.kmitl.ac.th/subjectge/90643041/'),
('90643042', 'CS2564', 'ฮาร์ดเพาเวอร์และซอฟท์เพาเวอร์', 'HARD POWER AND SOFT POWER', 3, 'https://gened.kmitl.ac.th/subjectge/90643042/'),
('90643043', 'CS2564', 'ธุรกิจดนตรี', 'MUSIC BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643043/'),
('90643044', 'CS2564', 'ลีนสตาร์ทอัพและแนวคิดธุรกิจแบบคล่องตัว', 'LEAN STARTUP AND AGILE BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90643044/'),
('90643045', 'CS2564', 'การจัดการนวัตกรรม', 'INNOVATION MANAGEMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90643045/'),
('90644001', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการสื่อสาร 1', 'PRACTICE UNDER LANGUAGE AND COMMUNICATION SKILLS 1', 1, 'https://gened.kmitl.ac.th/subjectge/90644001/'),
('90644002', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการสื่อสาร 2', 'PRACTICE UNDER LANGUAGE AND COMMUNICATION SKILLS 2', 2, 'https://gened.kmitl.ac.th/subjectge/90644002/'),
('90644003', 'CS2564', 'ปฏิบัติงานตามทักษะด้านการสื่อสาร 3', 'PRACTICE UNDER LANGUAGE AND COMMUNICATION SKILLS 3', 3, 'https://gened.kmitl.ac.th/subjectge/90644003/'),
('90644007', 'CS2564', 'ภาษาอังกฤษพื้นฐาน 1', 'FOUNDATION ENGLISH 1', 3, 'https://gened.kmitl.ac.th/subjectge/90644007/'),
('90644008', 'CS2564', 'ภาษาอังกฤษพื้นฐาน 2', 'FOUNDATION ENGLISH 2', 3, 'https://gened.kmitl.ac.th/subjectge/90644008/'),
('90644009', 'CS2564', 'การออกเสียงภาษาอังกฤษเบื้องต้น', 'BASIC ENGLISH PRONUNCIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644009/'),
('90644010', 'CS2564', 'การพัฒนาทักษะการอ่านและการเขียนภาษาอังกฤษ', 'DEVELOPMENT OF READING AND WRITING SKILLS IN ENGLISH', 3, 'https://gened.kmitl.ac.th/subjectge/90644010/'),
('90644011', 'CS2564', 'ภาษาอังกฤษเชิงวิชาการ', 'ENGLISH FOR ACADEMIC PURPOSES', 3, 'https://gened.kmitl.ac.th/subjectge/90644011/'),
('90644012', 'CS2564', 'ภาษาอังกฤษเพื่อการสื่อสาร', 'ENGLISH FOR COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644012/'),
('90644013', 'CS2564', 'การเขียนภาษาอังกฤษเพื่อการสื่อสาร', 'ENGLISH FOR COMMUNICATIVE WRITING', 3, 'https://gened.kmitl.ac.th/subjectge/90644013/'),
('90644014', 'CS2564', 'ภาษาอังกฤษเพื่อการสื่อสารทางวิชาชีพ', 'ENGLISH FOR PROFESSIONAL COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644014/'),
('90644015', 'CS2564', 'ภาษาอังกฤษเพื่อการศึกษาต่อ', 'ENGLISH FOR FURTHER STUDIES', 3, 'https://gened.kmitl.ac.th/subjectge/90644015/'),
('90644016', 'CS2564', 'อังกฤษเพื่ออุตสาหกรรม', 'ENGLISH FOR INDUSTRY', 3, 'https://gened.kmitl.ac.th/subjectge/90644016/'),
('90644017', 'CS2564', 'ภาษาอังกฤษสำหรับธุรกิจ', 'ENGLISH FOR BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90644017/'),
('90644018', 'CS2564', 'ภาษาอังกฤษเพื่อการตลาด', 'ENGLISH FOR MARKETING', 3, 'https://gened.kmitl.ac.th/subjectge/90644018/'),
('90644019', 'CS2564', 'ภาษาอังกฤษเพื่อการจัดการ', 'ENGLISH FOR MANAGEMENT', 3, 'https://gened.kmitl.ac.th/subjectge/90644019/'),
('90644020', 'CS2564', 'ภาษาอังกฤษเพื่อความเข้าใจข่าวสาร', 'ENGLISH FOR MEDIA', 3, 'https://gened.kmitl.ac.th/subjectge/90644020/'),
('90644022', 'CS2564', 'ภาษาอังกฤษสำหรับมืออาชีพ', 'ENGLISH FOR PROFESSIONAL PURPOSES', 3, 'https://gened.kmitl.ac.th/subjectge/90644022/'),
('90644023', 'CS2564', 'ภาษาอังกฤษเพื่อเตรียมตัวทำงาน', 'ENGLISH FOR WORK PREPARATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644023/'),
('90644024', 'CS2564', 'ภาษาอังกฤษเพื่อการท่องเที่ยวและการเดินทาง', 'ENGLISH FOR TOURISM AND TRAVELLING', 3, 'https://gened.kmitl.ac.th/subjectge/90644024/'),
('90644025', 'CS2564', 'ภาษาอังกฤษเพื่อการสื่อสารในงานสถาปัตยกรรม', 'ENGLISH FOR ARCHITECTURAL ARTS & DESIGN COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644025/'),
('90644026', 'CS2564', 'ภาษาอังกฤษเพื่อการนำเสนอในงานสถาปัตยกรรม', 'ENGLISH FOR ARCHITECTURAL ARTS & DESIGN PRESENTATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644026/'),
('90644027', 'CS2564', 'ภาษาอังกฤษสำหรับการเขียนพรรณา', 'ENGLISH FOR NARRATIVE WRITING', 3, 'https://gened.kmitl.ac.th/subjectge/90644027/'),
('90644028', 'CS2564', 'ภาษาอังกฤษเพื่อการออกแบบ', 'ENGLISH FOR DESIGN', 3, 'https://gened.kmitl.ac.th/subjectge/90644028/'),
('90644029', 'CS2564', 'ภาษาอังกฤษสำหรับวิชาชีพสุขภาพ', 'ENGLISH FOR HEALTH PROFESSIONS', 3, 'https://gened.kmitl.ac.th/subjectge/90644029/'),
('90644030', 'CS2564', 'ภาษาอังกฤษเพื่อการประชาสัมพันธ์', 'ENGLISH FOR PUBLIC RELATIONS', 3, 'https://gened.kmitl.ac.th/subjectge/90644030/'),
('90644031', 'CS2564', 'ภาษาอังกฤษสำหรับวิทยาศาสตร์และเทคโนโลยี', 'ENGLISH FOR SCIENCE AND TECHNOLOGY', 3, 'https://gened.kmitl.ac.th/subjectge/90644031/'),
('90644032', 'CS2564', 'ภาษาอังกฤษสำหรับการบิน', 'ENGLISH FOR AVIATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644032/'),
('90644033', 'CS2564', 'การเขียนและการพูดในงานอาชีพ', 'WRITING AND SPEAKING IN THE PROFESSIONS', 3, 'https://gened.kmitl.ac.th/subjectge/90644033/'),
('90644034', 'CS2564', 'การเขียนทางเทคนิค', 'TECHNICAL WRITING', 3, 'https://gened.kmitl.ac.th/subjectge/90644034/'),
('90644035', 'CS2564', 'การอ่านและเขียนเชิงวิชาการสำหรับวิทยาศาสตร์สุขภาพ', 'ACADEMIC READING AND WRITING FOR HEALTH SCIENCES', 3, 'https://gened.kmitl.ac.th/subjectge/90644035/'),
('90644036', 'CS2564', 'การพัฒนาทักษะทางภาษาอังกฤษเพื่อการเรียนรู้ตลอดชีวิต', 'ENGLISH SKILL DEVELOPMENT FOR LIFE-LONG LEARNING', 3, 'https://gened.kmitl.ac.th/subjectge/90644036/'),
('90644037', 'CS2564', 'การสื่อสารข้ามวัฒนธรรม', 'CROSS CULTURAL COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644037/'),
('90644039', 'CS2564', 'ทักษะการสื่อสารผ่านการอภิปราย', 'COMMUNICATION SKILLS THROUGH DEBATE', 3, 'https://gened.kmitl.ac.th/subjectge/90644039/'),
('90644040', 'CS2564', 'ทักษะการสื่อสารผ่านละคร', 'COMMUNICATION SKILLS THROUGH DRAMA', 3, 'https://gened.kmitl.ac.th/subjectge/90644040/'),
('90644041', 'CS2564', 'ภาษาอังกฤษจากสื่อบันเทิง', 'ENGLISH FROM ENTERTAINMENT MEDIA', 3, 'https://gened.kmitl.ac.th/subjectge/90644041/'),
('90644042', 'CS2564', 'การสื่อสารและการนำเสนออย่างมืออาชีพ', 'PROFESSIONAL COMMUNICATION AND PRESENTATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644042/'),
('90644043', 'CS2564', 'การพูดในที่สาธารณะ', 'PUBLIC SPEAKING', 3, 'https://gened.kmitl.ac.th/subjectge/90644043/'),
('90644044', 'CS2564', 'พูดได้ พูดดี พูดเป็น', 'BEST SPEECH', 3, 'https://gened.kmitl.ac.th/subjectge/90644044/'),
('90644045', 'CS2564', 'การค้นคว้าและการเขียนรายงาน', 'RESEARCH PAPER WRITING', 3, 'https://gened.kmitl.ac.th/subjectge/90644045/'),
('90644046', 'CS2564', 'การฟังและการอ่านเพื่อพัฒนาคุณภาพชีวิต', 'LISTENING AND READING FOR IMPROVING LIFE QUALITY', 3, 'https://gened.kmitl.ac.th/subjectge/90644046/'),
('90644047', 'CS2564', 'การพัฒนาทักษะการเขียนภาษาไทยเชิงสร้างสรรค์', 'DEVELOPMENT OF THAI CREATIVE WRITING SKILLS', 3, 'https://gened.kmitl.ac.th/subjectge/90644047/'),
('90644048', 'CS2564', 'ภาษาในสังคมไทย', 'LANGUAGE IN THAI SOCIETY', 3, 'https://gened.kmitl.ac.th/subjectge/90644048/'),
('90644049', 'CS2564', 'ภาษาไทยเพื่อการสร้างสรรค์', 'THAI LANGUAGE FOR CREATIVITY', 3, 'https://gened.kmitl.ac.th/subjectge/90644049/'),
('90644050', 'CS2564', 'การเขียนภาษาไทยในที่ทำงาน', 'THAI WRITING IN WORKPLACE', 3, 'https://gened.kmitl.ac.th/subjectge/90644050/'),
('90644051', 'CS2564', 'ภาษาไทยสำหรับทันตแพทย์', 'THAI FOR DENTAL PROFESSIONS', 3, 'https://gened.kmitl.ac.th/subjectge/90644051/'),
('90644052', 'CS2564', 'ศิลปะการสื่อสารสำหรับมืออาชีพด้านอาหาร', 'COMMUNICATION IN THAI FOR CULINARY PROFESSIONALS', 3, 'https://gened.kmitl.ac.th/subjectge/90644052/'),
('90644053', 'CS2564', 'การฟังและการพูดภาษาจีนพื้นฐาน', 'FUNDAMENTAL CHINESE FOR LISTENING AND SPEAKING', 3, 'https://gened.kmitl.ac.th/subjectge/90644053/'),
('90644054', 'CS2564', 'การอ่านและเขียนภาษาจีนพื้นฐาน', 'FUNDAMENTAL CHINESE READING AND WRITING', 3, 'https://gened.kmitl.ac.th/subjectge/90644054/'),
('90644055', 'CS2564', 'ไวยากรณ์ภาษาจีนพื้นฐาน และสำนวนและสุภาษิตภาษาจีน', 'BASIC CHINESE GRAMMAR AND CHINESE IDIOMS AND PROVERBS', 3, 'https://gened.kmitl.ac.th/subjectge/90644055/'),
('90644056', 'CS2564', 'วัฒนธรรม สำนวนและสุภาษิตจีน', 'CHINESE CULTURE IDIOMS AND PROVERBS', 3, 'https://gened.kmitl.ac.th/subjectge/90644056/'),
('90644057', 'CS2564', 'ภาษาจีนเพื่อการสื่อสาร', 'CHINESE FOR COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644057/'),
('90644058', 'CS2564', 'ภาษาจีนฉบับแฟนด้อม', 'CHINESE FANDOM', 3, 'https://gened.kmitl.ac.th/subjectge/90644058/'),
('90644059', 'CS2564', 'ภาษาจีนเพื่อการท่องเที่ยว', 'CHINESE FOR TRAVEL', 3, 'https://gened.kmitl.ac.th/subjectge/90644059/'),
('90644060', 'CS2564', 'ภาษาเยอรมันเพื่อการสื่อสาร', 'GERMAN FOR COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644060/'),
('90644061', 'CS2564', 'ภาษาเยอรมันเพื่อการทำงานและธุรกิจ', 'GERMAN FOR WORK AND BUSINESS', 3, 'https://gened.kmitl.ac.th/subjectge/90644061/'),
('90644062', 'CS2564', 'ภาษาญี่ปุ่นเพื่อการสื่อสาร', 'JAPANESE FOR COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644062/'),
('90644063', 'CS2564', 'ภาษาญี่ปุ่นเพื่อการท่องเที่ยว', 'JAPANESE FOR TRAVEL', 3, 'https://gened.kmitl.ac.th/subjectge/90644063/'),
('90644064', 'CS2564', 'ภาษาเกาหลีเพื่อการท่องเที่ยว', 'KOREAN FOR TRAVEL', 3, 'https://gened.kmitl.ac.th/subjectge/90644064/'),
('90644065', 'CS2564', 'ภาษาเวียดนามเพื่อการท่องเที่ยว', 'VIETNAMESE FOR TRAVEL', 3, 'https://gened.kmitl.ac.th/subjectge/90644065/'),
('90644066', 'CS2564', 'ภาษามาเลย์เพื่อการท่องเที่ยว', 'MALAY FOR TRAVEL', 3, 'https://gened.kmitl.ac.th/subjectge/90644066/'),
('90644067', 'CS2564', 'สนทนาภาษาจีนเพื่อไอที', 'CHINESE CONVERSATION FOR IT', 3, 'https://gened.kmitl.ac.th/subjectge/90644067/'),
('90644068', 'CS2564', 'รู้จีนให้ได้เงิน', 'HOW TO MAKE MONEY WITH CHINESE', 3, 'https://gened.kmitl.ac.th/subjectge/90644068/'),
('90644069', 'CS2564', 'ภาษาญี่ปุ่นพื้นฐาน', 'FOUNDATION JAPANESE', 3, 'https://gened.kmitl.ac.th/subjectge/90644069/'),
('90644070', 'CS2564', 'การสื่อสารนวัตกรรม', 'INNOVATIVE COMMUNICATION', 3, 'https://gened.kmitl.ac.th/subjectge/90644070/'),
('90645016', 'CS2564', 'การตลาดยุคคอนเทนท์', 'CONTENT MARKETING', 1, 'https://gened.kmitl.ac.th/subjectge/90645016/');
