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
    credit_str VARCHAR(20) NOT NULL,
    credit INTEGER NOT NULL DEFAULT 0,
    year INTEGER NOT NULL,
    semester INTEGER NOT NULL,
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
('05506004', '05506003'),
('90644008', '90644007'),
('05506006', '05506004'),
('05506007', '05506008'),
('05506002', '05506233'),
('05506236', '05506006'),
('05506113', '05506004'),
('05506014', '05506250'),
('05506210', '05506006'),
('05506017', '05506113'),
('05506016', '05506008'),
('05506237', '05506004'),
('05506098', '05506017'),
('05506099', '05506098');
