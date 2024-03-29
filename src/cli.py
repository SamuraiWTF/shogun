import argparse
import json
import sys
import time

from compose import create_student_container, delete_student_container, list_available_labs, \
    list_student_lab_combinations, multi_create_student_container
from lab_config import config


def reload_containers(pause_duration=8):
    combinations = list_student_lab_combinations()
    for lab_id, students in combinations.items():
        for student_id in students:
            delete_student_container(student_id, lab_id, True)  # assuming norestart is False
            print(f"Pausing for {pause_duration} seconds...")
            time.sleep(pause_duration)  # pause for specified duration
            create_student_container(student_id, lab_id, False)  # assuming norestart is False
            print(f"Reloaded container for student {student_id} in lab {lab_id}.")

def main():
    if sys.platform.startswith('win32'):
        prog_name = 'shogun.bat'
    elif sys.platform.startswith(('linux', 'darwin')):
        prog_name = 'shogun'
    else:
        prog_name = 'shogun'

    parser = argparse.ArgumentParser(prog=prog_name, description='Shogun CLI for Samurai WTF Labs')
    subparsers = parser.add_subparsers(dest='command')

    # Create student container command
    create_parser = subparsers.add_parser('create', help='Create a new student container')
    create_parser.add_argument('student_id', help='Student ID or Student ID prefix if count is provided')
    create_parser.add_argument('--count', type=int, default=0,
                               help='Number of student containers to create (positive integer)')
    create_parser.add_argument('--start', type=int, default=1,
                               help='Starting index for student container creation (positive integer)')
    create_parser.add_argument('lab_id', help='Lab ID')
    create_parser.add_argument('--norestart', action='store_true', default=False,
                               help='Do not restart Nginx after creating the container (default: restart)')

    # Delete student container command
    delete_parser = subparsers.add_parser('delete', help='Delete a student container')
    delete_parser.add_argument('student_id', nargs='?', default='*', help='Student ID (use * for all students)')
    delete_parser.add_argument('lab_id', nargs='?', default='*', help='Lab ID (use * for all labs)')
    delete_parser.add_argument('--norestart', action='store_true', default=False,
                               help='Do not restart Nginx after deleting the container (default: restart)')

    # List available labs command
    list_available_parser = subparsers.add_parser('list', help='List labs')
    list_available_parser.add_argument('type', choices=['available', 'active'],
                                       help='Specify whether to list available or active labs.')
    list_available_parser.add_argument('--format', choices=['json', 'text'], default='text',
                                       help='Output format: text or json (default: text)')

    reload_parser = subparsers.add_parser('reload', help='Reload student containers')
    reload_parser.add_argument('--pause', type=int, default=8,
                               help='Pause duration between delete and create operations (in seconds)')

    args = parser.parse_args()

    if args.command == 'create':
        if 'student_id' not in args:
            print(f"Specify a student ID or prefix for this container.")
        elif 'lab_id' not in args:
            print(f"Specify a lab ID for this container.")
        elif args.count > 0:
            multi_create_student_container(args.student_id, args.lab_id, args.count, args.start, args.norestart)
            print(f"Created {args.count} containers for student prefix {args.student_id} and lab {args.lab_id}.")
        else:
            create_student_container(args.student_id, args.lab_id, args.norestart)

    elif args.command == 'delete':
        delete_student_container(args.student_id, args.lab_id, args.norestart)

        if args.student_id == '*' and args.lab_id == '*':
            print("Deleted all labs for all students.")
        elif args.student_id == '*':
            print(f"Deleted lab {args.lab_id} for all students.")
        elif args.lab_id == '*':
            print(f"Deleted all labs for student {args.student_id}.")
        else:
            print(f"Deleted lab {args.lab_id} for student {args.student_id}.")
    elif args.command == 'list':

        if 'type' not in args:
            print(f"Specify which type of items you want to list. Choices are 'available' or 'active'.")
        elif args.type == 'available':
            labs = []
            for lab in config['labs']:
                labs.append(lab['name'])
            if len(labs) == 0 and args.format == 'text':
                print("No labs available.")
                return
            else:
                if args.format == 'json':
                    print(json.dumps(labs))
                else:
                    print("Available labs:")
                    for lab in labs:
                        print(f"- {lab}")
        elif args.type == 'active':
            combinations = list_student_lab_combinations()
            if not combinations:
                if args.format == 'json':
                    print(json.dumps({}))
                else:
                    print("No active student-lab combinations.")
                return
            else:
                if args.format == 'json':
                    print(json.dumps(combinations))
                else:
                    print("Active student-lab combinations:")
                    for lab_id, students in combinations.items():
                        print(f"Lab {lab_id}:")
                        for student_id in students:
                            print(f"  - {student_id}")

    elif args.command == 'reload':
        reload_containers(args.pause)
    else:
        parser.print_help()


def print_or_json(text, output_format):
    if output_format == 'json':
        print(json.dumps(text))
    else:
        print(text)


if __name__ == '__main__':
    main()
