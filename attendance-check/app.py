from flask import Flask, render_template, request
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# 🔹 Google Sheets API 설정
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# 🔹 스프레드시트 열기
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1oW4CIxFG_dFEdL5BnT7l7ADoulCCYfstkbTq6KsbLUM/edit?gid=942542949#gid=942542949"
spreadsheet = client.open_by_url(spreadsheet_url)

# 🔹 출석 기록 시트
attendance_sheet = spreadsheet.worksheet("attendance")  # 출석 기록이 저장되는 시트

# 🔹 요일별 출석 시간 기록 열 (D~K) (A열=목록, B열=학번, D~K열=출석 기록)
attendance_columns = {
    0: {"1교시": "D", "2교시": "E"},  # 월요일
    1: {"1교시": "F", "2교시": "G"},  # 화요일
    2: {"1교시": "H", "2교시": "I"},  # 수요일
    3: {"1교시": "J", "2교시": "K"},  # 목요일
}

@app.route('/')
def index():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('index.html', current_time=current_time)

@app.route('/submit', methods=['POST'])
def submit():
    student_id = request.form.get('student_id')

    if not student_id or len(student_id) != 4:
        return "올바른 학번(4자리)을 입력하세요!", 400

    # 🔹 현재 시간과 요일 확인
    now = datetime.now()
    weekday = now.weekday()  # 월요일=0, 화요일=1, 수요일=2, 목요일=3
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 🔹 출석 가능한 요일인지 확인 (월~목)
    if weekday not in attendance_columns:
        return "출석 체크는 월요일~목요일만 가능합니다.", 400

    # 🔹 현재 시간이 어느 교시인지 확인
    current_hour = now.hour
    current_minute = now.minute

    if (current_hour == 18 and current_minute >= 30) or (current_hour == 19 and current_minute <= 50):
        period = "1교시"  # 18:30~19:50
    elif (current_hour == 20) or (current_hour == 21 and current_minute == 0):
        period = "2교시"  # 20:00~21:00
    else:
        return "출석 가능한 시간이 아닙니다!", 400

    # 🔹 기록할 열 선택 (요일 & 교시 기반)
    column_letter = attendance_columns[weekday].get(period, None)
    
    # 🔍 디버깅 출력 (어떤 열에 기록할 것인지 확인)
    print(f"✅ 선택된 열: {column_letter} / 요일: {weekday} / 교시: {period}")

    if not column_letter:
        return "출석 기록을 저장할 올바른 열을 찾을 수 없습니다!", 400

    # 🔹 학생의 기존 출석 여부 확인 (학번은 B열, 3행부터 시작)
    students_data = attendance_sheet.get_all_values()
    student_row = None

    for i in range(2, len(students_data)):  # 3행부터 검색 (0-based index에서 2부터 시작)
        row = students_data[i]
        if len(row) > 1 and row[1] and str(row[1]).strip() == str(student_id).strip():  # B열이 비어있는지 확인 후 비교
            student_row = i + 1  # 실제 Google Sheets의 행 번호
            break

    # 🔍 디버깅 출력 (학번이 몇 번째 줄에 있는지 확인)
    print(f"✅ 찾은 학번: {student_id} / 행 번호: {student_row}")

    if student_row is None:
        return "해당 학번이 등록되지 않았습니다!", 400

    # 🔹 출석 시간 기록
    try:
        attendance_sheet.update_acell(f"{column_letter}{student_row}", current_time)
        return f"출석 완료! 학번: {student_id}, 요일: {now.strftime('%A')}, 교시: {period}, 시간: {current_time}", 200
    except Exception as e:
        return f"출석 데이터 업데이트 실패! 오류: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
