# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import font, ttk, messagebox
from tkcalendar import DateEntry
import threading
import os
import socket
import csv
import psycopg2
import time
from datetime import datetime, timedelta
from psycopg2 import OperationalError, DatabaseError, InterfaceError
from zk import ZK, const # type: ignore


def threaded_generate():
    start_time = time.time()  # Record the start time
    start_btn.focus_set()  # Save button gets focus

    log_text.config(state='normal')  # Enable the text box to modify its content
    log_text.delete('1.0', tk.END)  # Clear all content in the text box
    log_text.config(state='disabled')  # Disable the text box again

    rec = None
    start_date = start_calendar.get_date()
    end_date = end_calendar.get_date()

    # Global variables to keep track of progress
    current_progress = 0
    total_steps = 100

    # Log the action
    log(f'Start button clicked. Start Date: {start_date.strftime("%d/%m/%Y")}, End Date: {end_date.strftime("%d/%m/%Y")}')
    
    # Check if end_date is before start_date
    if end_date < start_date:
        messagebox.showerror('Error', 'End Date cannot be earlier than Start Date!')
        return

    def update_progress():
        global current_progress

        if current_progress < total_steps:
            current_progress += 1  # Increment progress
            progress_bar['value'] = current_progress  # Update progress bar
            root.update_idletasks()  # Update the GUI
            root.after(100, update_progress)  # Call this function again after 100ms

    # Function to parse date and time strings into datetime objects
    def parse_datetime(dt_str):
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') if dt_str else None

    # Function to format datetime objects back to string format
    def format_datetime(dt):
        return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''

    # Function to perform ping test for checking servers availabillity
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

    # Main function to count machine records
    def count_machine_records(start_date, end_date):
        nonlocal rec
        dip = '192.168.0.117'
        port = 4370
        zk = ZK(dip, port, timeout=5)
        conn = None
        sdate = start_date
        edate = end_date
        delta = edate - sdate   # returns timedelta

        try:
            log('STEP-2: Counting date-wise records ...')
            log('')
            conn = zk.connect()
            conn.disable_device()
            attendances = conn.get_attendance()
            cnt = tmp = 0 # Counter
            
            for i in range(delta.days + 1):
                datex = sdate + timedelta(days=i)

                for att in attendances:
                    x = att.timestamp

                    if (x.strftime('%Y-%m-%d') == datex.strftime('%Y-%m-%d')):
                        cnt += 1    # Increment

                log(f'{datex} has {cnt} record(s)')
                tmp += cnt
                cnt = 0
            
            conn.enable_device()
            log('')
            log(f'Total Record(s): {tmp}')
            log('')
            rec = tmp
            time.sleep(2)  # 2 seconds delay

        except Exception as e:
            log('Process terminate : {}'.format(e))

        finally:
            if conn:
                conn.disconnect()

    # Main function to pull attendance records from machine and push to erp server
    def get_data(start_date, end_date):
        dip = '192.168.0.117'
        port = 4370
        zk = ZK(dip, port, timeout=5)

        conn = None
        pgcon = None

        sdate = start_date
        edate = end_date

        delta = edate - sdate   # returns timedelta
        
        try:
            log('STEP-3: Fetching/Pulling records from machine ...')
            log('')
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

            # PGS Cursor
            cursor = pgcon.cursor()

            # Deleting records before inserting
            cursor.execute('DELETE FROM a_tmp;') # Decided now

            progress_bar['length'] == rec
            progress_bar['maximum'] == rec
            progress_bar['value'] = 0

            for i in range(delta.days + 1):
                datex = sdate + timedelta(days=i)
                log(f'Working on: {datex}')
                log('')

                if attendances:
                    cnt = 0 # Counter

                    for att in attendances:
                        x = att.timestamp

                        if (x.strftime('%Y-%m-%d') == datex.strftime('%Y-%m-%d')):
                            log('User      : {}'.format(att.user_id))
                            log('Timestamp : {}'.format(att.timestamp))

                            cnt += 1    # Increment

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

                                log('')

                                # # Reset the progress and start updating
                                progress_bar['value'] += (100 / rec)
                                root.update_idletasks()
                                root.after(10)  # Simulate delay

                            except (Exception, psycopg2.DatabaseError) as error:
                                log(error)

                    log(f'Record(s): {cnt}')    
                    log('')

            if pgcon:
                pgcon.commit()
                cursor.close()
                pgcon.close()


            conn.enable_device()
            time.sleep(2)  # 2 seconds delay

        except Exception as e:
            log('Process terminate : {}'.format(e))

        finally:
            if conn:
                conn.disconnect()

    # Function to get raw attendance data and perform the necessary transformation
    def fetch_records(start_date, end_date):
        try:
            # Establishing a connection to the PostgreSQL database
            conn = psycopg2.connect(
                database='fgtest',
                user='fgatt',
                password='fgatt1947',
                host='109.199.127.25',
                port='5432'
            )

            cur = conn.cursor()  # Creating a cursor object to interact with the database

            try:
                # SQL query to fetch attendance data within the given date range
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
                
                rows = cur.fetchall()  # Fetching all records matching the query
                
                cnt = tmp = 0 # Counter


                result = []  # List to store the results after processing
                tmp = len(rows)

                progress_bar['length'] == tmp
                progress_bar['maximum'] == tmp
                progress_bar['value'] = 0

                for r in rows:
                    # Parsing start and end times of the shift
                    # log(f'r[0]: {r[0]}, r[1]: {r[1]}, r[2]: {r[2]}, r[3]: {r[3]}')
                    start_time = datetime.strptime(r[2], '%H:%M').time()
                    end_time = datetime.strptime(r[3], '%H:%M').time()

                    # Calculating the minutes difference between the check-in/out time and shift start/end times
                    x = abs((r[1].hour * 60 + r[1].minute) - (start_time.hour * 60 + start_time.minute))
                    y = abs((r[1].hour * 60 + r[1].minute) - (end_time.hour * 60 + end_time.minute))

                    # Determining whether the record is closer to CheckIn or CheckOut time
                    if x < y:
                        z = 'CheckIn'  # start time is closer
                    elif y < x:
                        z = 'CheckOut'  # end time is closer

                    result.append((r[0], r[1].strftime('%Y-%m-%d %H:%M:%S'), z, r[4]))  # Appending processed data to result
                    cnt += 1    # Counter Increment

                # Raw data in tuple format
                raw_data = result

                # Convert tuples to lists
                raw_data_as_lists = [list(item) for item in raw_data]

                # Open a CSV file to write raw data
                with open('raw.csv', 'w', newline='') as csvfile:
                    fields = ['emp_id', 'check_time', 'check_type', 'shift_type']
                    writer = csv.writer(csvfile)
                    writer.writerow(fields)  # Writing the header
                    writer.writerows(raw_data_as_lists)  # Writing the rows of raw data

                # Read data from raw.csv
                with open('raw.csv', 'r') as infile:
                    reader = csv.DictReader(infile, delimiter=',')  # Reading CSV data into a dictionary format
                    raw_data = list(reader)

                # Transform data to match CheckIn with corresponding CheckOut
                transformed_data = []
                current_emp_id = None
                check_in_time = None
                current_shift = None
                max_shift_duration = timedelta(hours=24)  # Setting the maximum shift duration to 24 hours

                time.sleep(1)  # 1 seconds delay
                log('STEP-4: Getting raw data from table for processing furthur ...')
                log('')
                log('Identifying CheckIn/CheckOut based on shift timing:')
                log('')

                headerx = f'{"EmpID".ljust(10)}{"CheckTime".ljust(25)}{"CheckType".ljust(15)}{"ShiftType".ljust(15)}'
                log(59 * '-')
                log(headerx)
                log(59 * '-')

                # Getting raw data for processing from raw_data list
                for row in raw_data:
                    emp_id = row['emp_id']
                    check_time = row['check_time']
                    check_type = row['check_type']
                    shift_type = row['shift_type']
                    check_time_dt = parse_datetime(check_time)

                    log(f'{emp_id.ljust(10)}{check_time.ljust(25)}{check_type.ljust(15)}{shift_type.ljust(15)}')
                    progress_bar['value'] += (100 / tmp)
                    root.update_idletasks()
                    root.after(10)  # Simulate delay

                    if emp_id != current_emp_id:
                        
                        transformed_data.append([current_emp_id, format_datetime(check_in_time), '', current_shift])

                        # If the employee ID changes, reset variables for the new employee
                        current_emp_id = emp_id
                        current_shift = shift_type
                        check_in_time = None
                    
                    if check_type == 'CheckIn':
                        if check_in_time is None:
                            # Register a new CheckIn if there isn't one pending
                            check_in_time = check_time_dt
                        else:
                            # If there's already a pending CheckIn, store it without a corresponding CheckOut
                            transformed_data.append([emp_id, format_datetime(check_in_time), '', shift_type])
                            check_in_time = check_time_dt  # Update with the new CheckIn

                    elif check_type == 'CheckOut':
                        if check_in_time is not None:
                            # If there's a pending CheckIn, pair it with this CheckOut if within 24 hours
                            if check_time_dt - check_in_time <= max_shift_duration:
                                transformed_data.append([emp_id, format_datetime(check_in_time), format_datetime(check_time_dt), shift_type])
                                check_in_time = None
                            else:
                                # If the CheckOut is beyond 24 hours, discard it and consider it as an orphan entry
                                transformed_data.append([emp_id, format_datetime(check_in_time), '', shift_type])
                                check_in_time = None
                                # Store the orphan CheckOut separately
                                transformed_data.append([emp_id, '', format_datetime(check_time_dt), shift_type])
                        else:
                            # Orphan CheckOut with no preceding CheckIn
                            transformed_data.append([emp_id, '', format_datetime(check_time_dt), shift_type])

                # Handle remaining CheckIn with no corresponding CheckOut at the end of processing
                if check_in_time is not None:
                    transformed_data.append([current_emp_id, format_datetime(check_in_time), '', shift_type])

                log('')
                log(f'Record(s): {cnt}')
                log('')
                time.sleep(1)  # 1 seconds delay
                log('STEP-5: Raw data transformation is being processed ...')
                log('')
                log('Placing CheckIn/CheckOut based on shift timing:')
                log('')
                time.sleep(3)  # 3 seconds delay
                headery = f'{"EmpID".ljust(10)}{"CheckIn".ljust(25)}{"CheckOut".ljust(25)}{"ShiftType".ljust(15)}'
                log(69 * '-')
                log(headery)
                log(69 * '-')

                cnt = tmp = 0 # Counters

                # Displaying the transformed data
                for row in transformed_data:
                    
                    tmp += 1

                progress_bar['length'] == tmp
                progress_bar['maximum'] == tmp
                progress_bar['value'] = 0

                for row in transformed_data:
                    if row[0]:
                        if row[1] or row[2]:
                            log(f'{row[0].ljust(10)}{row[1].ljust(25)}{row[2].ljust(25)}{row[3].ljust(15)}')

                        cnt += 1    # Counter Increment
                        progress_bar['value'] += (100 / tmp)
                        root.update_idletasks()
                        root.after(10)  # Simulate delay

                log('')
                log(f'Record(s): {cnt}')
                log('')

                # Write the transformed data to a final CSV file
                with open('final.csv', 'w', newline='') as outfile:
                    writer = csv.writer(outfile)
                    writer.writerow(['emp_id', 'check_in', 'check_out', 'shift_type'])  # Writing the header
                    writer.writerows(transformed_data)  # Writing the transformed data rows

                time.sleep(2)  # 2 seconds delay

            # Catching and printing database-related errors
            except (DatabaseError, InterfaceError) as e:
                log(f'ERROR: {type(e).__name__} - {e}')

            # Closing the cursor and database connection
            finally:
                cur.close()
                conn.close()

        except OperationalError as e:
            # Catching and printing operational errors (e.g., connection issues)
            log(f'ERROR: {type(e).__name__} - {e}')

    # Function to insert records into c_tmp table from final.csv file
    def insert_into_c_tmp(csv_file):
        time.sleep(1)  # 1 seconds delay
        log('STEP-6: Uploading final record(s) ...')
        log('')
        
        # Database connection details
        db_config = {
            'dbname': 'fgtest',
            'user': 'fgatt',
            'password': 'fgatt1947',
            'host': '109.199.127.25',
            'port': '5432'
        }

        try:
            # Establish a database connection
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # Just two counters
            cnt = tmp = 0

            headery = f'{"EmpID".ljust(10)}{"CheckIn".ljust(25)}{"CheckOut".ljust(25)}'
            log(59 * '-')
            log(headery)
            log(59 * '-')

            # Open the CSV file and read its content
            with open(csv_file, mode='r') as file:
                csv_reader = csv.reader(file)
                header = next(csv_reader)  # Skip the header row if present

                for row in csv_reader:
                    tmp += 1

            progress_bar['length'] == tmp
            progress_bar['maximum'] == tmp
            progress_bar['value'] = 0

            # Open the CSV file and read its content
            with open(csv_file, mode='r') as file:
                csv_reader = csv.reader(file)
                header = next(csv_reader)  # Skip the header row if present

                # Prepare the SQL query for inserting data
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

                # Deleting records before inserting
                cursor.execute('DELETE FROM c_tmp;')

                # Iterate over the CSV data and insert each row into the database
                for row in csv_reader:
                    emp_id, check_in, check_out = row[:3]
                    log(f'{row[0].ljust(10)}{row[1].ljust(25)}{row[2].ljust(25)}')
                    
                    if check_in == '':
                        check_in = None  # Handle missing check_in as NULL

                    if check_out == '':
                        check_out = None  # Handle missing check_out as NULL

                    # Handling missing emp_id, it can't be null
                    if emp_id:
                        # Handling missing check_in or check_out, can't be null both columns, need one of them else skip current row 
                        if check_in or check_out:
                            cursor.execute(insert_query, (emp_id, check_in, check_out))

                        cnt += 1    # Counter Increment
                        progress_bar['value'] += (100 / tmp)
                        root.update_idletasks()
                        root.after(10)  # Simulate delay

            log('')
            log(f'Record(s): {cnt}')
            log('')

            # Commit the transaction
            conn.commit()

        except (Exception, psycopg2.DatabaseError) as error:
            log(f'Error occurred: {error}')
            conn.rollback()  # Rollback in case of error

        finally:
            # Close the database connection
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Main function
    def main():
        '''Main function to check connectivity before execution of get_data fuction'''

        log('')
        log('STEP-1: Performing connectivity tests ...')
        log('')

        host1 = '109.199.127.25'
        port1 = 80
        host2 = '192.168.0.117'
        port2 = 4370
        ping_test1, ping_test2 = False, False

        if (ping_host(host1, port1)) is True:
            ping_test1 = True
            log('PASSED: ERP Server Ping-Test ...')
        else:
            ping_test1 = False
            log('FAILED: ERP Server Ping-Test ...')

        if (ping_host(host2, port2)) is True:
            ping_test2 = True
            log('PASSED: Attendance Machine Pint-Test ...')
        else:
            ping_test2 = False
            log('FAILED: Attendance Machine Ping-Test ...')

        if not (ping_test1 and ping_test2):
            log('FAILED: In order to proceed furthur both Ping-Tests should be PASSED ...')
            log('')
        else:
            log('PASSED: Both Ping Tests Are PASSED ...')
            log('')

            # Count records from attendance machine
            count_machine_records(start_date, end_date)
            
            # Fetch data from attendance machine
            get_data(start_date, end_date)

            # Fetch and process records based on the provided dates from a_tmp table
            fetch_records(start_date, end_date)

            # Insert final.csv data into c_tmp table
            insert_into_c_tmp('final.csv')

            log('----------------')
            log('--- FINISHED ---')
            log('----------------')
            log('')
            log('Save the logs by clicking the "Save Log" button.')
            log('')

    # Calling main()
    main()

    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))  # Format the elapsed time    
    log(f'Time consumed during execution: {formatted_time}')
    log('')

    # start_btn.config(relief='raised')  # Save Log button goes back to raised
    # messagebox.showinfo('Finished', f'Start Date: {start_date.strftime("%d/%m/%Y")}\nEnd Date: {end_date.strftime("%d/%m/%Y")}')

def log(message):
    log_text.config(state='normal')  # Temporarily enable writing
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_text.insert(tk.END, f'{current_time} - {message}\n')
    log_text.see(tk.END)  # Scroll to the end to show the latest log
    log_text.config(state='disabled')  # Disable writing again
    root.update_idletasks()  # Update the GUI in real-time

def save_log_to_file():
    save_btn.focus_set()  # Close button gets focus
    log_content = log_text.get('1.0', tk.END)  # Get all content from Text widget

    with open('attlog.txt', 'w') as file:
        file.write(log_content)

    # deleting raw.csv and final.csv
    try:
        os.remove('raw.csv')
        log('"raw.csv" deleted successfully ...')
    except FileNotFoundError:
        log('"raw.csv" not found, unable to delete ...')

    try:
        os.remove('final.csv')
        log('"final.csv" deleted successfully ...')
    except FileNotFoundError:
        log('"final.csv" not found, unable to delete ...')

    log('Logs saved to "attlog.txt" ...')

def disable_close_button():
    # Override the close button behavior (Windows 'X' button)
    root.protocol('WM_DELETE_WINDOW', on_close_attempt)

def enable_close_button():
    # Restore the default close behavior
    root.protocol('WM_DELETE_WINDOW', root.destroy)

def on_close_attempt():
    # Log a message instead of closing
    log('Close button is disabled during execution.')

def close():
    close_btn.focus_set()  # Close button gets focus
    log('Close button clicked.')
    root.destroy()

def start_generate():
    start_btn.config(state='disabled')  # Disable the button while processing
    close_btn.config(state='disabled')  # Disable the button while processing
    save_btn.config(state='disabled')  # Disable the button while processing

    start_calendar.config(state='disabled')  # Disable the Start calendar
    end_calendar.config(state='disabled')  # Disable the End calendar

    disable_close_button()  # Disable the window's close button

    thread = threading.Thread(target=threaded_generate)
    thread.start()
    check_thread(thread)

def check_thread(thread):
    if thread.is_alive():
        root.after(100, lambda: check_thread(thread))
    else:
        start_btn.config(state='normal')  # Re-enable the button when done
        close_btn.config(state='normal')  # Re-enable the button when done
        save_btn.config(state='normal')  # Re-enable the button when done

        start_calendar.config(state='normal')  # Re-enable the Start calendar
        end_calendar.config(state='normal')  # Re-enable the End calendar

        enable_close_button()  # Re-enable the window's close button

def update_status_bar():
    width = root.winfo_width()
    height = root.winfo_height()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status_label.config(text=f'Size: {width} x {height} | Date & Time: {current_time}')
    root.after(1000, update_status_bar)

def center_window(win, width=600, height=600):
    screen_width = win.winfo_screenwidth()
    screen_height = win.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    win.geometry(f'{width}x{height}+{x}+{y}')

root = tk.Tk()
root.title('Get Attendance')
center_window(root, 600, 600)

root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_columnconfigure(3, weight=1)
root.grid_columnconfigure(4, weight=1)
root.grid_columnconfigure(5, weight=1)
root.grid_columnconfigure(6, weight=1)  # Added a new column
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(3, weight=0)

tk.Label(root, text='Start Date:').grid(row=0, column=0, padx=10, pady=10, sticky='ew')
start_calendar = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/MM/yyyy')
start_calendar.grid(row=0, column=1, padx=10, pady=10, sticky='ew')

tk.Label(root, text='End Date:').grid(row=0, column=2, padx=10, pady=10, sticky='ew')
end_calendar = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='dd/MM/yyyy')
end_calendar.grid(row=0, column=3, padx=10, pady=10, sticky='ew')

start_btn = tk.Button(
    root, 
    text='Start', 
    command=start_generate, 
    relief='raised', 
    activebackground='lightblue', 
    activeforeground='black'
)

start_btn.grid(row=0, column=4, padx=10, pady=10, sticky='ew')

close_btn = tk.Button(root, text='Close', command=close)
close_btn.grid(row=0, column=5, padx=10, pady=10, sticky='ew')

save_btn = tk.Button(root, text='Save Log', command=save_log_to_file)
save_btn.grid(row=0, column=6, padx=10, pady=10, sticky='ew')  # Moved to column 6

monospace_font = font.Font(family='Consolas', size=8)

# Create a frame to hold the log_text and scrollbar
log_frame = tk.Frame(root)
log_frame.grid(row=1, column=0, columnspan=7, padx=10, pady=10, sticky='nsew')  # Increased columnspan to 7
log_frame.grid_columnconfigure(0, weight=1)
log_frame.grid_rowconfigure(0, weight=1)

log_text = tk.Text(log_frame, font=monospace_font, state='disabled', wrap='word')
log_text.grid(row=0, column=0, sticky='nsew')

# Create a custom style for the scrollbar
style = ttk.Style()
style.theme_use('clam')
style.configure('Thin.Vertical.TScrollbar', gripcount=0, background='gray', troughcolor='white', width=8)

scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview, style='Thin.Vertical.TScrollbar')
scrollbar.grid(row=0, column=1, sticky='ns')
log_text.config(yscrollcommand=scrollbar.set)

style.configure('black.Horizontal.TProgressbar', foreground='black', background='black')

progress_bar = ttk.Progressbar(root, orient='horizontal', length=100, mode='determinate', maximum=100, style='black.Horizontal.TProgressbar')
progress_bar.grid(row=2, column=0, columnspan=7, padx=10, pady=10, sticky='ew')  # Increased columnspan to 7

status_label = tk.Label(root, text='', bd=1, relief=tk.SUNKEN, anchor=tk.W)
status_label.grid(row=3, column=0, columnspan=7, sticky='ew')  # Increased columnspan to 7

update_status_bar()
root.mainloop()