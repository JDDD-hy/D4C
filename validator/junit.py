import os
import re
import subprocess
import signal

def signal_handler(signum, frame):
    raise TimeoutError("Time out")

def set_timeout(seconds):
    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

def reset_timeout():
    signal.alarm(0)

def run_JUnit(bug_id, test_config):
    try:
        os.chdir('defects4j/' + bug_id + '_buggy')
        set_timeout(test_config['time_out'])
        cmd = 'defects4j test'
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        os.chdir('../../')
        output, _ = process.communicate()
        process.kill()
        output = output.decode('utf-8')
        reset_timeout()
        # if output != 'Failing tests: 0':
        if 'Running ant (compile.tests)................................................ FAIL' in output:
            return False, 'Compile failed' 
        else:
            match = re.search(r'Failing tests:\s*\d+', output)
            if match:
                failing_test_result = match.group(0)
            else:
                failing_test_result = 'Failing tests count not found'
            return True if failing_test_result == 'Failing tests: 0' else False, failing_test_result
    except (RuntimeError, TypeError, NameError, FileNotFoundError, TimeoutError) as e:
        print(e)
        process.kill()
        return False, e

def class_read(java_file_path):
    try:
        with open(java_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except UnicodeDecodeError:
        with open(java_file_path, 'r', encoding='iso-8859-1') as file:  # otherwise, try 'iso-8859-1' or 'cp1252'
            content = file.read()
    return content

def class_write(java_file_path, content):
    with open(java_file_path, 'w', encoding='utf-8', errors='ignore') as outfile:
        outfile.write(content)
    outfile.close()
    
def extract_method_start_end_index(java_file_path, function_head, method_length):
    content = class_read(java_file_path)
    lines = content.split('\n')
    pattern_lines = function_head.split('\n')

    start_char_idx = content.find(function_head)
    if start_char_idx != -1:
        start_line_idx = content[:start_char_idx].count('\n')
        return [start_line_idx, start_line_idx + method_length]

    for i in range(len(lines)):
        if lines[i].split(')')[0].strip() == pattern_lines[0].strip():
            if len(pattern_lines) == 1:
                return [i, i + method_length]
            for j in range(len(pattern_lines))[1:]:
                if lines[i + j].split(')')[0].strip() != pattern_lines[j].strip():
                    break
            return [i, i + method_length]   
        
    return None
            
def replace_file(java_file_path, replace_index, fixed_method):
    content = class_read(java_file_path)
    class_lines = content.split('\n')
    fixed_method_lines = fixed_method.split('\n')
    fixed_method_lines[-1] = fixed_method_lines[-1].split('@Override')[0] # remove redundant '@Override' at the end of the method
    class_lines[replace_index[0]:replace_index[1]] = fixed_method_lines
    code = '\n'.join(class_lines)
    class_write(java_file_path, code)

def restore_file(file_path, bug_id):
    try:
        # Using git restore command to revert the file to the last commit state
        os.chdir('defects4j/' + bug_id + '_buggy')
        cmd = 'git checkout -- ' + file_path.replace('defects4j/' + bug_id + '_buggy/', '')
        os.system(cmd)
        os.chdir('../../')
    except (RuntimeError, TypeError, NameError,FileNotFoundError) as e:
        print(f"An error occurred while restoring changes to the file: {e}")

