# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import threading
import os
import socket
import csv
import psycopg2
import time
from datetime import datetime, timedelta
from psycopg2 import OperationalError, DatabaseError, InterfaceError
from zk import ZK

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title('Get Attendance')
        self.center_window(625, 625)

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_columnconfigure(3, weight=1)
        self.root.grid_columnconfigure(4, weight=1)
        self.root.grid_columnconfigure(5, weight=1)
        self.root.grid_columnconfigure(6, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(3, weight=0)

        self.setup_widgets()
        self.update_status_bar()

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_widgets(self):
        tk.Label(self.root, text='Start Date:').grid(row=0, column=0, padx=10, pady=10, sticky='ew')
        self.start_calendar = DateEntry(self.root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/MM/yyyy')
        self.start_calendar.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

        tk.Label(self.root, text='End Date:').grid(row=0, column=2, padx=10, pady=10, sticky='ew')
        self.end_calendar = DateEntry(self.root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/MM/yyyy')
        self.end_calendar.grid(row=0, column=3, padx=10, pady=10, sticky='ew')

        self.start_btn = tk.Button(self.root, text='Start', command=self.start_generate, relief='raised', activebackground='lightblue', activeforeground='black')
        self.start_btn.grid(row=0, column=4, padx=10, pady=10, sticky='ew')

        self.close_btn = tk.Button(self.root, text='Close', command=self.close)
        self.close_btn.grid(row=0, column=5, padx=10, pady=10, sticky='ew')

        self.save_btn = tk.Button(self.root, text='Save Log', command=self.save_log_to_file)
        self.save_btn.grid(row=0, column=6, padx=10, pady=10, sticky='ew')

        # Log text setup
        log_frame = tk.Frame(self.root)
        log_frame.grid(row=1, column=0, columnspan=7, padx=10, pady=0, sticky='nsew')
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, font=('Consolas', 8), state='disabled', wrap='word')
        self.log_text.grid(row=0, column=0, sticky='nsew')

        # Style setup
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Scrollbar setup
        self.style.configure('Thin.Vertical.TScrollbar', gripcount=0, background='gray', troughcolor='white', width=8)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview, style='Thin.Vertical.TScrollbar')
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Progressframe setup
        progress_frame = tk.Frame(self.root)
        progress_frame.grid(row=2, column=0, columnspan=7, sticky='ew')
        progress_frame.grid_columnconfigure(0, weight=1)

        # Progressbar setup
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', length=100, mode='determinate', maximum=100, style='black.Horizontal.TProgressbar')
        self.progress_bar.grid(row=2, column=0, columnspan=6, padx=10, pady=10, sticky='ew')
        self.progress_label = tk.Label(progress_frame, text='000%', font=('Consolas', 8, 'bold'))
        self.progress_label.grid(row=2, column=7, padx=(0, 10), pady=10, sticky='w')

        self.status_label = tk.Label(self.root, text='', bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=3, column=0, columnspan=7, sticky='ew')

    def update_progress_label(self, value):
        self.progress_label.config(text=f'{value}%')

    def update_status_bar(self):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        current_date = datetime.now().strftime('%d/%m/%Y')
        current_time = datetime.now().strftime('%H:%M:%S')
        self.status_label.config(text=f'[{width} x {height}] - [{current_date}] - [{current_time}]')
        self.root.after(1000, self.update_status_bar)

    def log(self, message, color='black', style='normal', size=8, blink=False):
        self.log_text.config(state='normal')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.insert(tk.END, f'{current_time} - {message}\n')
        tag_name = f"tag_{self.log_text.index('end')}"
        self.log_text.tag_add(tag_name, f'{self.log_text.index("end-2l")} linestart', f'{self.log_text.index("end-1l")} lineend')
        font_config = ('Consolas', size, style)
        self.log_text.tag_config(tag_name, foreground=color, font=font_config)

        if blink and color == 'black':
            self.blink_black_text(tag_name)

        if blink and color == 'green':
            self.blink_green_text(tag_name)

        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def blink_black_text(self, tag_name, current_color='black'):
        next_color = 'red' if current_color == 'black' else 'black'
        self.log_text.tag_config(tag_name, foreground=next_color)
        self.root.after(500, self.blink_black_text, tag_name, next_color)

    def blink_green_text(self, tag_name, current_color='green'):
        next_color = 'green' if current_color == 'blue' else 'blue'
        self.log_text.tag_config(tag_name, foreground=next_color)
        self.root.after(500, self.blink_green_text, tag_name, next_color)

    def save_log_to_file(self):
        # Save the log content
        log_content = self.log_text.get('1.0', tk.END)

        with open('attlog.txt', 'w') as file:
            file.write(log_content)

        # Attempt to delete 'raw.csv'
        try:
            os.remove('raw.csv')
            self.log('"raw.csv" deleted successfully ...')
        except FileNotFoundError:
            self.log('"raw.csv" not found, unable to delete ...')

        # Attempt to delete 'final.csv'
        try:
            os.remove('final.csv')
            self.log('"final.csv" deleted successfully ...')
        except FileNotFoundError:
            self.log('"final.csv" not found, unable to delete ...')

        self.log('Logs saved to "attlog.txt" ...')

    # The everything
    def threaded_generate(self):
        start_time = time.time()
        self.start_btn.focus_set()

        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')

        rec = None
        start_date = self.start_calendar.get_date()
        end_date = self.end_calendar.get_date()

        self.log(f'Start button clicked. Start Date: {start_date.strftime("%d/%m/%Y")}, End Date: {end_date.strftime("%d/%m/%Y")}')
        
        if end_date < start_date:
            messagebox.showerror('Error', 'End Date cannot be earlier than Start Date!')
            return

        def init_progressbar(value):
            self.progress_bar['length'] = value
            self.progress_bar['maximum'] = value
            self.progress_bar['value'] = 0

        def update_progressbar(value):
            if self.progress_bar['value'] <= 25:
                self.style.configure('red.Horizontal.TProgressbar', foreground='red', background='red')
                self.progress_bar['style'] = 'red.Horizontal.TProgressbar'
            elif self.progress_bar['value'] > 25 and self.progress_bar['value'] < 50:
                self.style.configure('green.Horizontal.TProgressbar', foreground='green', background='green')
                self.progress_bar['style'] = 'green.Horizontal.TProgressbar'
            elif self.progress_bar['value'] > 50 and self.progress_bar['value'] < 75:
                self.style.configure('blue.Horizontal.TProgressbar', foreground='blue', background='blue')
                self.progress_bar['style'] = 'blue.Horizontal.TProgressbar'
            else:
                self.style.configure('black.Horizontal.TProgressbar', foreground='black', background='black')
                self.progress_bar['style'] = 'black.Horizontal.TProgressbar'
            
            self.progress_bar['value'] = value
            self.update_progress_label(str(round(value)).zfill(3))

            root.update_idletasks()
            root.after(10)

        def parse_datetime(dt_str):
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') if dt_str else None

        def format_datetime(dt):
            return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''

        def ping_host(host: str, port: int, timeout=5):
            '''ping server'''

            try:
                socket.setdefaulttimeout(timeout)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((host, port))
            except OSError as error:
                return False
            else:
                s.close()
                return True

        def count_machine_records(start_date, end_date):
            nonlocal rec
            dip = '192.168.0.117'
            port = 4370
            zk = ZK(dip, port, timeout=5)
            conn = None
            sdate = start_date
            edate = end_date
            delta = edate - sdate

            try:
                self.log('STEP-2: Counting date-wise records ...', 'blue', 'bold')
                self.log('')
                conn = zk.connect()
                conn.disable_device()
                attendances = conn.get_attendance()
                cnt = tmp = 0
                
                for i in range(delta.days + 1):
                    datex = sdate + timedelta(days=i)

                    for att in attendances:
                        x = att.timestamp

                        if (x.strftime('%Y-%m-%d') == datex.strftime('%Y-%m-%d')):
                            cnt += 1

                    self.log(f'{datex} has {cnt} record(s)')
                    tmp += cnt
                    cnt = 0
                
                conn.enable_device()
                self.log('')
                self.log(f'Total Record(s): {tmp}')
                self.log('')
                rec = tmp
                time.sleep(1)

            except Exception as e:
                self.log('Process terminate : {}'.format(e))

            finally:
                if conn:
                    conn.disconnect()

        def get_data(start_date, end_date):
            dip = '192.168.0.117'
            port = 4370
            zk = ZK(dip, port, timeout=5)

            conn = None
            pgcon = None

            sdate = start_date
            edate = end_date

            delta = edate - sdate
            
            try:
                self.log('STEP-3: Fetching/Pulling records from machine ...', 'blue', 'bold')
                self.log('')
                conn = zk.connect()
                conn.disable_device()

                pgcon = psycopg2.connect(
                    database = 'fgtest',
                    user = 'fgatt',
                    password = 'fgatt1947',
                    host = '109.199.127.25',
                    port = '5432'
                )

                attendances = conn.get_attendance()

                cursor = pgcon.cursor()

                cursor.execute('DELETE FROM a_tmp;')

                init_progressbar(rec)

                for i in range(delta.days + 1):
                    datex = sdate + timedelta(days=i)
                    self.log(f'Working on: {datex}')
                    self.log('')

                    if attendances:
                        cnt = 0

                        for att in attendances:
                            x = att.timestamp

                            if (x.strftime('%Y-%m-%d') == datex.strftime('%Y-%m-%d')):
                                self.log('User      : {}'.format(att.user_id))
                                self.log('Timestamp : {}'.format(att.timestamp))
                                cnt += 1

                                try:
                                    res = None

                                    cursor.execute('''
                                        SELECT 
                                            id,
                                            emp_id,
                                            check_in_out,
                                            is_done
                                        FROM
                                            a_tmp
                                        WHERE
                                            check_in_out = %s;
                                    ''', (
                                        att.timestamp,
                                    ))

                                    res = cursor.fetchone()

                                    if res:
                                        log(f'Record already exists:, {res[1]}, {res[2]}')
                                    else:
                                        log('Action    : Inserting record')

                                        cursor.execute('''
                                            INSERT INTO a_tmp (
                                                emp_id, 
                                                check_in_out
                                            ) 
                                            VALUES (
                                                %s, 
                                                %s
                                            )''', ( 
                                                att.user_id, 
                                                att.timestamp
                                            )
                                        )

                                    self.log('')
                                    rec += (100 / rec)
                                    update_progressbar(rec)

                                except (Exception, psycopg2.DatabaseError) as error:
                                    self.log(error)

                        self.log(f'Record(s): {cnt}')    
                        self.log('')

                if pgcon:
                    pgcon.commit()
                    cursor.close()
                    pgcon.close()

                conn.enable_device()
                time.sleep(1)

            except Exception as e:
                log('Process terminate : {}'.format(e))

            finally:
                if conn:
                    conn.disconnect()

        def fetch_records(start_date, end_date):
            try:
                conn = psycopg2.connect(
                    database='fgtest',
                    user='fgatt',
                    password='fgatt1947',
                    host='109.199.127.25',
                    port='5432'
                )

                cur = conn.cursor()

                try:
                    cur.execute('''
                        SELECT
                            x.emp_id,
                            x.check_in_out,
                            x.start_time,
                            x.end_time,
                            CASE
                                WHEN
                                    start_time > end_time
                                THEN
                                    'Night'
                                ELSE
                                    'Day'
                            END AS shift_type
                        FROM 
                        (
                            SELECT 
                                a.emp_id, 
                                a.check_in_out,
                                SUBSTRING(split_part(r.name, '-', 1) FROM 1 FOR 2) || ':' || 
                                SUBSTRING(split_part(r.name, '-', 1) FROM 3 FOR 2) AS start_time,
                                SUBSTRING(split_part(r.name, '-', 2) FROM 1 FOR 2) || ':' || 
                                SUBSTRING(split_part(r.name, '-', 2) FROM 3 FOR 2) AS end_time
                            FROM 
                                a_tmp AS a
                            INNER JOIN
                                hr_employee AS e
                            ON
                                a.emp_id = e.id
                            INNER JOIN
                                resource_calendar AS r
                            ON
                                e.resource_calendar_id = r.id
                            WHERE
                                DATE(a.check_in_out) 
                            BETWEEN 
                                %s
                            AND 
                                %s
                            ORDER BY 
                                a.emp_id,
                                a.check_in_out
                        ) AS x
                        ORDER BY 
                            x.emp_id,
                            x.check_in_out;
                    ''', (start_date, end_date,))
                    
                    rows = cur.fetchall()
                    
                    cnt = tmp = 0
                    result = []
                    tmp = len(rows)
                    init_progressbar(tmp)

                    for r in rows:
                        start_time = datetime.strptime(r[2], '%H:%M').time()
                        end_time = datetime.strptime(r[3], '%H:%M').time()

                        x = abs((r[1].hour * 60 + r[1].minute) - (start_time.hour * 60 + start_time.minute))
                        y = abs((r[1].hour * 60 + r[1].minute) - (end_time.hour * 60 + end_time.minute))

                        if x < y:
                            z = 'CheckIn'
                        elif y < x:
                            z = 'CheckOut'

                        result.append((r[0], r[1].strftime('%Y-%m-%d %H:%M:%S'), z, r[4]))
                        cnt += 1

                    raw_data = result

                    raw_data_as_lists = [list(item) for item in raw_data]

                    with open('raw.csv', 'w', newline='') as csvfile:
                        fields = ['emp_id', 'check_time', 'check_type', 'shift_type']
                        writer = csv.writer(csvfile)
                        writer.writerow(fields)
                        writer.writerows(raw_data_as_lists)

                    with open('raw.csv', 'r') as infile:
                        reader = csv.DictReader(infile, delimiter=',')
                        raw_data = list(reader)

                    transformed_data = []
                    current_emp_id = None
                    check_in_time = None
                    current_shift = None
                    max_shift_duration = timedelta(hours=24)

                    time.sleep(1)
                    self.log('STEP-4: Getting raw data from table for processing furthur ...', 'blue', 'bold')
                    self.log('')
                    self.log('Identifying CheckIn/CheckOut based on shift timing:')
                    self.log('')

                    headerx = f'{"EmpID".ljust(10)}{"CheckTime".ljust(25)}{"CheckType".ljust(15)}{"ShiftType".ljust(15)}'
                    self.log(59 * '-')
                    self.log(headerx)
                    self.log(59 * '-')
                    pb = 0

                    for row in raw_data:
                        emp_id = row['emp_id']
                        check_time = row['check_time']
                        check_type = row['check_type']
                        shift_type = row['shift_type']
                        check_time_dt = parse_datetime(check_time)

                        self.log(f'{emp_id.ljust(10)}{check_time.ljust(25)}{check_type.ljust(15)}{shift_type.ljust(15)}')
                        pb += (100 / tmp)
                        update_progressbar(pb)

                        if emp_id != current_emp_id:
                            transformed_data.append([current_emp_id, format_datetime(check_in_time), '', current_shift])

                            current_emp_id = emp_id
                            current_shift = shift_type
                            check_in_time = None
                        
                        if check_type == 'CheckIn':
                            if check_in_time is None:
                                check_in_time = check_time_dt
                            else:
                                transformed_data.append([emp_id, format_datetime(check_in_time), '', shift_type])
                                check_in_time = check_time_dt

                        elif check_type == 'CheckOut':
                            if check_in_time is not None:
                                if check_time_dt - check_in_time <= max_shift_duration:
                                    transformed_data.append([emp_id, format_datetime(check_in_time), format_datetime(check_time_dt), shift_type])
                                    check_in_time = None
                                else:
                                    transformed_data.append([emp_id, format_datetime(check_in_time), '', shift_type])
                                    check_in_time = None
                                    transformed_data.append([emp_id, '', format_datetime(check_time_dt), shift_type])
                            else:
                                transformed_data.append([emp_id, '', format_datetime(check_time_dt), shift_type])

                    if check_in_time is not None:
                        transformed_data.append([current_emp_id, format_datetime(check_in_time), '', shift_type])

                    self.log('')
                    self.log(f'Record(s): {cnt}')
                    self.log('')
                    time.sleep(1)
                    self.log('STEP-5: Raw data transformation is being processed ...', 'blue', 'bold')
                    self.log('')
                    self.log('Placing CheckIn/CheckOut based on shift timing:')
                    self.log('')
                    time.sleep(1)
                    headery = f'{"EmpID".ljust(10)}{"CheckIn".ljust(25)}{"CheckOut".ljust(25)}{"ShiftType".ljust(15)}'
                    self.log(69 * '-')
                    self.log(headery)
                    self.log(69 * '-')

                    cnt = tmp = pb = 0

                    for row in transformed_data:
                        tmp += 1

                    init_progressbar(tmp)

                    for row in transformed_data:
                        if row[0]:
                            if row[1] or row[2]:
                                self.log(f'{row[0].ljust(10)}{row[1].ljust(25)}{row[2].ljust(25)}{row[3].ljust(15)}')

                            cnt += 1
                            pb += (100 / tmp)
                            update_progressbar(pb)
                    
                    if pb < 100:
                        pb = 100
                        update_progressbar(pb)

                    self.log('')
                    self.log(f'Record(s): {cnt}')
                    self.log('')

                    with open('final.csv', 'w', newline='') as outfile:
                        writer = csv.writer(outfile)
                        writer.writerow(['emp_id', 'check_in', 'check_out', 'shift_type'])
                        writer.writerows(transformed_data)

                    time.sleep(1)

                except (DatabaseError, InterfaceError) as e:
                    self.log(f'ERROR: {type(e).__name__} - {e}')

                finally:
                    cur.close()
                    conn.close()

            except OperationalError as e:
                self.log(f'ERROR: {type(e).__name__} - {e}')

        def insert_into_c_tmp(csv_file):
            time.sleep(1)
            self.log('STEP-6: Uploading final record(s) ...', 'blue', 'bold')
            self.log('')
            
            db_config = {
                'dbname': 'fgtest',
                'user': 'fgatt',
                'password': 'fgatt1947',
                'host': '109.199.127.25',
                'port': '5432'
            }

            try:
                conn = psycopg2.connect(**db_config)
                cursor = conn.cursor()

                cnt = tmp = pb = 0

                headery = f'{"EmpID".ljust(10)}{"CheckIn".ljust(25)}{"CheckOut".ljust(25)}'
                self.log(59 * '-')
                self.log(headery)
                self.log(59 * '-')

                with open(csv_file, mode='r') as file:
                    csv_reader = csv.reader(file)
                    header = next(csv_reader)

                    for row in csv_reader:
                        tmp += 1

                init_progressbar(tmp)

                with open(csv_file, mode='r') as file:
                    csv_reader = csv.reader(file)
                    header = next(csv_reader)

                    insert_query = '''
                        INSERT INTO 
                            c_tmp (
                                emp_id, 
                                check_in, 
                                check_out
                            )
                        VALUES (
                            %s, 
                            %s, 
                            %s
                        )
                    '''

                    cursor.execute('DELETE FROM c_tmp;')

                    for row in csv_reader:
                        emp_id, check_in, check_out = row[:3]
                        self.log(f'{row[0].ljust(10)}{row[1].ljust(25)}{row[2].ljust(25)}')
                        
                        if check_in == '':
                            check_in = None

                        if check_out == '':
                            check_out = None

                        if emp_id:
                            if check_in or check_out:
                                cursor.execute(insert_query, (emp_id, check_in, check_out))

                            cnt += 1
                            pb += (100 / tmp)
                            update_progressbar(pb)

                    if pb < 100:
                        pb = 100
                        update_progressbar(pb)

                self.log('')
                self.log(f'Record(s): {cnt}')
                self.log('')

                conn.commit()

            except (Exception, psycopg2.DatabaseError) as error:
                self.log(f'Error occurred: {error}')
                conn.rollback()

            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

        def mainx():
            '''Main function to check connectivity before execution of get_data fuction'''

            self.log('')
            self.log('STEP-1: Performing connectivity tests ...', 'blue', 'bold')
            self.log('')

            host1 = '109.199.127.25'
            port1 = 80
            host2 = '192.168.0.117'
            port2 = 4370
            ping_test1, ping_test2 = False, False

            if (ping_host(host1, port1)) is True:
                ping_test1 = True
                self.log('PASSED: ERP Server Ping-Test ...', 'green')
            else:
                ping_test1 = False
                self.log('FAILED: ERP Server Ping-Test ...', 'black', blink=True)

            if (ping_host(host2, port2)) is True:
                ping_test2 = True
                self.log('PASSED: Attendance Machine Pint-Test ...', 'green')
            else:
                ping_test2 = False
                self.log('FAILED: Attendance Machine Ping-Test ...', 'black', blink=True)

            if not (ping_test1 and ping_test2):
                self.log('FAILED: In order to proceed furthur both Ping-Tests should be PASSED ...', 'black', blink=True)
                self.log('')
            else:
                self.log('PASSED: Both Ping Tests Are PASSED ...', 'green')
                self.log('')

                count_machine_records(start_date, end_date)
                get_data(start_date, end_date)
                fetch_records(start_date, end_date)
                insert_into_c_tmp('final.csv')

                self.log(28 * '-' + ' [ FINISHED ] ' + 28 * '-', 'green', 'bold')
                self.log('')
                self.log('Save the logs by clicking the "Save Log" button.')
                self.log('')

        mainx()

        end_time = time.time()
        elapsed_time = end_time - start_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        self.log(f'Time consumed during execution: {formatted_time}', 'green', 'bold', blink=True)
        self.log('')

    def start_generate(self):
        self.start_btn.config(state='disabled')
        self.close_btn.config(state='disabled')
        self.save_btn.config(state='disabled')
        self.start_calendar.config(state='disabled')
        self.end_calendar.config(state='disabled')
        thread = threading.Thread(target=self.threaded_generate)
        thread.start()
        self.check_thread(thread)

    def check_thread(self, thread):
        if thread.is_alive():
            self.root.after(100, lambda: self.check_thread(thread))
        else:
            self.start_btn.config(state='normal')
            self.close_btn.config(state='normal')
            self.save_btn.config(state='normal')
            self.start_calendar.config(state='normal')
            self.end_calendar.config(state='normal')

    def close(self):
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()